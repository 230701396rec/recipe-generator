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
const authStatus = document.getElementById("auth-status");
const statusMessage = document.getElementById("status-message");
const savedStatus = document.getElementById("saved-status");
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
                    <strong>${recipe.favorite ? "Favorite" : "Saved Recipe"}</strong>
                    <button type="button" class="ghost-button favorite-button" data-favorite="${recipe.favorite}">
                        ${recipe.favorite ? "Unfavorite" : "Favorite"}
                    </button>
                </div>
                <p class="recipe-meta">${recipe.createdAt || "Just now"}</p>
                <p class="recipe-meta">${Array.isArray(recipe.ingredients) ? recipe.ingredients.join(", ") : (recipe.ingredients || "No ingredients provided.")}</p>
                <pre>${recipe.generatedRecipe}</pre>
            </div>
        </article>
    `;
}

async function loadSavedRecipes() {
    if (!isAuthConfigured()) {
        savedStatus.textContent = "Easy Auth is not available in this environment.";
        savedRecipes.innerHTML = "";
        return;
    }

    if (!isAuthEnabled()) {
        savedStatus.textContent = "Your session is missing. Please sign in again.";
        savedRecipes.innerHTML = "";
        window.location.assign("/");
        return;
    }

    try {
        savedStatus.textContent = "Loading your saved recipes...";
        const data = await apiRequest("/my-recipes");

        if (!data.recipes.length) {
            savedRecipes.innerHTML = "";
            savedStatus.textContent = "No recipes saved yet.";
            return;
        }

        savedRecipes.innerHTML = data.recipes.map(recipeCardTemplate).join("");
        savedStatus.textContent = `${data.recipes.length} recipe(s) loaded.`;
    } catch (error) {
        savedRecipes.innerHTML = "";
        savedStatus.textContent = error.message;
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

savedRecipes.addEventListener("click", async (event) => {
    const target = event.target.closest(".favorite-button");
    if (!target) {
        return;
    }

    const recipeCard = target.closest(".recipe-card");
    const recipeId = recipeCard?.dataset.recipeId;
    if (!recipeId) {
        return;
    }

    const nextFavorite = target.dataset.favorite !== "true";

    try {
        savedStatus.textContent = "Updating favorite...";
        await apiRequest(`/favorite-recipes/${recipeId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ favorite: nextFavorite })
        });
        await loadSavedRecipes();
    } catch (error) {
        savedStatus.textContent = error.message;
    }
});

logoutButton.addEventListener("click", async () => {
    await logout();
});

onAuthStateChanged(async ({ enabled, user, error }) => {
    if (error) {
        authStatus.textContent = error.message;
        savedStatus.textContent = error.message;
        return;
    }

    if (!enabled) {
        authStatus.textContent = "Easy Auth is not available in this environment.";
        savedStatus.textContent = "Easy Auth is not available in this environment.";
        setRecipeActionsEnabled(false);
        return;
    }

    if (!user) {
        authStatus.textContent = "No active session found. Redirecting to sign in...";
        savedStatus.textContent = "Please sign in to access your dashboard.";
        setRecipeActionsEnabled(false);
        window.location.assign("/");
        return;
    }

    authStatus.textContent = `Signed in as ${user.email || user.userId}.`;
    setRecipeActionsEnabled(Boolean(currentRecipe));
    await loadSavedRecipes();
});

try {
    const authState = await initAuth();
    if (!authState.user && isAuthConfigured()) {
        authStatus.textContent = "No active session found. Redirecting to sign in...";
        window.location.assign("/");
    } else if (!authState.user) {
        authStatus.textContent = "Easy Auth is not available in this environment.";
        savedStatus.textContent = "Easy Auth is not available in this environment.";
    }
} catch (error) {
    authStatus.textContent = error.message;
    savedStatus.textContent = error.message;
}
