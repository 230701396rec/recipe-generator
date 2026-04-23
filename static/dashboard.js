import {
    initAuth,
    isAuthConfigured,
    isAuthEnabled,
    logout,
    onAuthStateChanged
} from "./auth.js";

const form = document.getElementById("recipe-form");
const imageInput = document.getElementById("image");
const generateButton = document.getElementById("generate-button");
const saveButton = document.getElementById("save-button");
const refreshRecipesButton = document.getElementById("refresh-recipes-button");
const logoutButton = document.getElementById("logout-button");
const statusMessage = document.getElementById("status-message");
const recipeOutput = document.getElementById("recipe-output");
const savedRecipes = document.getElementById("saved-recipes");

let currentRecipe = "";

function setRecipeActionsEnabled(isEnabled) {
    saveButton.disabled = !isEnabled;
}

function resetRecipeOutput(message) {
    currentRecipe = "";
    recipeOutput.textContent = message;
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
                <pre>${recipe.generatedRecipe}</pre>
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
    recipeOutput.textContent = "Please wait while your recipe is being created.";

    try {
        const formData = new FormData(form);
        const data = await apiRequest("/generate-recipe", {
            method: "POST",
            body: formData
        });

        currentRecipe = data.recipe;
        recipeOutput.textContent = currentRecipe;
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
