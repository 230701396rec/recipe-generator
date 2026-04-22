# Recipe Generator

Recipe Generator is a Flask web application that creates recipes from user-provided ingredients, supports Azure AD B2C authentication, stores saved recipes in Azure Cosmos DB, and uploads recipe images to Azure Blob Storage.

## Project structure

```text
recipe-generator/
|
|-- app.py
|-- middleware/
|   |-- auth_middleware.py
|-- routes/
|   |-- recipe_routes.py
|-- services/
|   |-- blob_service.py
|   |-- cosmos_service.py
|   |-- recipe_service.py
|-- requirements.txt
|-- Procfile
|-- runtime.txt
|-- README.md
|-- .gitignore
|-- templates/
|   |-- index.html
|-- static/
|   |-- auth.js
|   |-- login.js
|   |-- style.css
|   |-- script.js
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root:

```env
MISTRAL_API_KEY=your_api_key_here
MISTRAL_MODEL=mistral-small-latest
PORT=8000

AZURE_B2C_TENANT_NAME=yourtenant
AZURE_B2C_TENANT_DOMAIN=yourtenant.onmicrosoft.com
AZURE_B2C_POLICY=B2C_1_signupsignin
AZURE_B2C_CLIENT_ID=your_spa_client_id
AZURE_B2C_AUDIENCE=your_api_app_client_id
AZURE_B2C_API_SCOPES=https://yourtenant.onmicrosoft.com/api/demo.read

AZURE_COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
AZURE_COSMOS_KEY=your_cosmos_key
AZURE_COSMOS_DATABASE=recipe-generator
AZURE_COSMOS_USERS_CONTAINER=users
AZURE_COSMOS_RECIPES_CONTAINER=recipes

AZURE_BLOB_CONNECTION_STRING=your_blob_connection_string
AZURE_BLOB_CONTAINER=recipe-images
AZURE_BLOB_PUBLIC_BASE_URL=https://yourstorageaccount.blob.core.windows.net/recipe-images
```

## Run locally

Start the app:

```bash
python app.py
```

Open this in your browser:

```text
http://127.0.0.1:8000
```

## Environment variables

The application reads these environment variables:

- `MISTRAL_API_KEY`
- `MISTRAL_MODEL` (optional, defaults to `mistral-small-latest`)
- `PORT`
- `AZURE_B2C_TENANT_NAME`
- `AZURE_B2C_TENANT_DOMAIN`
- `AZURE_B2C_POLICY`
- `AZURE_B2C_CLIENT_ID`
- `AZURE_B2C_AUDIENCE`
- `AZURE_B2C_API_SCOPES`
- `AZURE_B2C_REDIRECT_URI` (optional)
- `AZURE_B2C_POST_LOGOUT_REDIRECT_URI` (optional)
- `AZURE_COSMOS_ENDPOINT`
- `AZURE_COSMOS_KEY`
- `AZURE_COSMOS_DATABASE`
- `AZURE_COSMOS_USERS_CONTAINER`
- `AZURE_COSMOS_RECIPES_CONTAINER`
- `AZURE_BLOB_CONNECTION_STRING`
- `AZURE_BLOB_CONTAINER`
- `AZURE_BLOB_PUBLIC_BASE_URL` (optional)

Do not hardcode secrets in the code.

## API routes

- `POST /generate` keeps the original public recipe generation flow.
- `POST /generate-recipe` is the authenticated Azure AD B2C protected generation route.
- `POST /save-recipe` saves a generated recipe and optional image.
- `GET /my-recipes` returns recipes for the signed-in user.
- `POST /favorite-recipes/<recipe_id>` toggles favorite recipes.
- `GET /admin/recipes` is restricted to users with the `admin` role claim.

## Azure deployment

Deploy this repository to an Azure Web App on Linux with Python 3.14.

### Azure App Settings

Add these Application Settings in Azure:

- `SCM_DO_BUILD_DURING_DEPLOYMENT = true`
- `MISTRAL_API_KEY = <your_api_key>`
- `MISTRAL_MODEL = mistral-small-latest`

### Startup command

Use this startup command in Azure:

```text
gunicorn --bind=0.0.0.0:$PORT app:app
```

The app entry point is `app.py` and the Flask application instance is `app`, so `gunicorn app:app` is the correct base command.

### GitHub deployment flow

1. Push this project to GitHub.
2. In Azure, create a Linux Web App using Python 3.14.
3. Connect the Web App to your GitHub repository.
4. Azure will install dependencies from `requirements.txt` and start the app with gunicorn.

## Git commands

Use these commands to push your latest Azure-ready changes:

```text
git add .
git commit -m "Configure project for Azure deployment"
git push origin main
```
