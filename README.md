# Recipe Generator

Recipe Generator is a simple Flask web application that creates recipes from ingredients entered by the user. It uses the Mistral AI API and is structured to be easy to deploy to Azure Web App.

## Project structure

```text
recipe-generator/
|
|-- app.py
|-- requirements.txt
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

## Azure deployment note

This project is ready for Azure Web App. Use a Linux Python Web App and set the startup command to:

```text
gunicorn --bind 0.0.0.0:$PORT app:app
```

In Azure App Settings, add:

- `MISTRAL_API_KEY`
- `MISTRAL_MODEL`
- `PORT`
