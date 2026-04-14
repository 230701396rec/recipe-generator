const form = document.getElementById("recipe-form");
const generateButton = document.getElementById("generate-button");
const statusMessage = document.getElementById("status-message");
const recipeOutput = document.getElementById("recipe-output");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(form);

    generateButton.disabled = true;
    statusMessage.textContent = "Generating recipe...";
    recipeOutput.textContent = "Please wait while your recipe is being created.";

    try {
        const response = await fetch("/generate", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Something went wrong.");
        }

        recipeOutput.textContent = data.recipe;
        statusMessage.textContent = "Recipe generated successfully.";
    } catch (error) {
        recipeOutput.textContent = "";
        statusMessage.textContent = "Recipe generation failed.";
        recipeOutput.textContent = error.message;
    } finally {
        generateButton.disabled = false;
    }
});
