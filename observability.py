import os
from contextlib import contextmanager
from typing import Any, Iterator

from dotenv import load_dotenv

load_dotenv()

from opentelemetry import context as otel_context

_langfuse_client = None


def _get_langfuse():
    global _langfuse_client
    if _langfuse_client is None:
        from langfuse import get_client

        _langfuse_client = get_client()
    return _langfuse_client


def trace_metadata(tenant_id: str, item_id: str, **extra: Any) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "item_id": item_id,
        "environment": os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"),
        **extra,
    }


@contextmanager
def current_observation(
    *,
    name: str,
    as_type: str = "span",
    tenant_id: str | None = None,
    item_id: str | None = None,
    input: Any = None,
    metadata: Any = None,
) -> Iterator[Any]:
    with _get_langfuse().start_as_current_observation(
        name=name,
        as_type=as_type,
        input=input,
        metadata=metadata,
    ) as observation:
        yield observation


def flush_traces() -> None:
    _get_langfuse().flush()


@contextmanager
def propagate_trace_attributes(**attributes: Any) -> Iterator[None]:
    from langfuse import propagate_attributes

    with propagate_attributes(**attributes):
        yield


def inject_trace_headers(headers: dict[str, str]) -> dict[str, str]:
    from opentelemetry.propagate import inject

    inject(headers)
    return headers


@contextmanager
def extracted_trace_context(headers: Any) -> Iterator[None]:
    from opentelemetry.propagate import extract

    context = extract(dict(headers))
    token = otel_context.attach(context)
    try:
        yield
    finally:
        otel_context.detach(token)