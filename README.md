# Recipe Generator

Recipe Generator is a Flask web application that creates recipes from user-provided ingredients, stores saved recipes as JSON files in Azure Blob Storage, and uploads recipe images to Azure Blob Storage.

## Project structure

```text
recipe-generator/
|
|-- app.py
|-- routes/
|   |-- recipe_routes.py
|-- services/
|   |-- blob_service.py
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

AZURE_STORAGE_CONNECTION_STRING=your_blob_connection_string
AZURE_BLOB_CONTAINER=recipe-images
AZURE_RECIPES_CONTAINER=recipes
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
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_BLOB_CONTAINER`
- `AZURE_RECIPES_CONTAINER` (optional, defaults to `recipes`)
- `AZURE_BLOB_PUBLIC_BASE_URL` (optional)
- `APPLICATIONINSIGHTS_CONNECTION_STRING` (optional, enables Azure Application Insights telemetry)

Do not hardcode secrets in the code.

## Application Insights telemetry

When `APPLICATIONINSIGHTS_CONNECTION_STRING` is configured, the app sends the normal Flask request telemetry plus these custom metrics:

- `recipegenie.server.response_time`
- `recipegenie.server.availability`
- `recipegenie.server.requests`
- `recipegenie.server.failed_requests`

Example Kusto queries in Application Insights Logs:

```kusto
customMetrics
| where name == "recipegenie.server.response_time"
| summarize avg(value) by bin(timestamp, 5m)
| render timechart
```

```kusto
customMetrics
| where name == "recipegenie.server.availability"
| summarize availabilityPercent = avg(value) by bin(timestamp, 5m)
| render timechart
```

## API routes

- `POST /generate` keeps the original public recipe generation flow.
- `POST /generate-recipe` generates a recipe using the same backend recipe flow.
- `POST /save-recipe` saves a generated recipe as a JSON blob and optionally uploads an image.
- `GET /my-recipes` keeps the existing route available and currently returns an empty list in Blob-only mode.
- `POST /favorite-recipes/<recipe_id>` keeps the existing route available but favorite updates are not supported in Blob-only mode.
- `GET /admin/recipes` keeps the existing route available and currently returns an empty list in Blob-only mode.

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
