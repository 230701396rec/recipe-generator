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
const refreshMetricsButton = document.getElementById("refresh-metrics-button");
const statusMessage = document.getElementById("status-message");
const metricsStatus = document.getElementById("metrics-status");
const recipeOutput = document.getElementById("recipe-output");
const savedRecipes = document.getElementById("saved-recipes");
const metricsChart = document.getElementById("metrics-chart");
const responseTimeValue = document.getElementById("response-time-value");
const availabilityValue = document.getElementById("availability-value");
const requestCountValue = document.getElementById("request-count-value");

let currentRecipe = "";
let metricsPollTimer = null;

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

function drawEmptyChart(ctx, width, height, message) {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#736b5e";
    ctx.font = "14px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(message, width / 2, height / 2);
}

function drawMetricsChart(samples) {
    if (!metricsChart) return;

    const ctx = metricsChart.getContext("2d");
    const width = metricsChart.width;
    const height = metricsChart.height;
    const padding = { top: 24, right: 34, bottom: 42, left: 54 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    ctx.clearRect(0, 0, width, height);

    if (!samples.length) {
        drawEmptyChart(ctx, width, height, "No request data yet. Refresh or use the app to create samples.");
        return;
    }

    const maxDuration = Math.max(100, ...samples.map((sample) => sample.durationMs));
    const xForIndex = (index) => {
        if (samples.length === 1) return padding.left + chartWidth;
        return padding.left + (index / (samples.length - 1)) * chartWidth;
    };
    const yForDuration = (duration) => padding.top + chartHeight - (duration / maxDuration) * chartHeight;
    const yForAvailability = (isAvailable) => padding.top + chartHeight - (isAvailable ? chartHeight : 0);

    ctx.strokeStyle = "#efe6dc";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i <= 4; i += 1) {
        const y = padding.top + (i / 4) * chartHeight;
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
    }
    ctx.stroke();

    ctx.fillStyle = "#736b5e";
    ctx.font = "12px Inter, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(`${Math.round(maxDuration)} ms`, padding.left - 10, padding.top + 4);
    ctx.fillText("0 ms", padding.left - 10, padding.top + chartHeight + 4);

    ctx.textAlign = "left";
    ctx.fillText("100%", width - padding.right + 8, padding.top + 4);
    ctx.fillText("0%", width - padding.right + 8, padding.top + chartHeight + 4);

    ctx.strokeStyle = "#2f7d6b";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    samples.forEach((sample, index) => {
        const x = xForIndex(index);
        const y = yForAvailability(sample.available);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.strokeStyle = "#ff6b4a";
    ctx.lineWidth = 3;
    ctx.beginPath();
    samples.forEach((sample, index) => {
        const x = xForIndex(index);
        const y = yForDuration(sample.durationMs);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    samples.forEach((sample, index) => {
        const x = xForIndex(index);
        const y = yForDuration(sample.durationMs);
        ctx.fillStyle = sample.available ? "#ff6b4a" : "#c0392b";
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
    });

    ctx.fillStyle = "#2c2925";
    ctx.font = "12px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("Response time", padding.left, height - 14);
    ctx.fillStyle = "#2f7d6b";
    ctx.fillText("Availability", padding.left + 120, height - 14);
}

async function loadMetrics() {
    if (!metricsChart) return;

    try {
        const data = await apiRequest("/metrics/summary");
        const samples = Array.isArray(data.samples) ? data.samples : [];

        responseTimeValue.textContent = `${data.averageResponseTimeMs || 0} ms`;
        availabilityValue.textContent = `${data.availabilityPercent ?? 100}%`;
        requestCountValue.textContent = data.totalRequests || 0;
        metricsStatus.textContent = samples.length
            ? `Updated with the last ${samples.length} request${samples.length === 1 ? "" : "s"}.`
            : "Waiting for request data.";
        drawMetricsChart(samples);
    } catch (error) {
        metricsStatus.textContent = error.message;
        drawMetricsChart([]);
    }
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

refreshMetricsButton.addEventListener("click", async () => {
    await loadMetrics();
});

logoutButton.addEventListener("click", async () => {
    await logout();
});

onAuthStateChanged(async ({ enabled, user, error }) => {
    if (error) return;

    if (!enabled) {
        setRecipeActionsEnabled(false);
        savedRecipes.innerHTML = "<p>Sign-in is not configured locally.</p>";
        return;
    }

    if (!user) {
        setRecipeActionsEnabled(false);
        window.location.assign("/");
        return;
    }

    setRecipeActionsEnabled(Boolean(currentRecipe));
    await loadSavedRecipes();
});

try {
    await loadMetrics();
    metricsPollTimer = window.setInterval(loadMetrics, 10000);

    const authState = await initAuth();
    if (!authState.user && isAuthConfigured()) {
        window.location.assign("/");
    }
} catch (error) {
    console.error("Auth initialization failed:", error);
} finally {
    window.addEventListener("beforeunload", () => {
        if (metricsPollTimer) {
            window.clearInterval(metricsPollTimer);
        }
    });
}
