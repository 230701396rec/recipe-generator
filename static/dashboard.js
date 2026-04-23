import {
    initAuth,
    isAuthConfigured,
    isAuthEnabled,
    logout,
    onAuthStateChanged
} from "./auth.js";

const form = document.getElementById("recipe-form");
const imageInput = document.getElementById("image");
const imagePreview = document.getElementById("image-preview");
const generateButton = document.getElementById("generate-button");
const saveButton = document.getElementById("save-button");
const refreshRecipesButton = document.getElementById("refresh-recipes-button");
const logoutButton = document.getElementById("logout-button");
const statusMessage = document.getElementById("status-message");
const recipeOutput = document.getElementById("recipe-output");
const savedRecipes = document.getElementById("saved-recipes");

let currentRecipe = "";

imageInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imagePreview.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    } else {
        imagePreview.src = "";
        imagePreview.classList.add("hidden");
    }
});

function parseMarkdown(text) {
    if (!text) return "";
    return text
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');
}

function setRecipeActionsEnabled(isEnabled) {
    saveButton.disabled = !isEnabled;
}

function resetRecipeOutput(message) {
    currentRecipe = "";
    recipeOutput.innerHTML = message;
    setRecipeActionsEnabled(false);
}

async function apiRequest(url, options = {}) {
    const requestOptions = {
        ...options,
        headers: new Headers(options.headers || {})
    };

    const response = await fetch(url, requestOptions);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }

    return data;
}

function recipeCardTemplate(recipe) {
    const imageMarkup = recipe.imageUrl
        ? `<img src="${recipe.imageUrl}" alt="Recipe image for saved recipe">`
        : "";

    return `
        <article class="recipe-card" data-recipe-id="${recipe.id}">
            ${imageMarkup}
            <div class="recipe-card-body">
                <div class="recipe-card-header">
                    <strong>Saved Recipe</strong>
                </div>
                <p class="recipe-meta">${recipe.createdAt || "Just now"}</p>
                <p class="recipe-meta">${Array.isArray(recipe.ingredients) ? recipe.ingredients.join(", ") : (recipe.ingredients || "No ingredients provided.")}</p>
                <div class="recipe-content">${parseMarkdown(recipe.generatedRecipe)}</div>
            </div>
        </article>
    `;
}

async function loadSavedRecipes() {
    if (!isAuthConfigured() || !isAuthEnabled()) {
        savedRecipes.innerHTML = "<p>Please sign in to access your recipes.</p>";
        return;
    }

    try {
        const data = await apiRequest("/my-recipes");

        if (!data.recipes.length) {
            savedRecipes.innerHTML = "<p>No recipes saved yet.</p>";
            return;
        }

        savedRecipes.innerHTML = data.recipes.map(recipeCardTemplate).join("");
    } catch (error) {
        savedRecipes.innerHTML = `<p class="error-text">${error.message}</p>`;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    generateButton.disabled = true;
    statusMessage.textContent = "Generating recipe...";
    recipeOutput.innerHTML = "Please wait while your recipe is being created.";

    try {
        const formData = new FormData(form);
        const data = await apiRequest("/generate-recipe", {
            method: "POST",
            body: formData
        });

        currentRecipe = data.recipe;
        recipeOutput.innerHTML = parseMarkdown(currentRecipe);
        statusMessage.textContent = "Recipe generated successfully.";
        setRecipeActionsEnabled(Boolean(currentRecipe));
    } catch (error) {
        resetRecipeOutput(error.message);
        statusMessage.textContent = "Recipe generation failed.";
    } finally {
        generateButton.disabled = false;
    }
});

saveButton.addEventListener("click", async () => {
    if (!currentRecipe) {
        statusMessage.textContent = "Generate a recipe before saving it.";
        return;
    }

    try {
        saveButton.disabled = true;
        statusMessage.textContent = "Saving recipe...";

        const formData = new FormData();
        formData.set("ingredients", document.getElementById("ingredients").value.trim());
        formData.set("generatedRecipe", currentRecipe);

        const file = imageInput.files[0];
        if (file) {
            formData.set("image", file);
        }

        await apiRequest("/save-recipe", {
            method: "POST",
            body: formData
        });

        statusMessage.textContent = "Recipe saved successfully.";
        await loadSavedRecipes();
    } catch (error) {
        statusMessage.textContent = error.message;
    } finally {
        setRecipeActionsEnabled(Boolean(currentRecipe));
    }
});

refreshRecipesButton.addEventListener("click", async () => {
    await loadSavedRecipes();
});

logoutButton.addEventListener("click", async () => {
    await logout();
});

onAuthStateChanged(async ({ enabled, user, error }) => {
    if (error) return;

    if (!enabled || !user) {
        setRecipeActionsEnabled(false);
        window.location.assign("/");
        return;
    }

    setRecipeActionsEnabled(Boolean(currentRecipe));
    await loadSavedRecipes();
});

try {
    const authState = await initAuth();
    if (!authState.user && isAuthConfigured()) {
        window.location.assign("/");
    }
} catch (error) {
    console.error("Auth initialization failed:", error);
}
