
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)


def configure_telemetry():
    # Avoid configuring the provider repeatedly on Streamlit reruns.
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return

    resource = Resource.create({
        "service.name": "aml-investigation-copilot",
        "deployment.environment": "demo",
    })

    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(
        endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "http://localhost:4318/v1/traces",
        ),
        timeout=3,
    )

    provider.add_span_processor(
        BatchSpanProcessor(exporter)
    )

    trace.set_tracer_provider(provider)


def get_tracer():
    return trace.get_tracer("aml-investigation-copilot")
