from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from uuid import UUID, uuid4

import structlog
from fastapi import FastAPI, Request, Response
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"


@dataclass(frozen=True)
class OperationalMetrics:
    requests: object
    request_duration: object
    executions: object

    def record_execution(self, *, status: str, source: str) -> None:
        self.executions.add(1, {"execution.status": status, "execution.source": source})


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
    metrics_enabled: bool,
    service_name: str,
    environment: str,
    otlp_endpoint: str | None,
) -> OperationalMetrics:
    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment.name": environment,
        }
    )
    if enabled:
        provider = TracerProvider(resource=resource)
        if otlp_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    if metrics_enabled:
        metrics.set_meter_provider(
            MeterProvider(
                resource=resource,
                metric_readers=[PrometheusMetricReader()],
                views=[
                    View(
                        instrument_name="aieo.http.server.duration",
                        aggregation=ExplicitBucketHistogramAggregation(
                            boundaries=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10)
                        ),
                    )
                ],
            )
        )
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)
    operational_metrics = OperationalMetrics(
        requests=meter.create_counter(
            "aieo.http.server.requests",
            unit="{request}",
            description="Quantidade de requisições HTTP processadas.",
        ),
        request_duration=meter.create_histogram(
            "aieo.http.server.duration",
            unit="s",
            description="Duração das requisições HTTP.",
        ),
        executions=meter.create_counter(
            "aieo.executions",
            unit="{execution}",
            description="Quantidade de execuções por origem e estado final.",
        ),
    )

    @app.middleware("http")
    async def correlate_request(
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = _valid_request_id(request.headers.get(REQUEST_ID_HEADER))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        started_at = monotonic()
        response_status = 500
        try:
            with tracer.start_as_current_span("http.request.correlation") as span:
                span.set_attribute("request.id", request_id)
                response = await call_next(request)
                response_status = response.status_code
                response.headers[REQUEST_ID_HEADER] = request_id
                trace_id = current_trace_id()
                if trace_id:
                    response.headers[TRACE_ID_HEADER] = trace_id
                return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            attributes = {
                "http.request.method": request.method,
                "http.route": route_path,
                "http.response.status_code": response_status,
            }
            operational_metrics.requests.add(1, attributes)
            operational_metrics.request_duration.record(monotonic() - started_at, attributes)
            structlog.contextvars.clear_contextvars()
    return operational_metrics
