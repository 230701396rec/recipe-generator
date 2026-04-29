import os
import logging
from collections import deque
from time import perf_counter, time

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request

from routes.recipe_routes import create_recipe_blueprint
from services.blob_service import BlobService
from services.recipe_service import RecipeGenerationService


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_SAMPLES_LIMIT = 80
request_samples = deque(maxlen=REQUEST_SAMPLES_LIMIT)

# Application Insights reads telemetry from this connection string.
# Keep the value in environment variables or Azure App Settings, never in code.
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv(
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
    "",
).strip()

if APPLICATIONINSIGHTS_CONNECTION_STRING:
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry import metrics, trace

        # Azure Monitor OpenTelemetry auto-tracks Flask requests, exceptions, and logs.
        configure_azure_monitor(
            connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING,
        )
        tracer = trace.get_tracer(__name__)
        meter = metrics.get_meter(__name__)
        request_duration_histogram = meter.create_histogram(
            "recipegenie.server.response_time",
            unit="ms",
            description="Server response time for RecipeGenie Flask requests.",
        )
        availability_histogram = meter.create_histogram(
            "recipegenie.server.availability",
            unit="%",
            description="Per-request availability value. Successful requests record 100, server failures record 0.",
        )
        request_counter = meter.create_counter(
            "recipegenie.server.requests",
            unit="1",
            description="Total RecipeGenie Flask requests.",
        )
        failed_request_counter = meter.create_counter(
            "recipegenie.server.failed_requests",
            unit="1",
            description="Total RecipeGenie Flask requests with 5xx responses.",
        )
    except Exception:
        logger.exception(
            "Azure Monitor telemetry could not be configured. "
            "Verify azure-monitor-opentelemetry is installed and "
            "APPLICATIONINSIGHTS_CONNECTION_STRING is valid."
        )
        tracer = None
        request_duration_histogram = None
        availability_histogram = None
        request_counter = None
        failed_request_counter = None
else:
    tracer = None
    request_duration_histogram = None
    availability_histogram = None
    request_counter = None
    failed_request_counter = None


def _record_server_telemetry(sample):
    attributes = {
        "http.method": sample["method"],
        "http.route": request.endpoint or sample["path"],
        "http.status_code": sample["status"],
        "recipegenie.available": sample["available"],
    }

    if request_duration_histogram:
        request_duration_histogram.record(sample["durationMs"], attributes)
    if availability_histogram:
        availability_histogram.record(100 if sample["available"] else 0, attributes)
    if request_counter:
        request_counter.add(1, attributes)
    if failed_request_counter and not sample["available"]:
        failed_request_counter.add(1, attributes)

    current_span = trace.get_current_span() if tracer else None
    if current_span:
        current_span.set_attribute("recipegenie.response_time_ms", sample["durationMs"])
        current_span.set_attribute("recipegenie.available", sample["available"])


def create_app():
    app = Flask(__name__)

    @app.before_request
    def start_request_timer():
        g.request_started_at = perf_counter()

    @app.after_request
    def capture_request_metrics(response):
        if request.path.startswith("/static/"):
            return response

        started_at = getattr(g, "request_started_at", None)
        if started_at is not None:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            sample = {
                "timestamp": int(time() * 1000),
                "path": request.path,
                "method": request.method,
                "status": response.status_code,
                "durationMs": duration_ms,
                "available": response.status_code < 500,
            }
            request_samples.append(sample)
            _record_server_telemetry(sample)

        return response

    blob_service = BlobService(
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip(),
        container_name=os.getenv("AZURE_BLOB_CONTAINER", "recipe-images").strip(),
        public_base_url=os.getenv("AZURE_BLOB_PUBLIC_BASE_URL", "").strip(),
        recipes_container_name=os.getenv("AZURE_RECIPES_CONTAINER", "recipes").strip(),
    )

    recipe_service = RecipeGenerationService(
        api_key=os.getenv("MISTRAL_API_KEY", "").strip(),
        model_name=os.getenv("MISTRAL_MODEL", "mistral-small-latest").strip(),
    )

    app.register_blueprint(
        create_recipe_blueprint(
            blob_service=blob_service,
            recipe_service=recipe_service,
        )
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/health")
    def health():
        # Example custom span/trace visible in Application Insights transaction details.
        if tracer:
            with tracer.start_as_current_span("health_check"):
                logger.info("Health check endpoint called")
        else:
            logger.info("Health check endpoint called")
        return jsonify({"status": "ok"}), 200

    @app.route("/metrics/summary")
    def metrics_summary():
        samples = list(request_samples)
        total = len(samples)
        successful = sum(1 for sample in samples if sample["available"])
        average_response_time = (
            round(sum(sample["durationMs"] for sample in samples) / total, 2)
            if total
            else 0
        )
        availability = round((successful / total) * 100, 2) if total else 100

        if tracer:
            with tracer.start_as_current_span("metrics_summary") as span:
                span.set_attribute(
                    "recipegenie.average_response_time_ms",
                    average_response_time,
                )
                span.set_attribute("recipegenie.availability_percent", availability)
                span.set_attribute("recipegenie.total_requests", total)

        return jsonify(
            {
                "averageResponseTimeMs": average_response_time,
                "availabilityPercent": availability,
                "totalRequests": total,
                "samples": samples,
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
