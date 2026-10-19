from collections.abc import Callable
from uuid import UUID, uuid4

import structlog
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"


def _valid_request_id(value: str | None) -> str:
    if not value:
        return str(uuid4())
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid4())


def current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return trace.format_trace_id(span_context.trace_id)


def configure_telemetry(
    app: FastAPI,
    *,
    enabled: bool,
    service_name: str,
    environment: str,
    otlp_endpoint: str | None,
) -> None:
    if enabled:
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": service_name,
                    "deployment.environment.name": environment,
                }
            )
        )
        if otlp_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    tracer = trace.get_tracer(__name__)

    @app.middleware("http")
    async def correlate_request(
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = _valid_request_id(request.headers.get(REQUEST_ID_HEADER))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        try:
            with tracer.start_as_current_span("http.request.correlation") as span:
                span.set_attribute("request.id", request_id)
                response = await call_next(request)
                response.headers[REQUEST_ID_HEADER] = request_id
                trace_id = current_trace_id()
                if trace_id:
                    response.headers[TRACE_ID_HEADER] = trace_id
                return response
        finally:
            structlog.contextvars.clear_contextvars()
