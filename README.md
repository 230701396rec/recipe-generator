# Recipe Generator

Recipe Generator is a simple Flask web application that creates recipes from ingredients entered by the user. It uses the Mistral AI API and is ready to deploy to Azure Web App from GitHub.

## Project structure

```text
recipe-generator/
|
|-- app.py
|-- requirements.txt
|-- Procfile
|-- runtime.txt
|-- README.md
|-- .gitignore
|-- templates/
|   |-- index.html
|-- static/
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

Do not hardcode secrets in the code.

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
2. In Azure, create a Linux Web App using Python 3.11.
3. Connect the Web App to your GitHub repository.
4. Azure will install dependencies from `requirements.txt` and start the app with gunicorn.

## Git commands

Use these commands to push your latest Azure-ready changes:

```text
git add .
git commit -m "Configure project for Azure deployment"
git push origin main
```
