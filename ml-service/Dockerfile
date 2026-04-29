# ML service Docker image
FROM python:3.10-slim

# Prevent Python from writing pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# App directory inside the container
WORKDIR /app

# Install Python dependencies first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the ML service source
COPY . .

# Flask ML service listens on port 6000
EXPOSE 6000

# Start the Flask app (expects app.py in ml-service/)
CMD ["python", "app.py"]
