from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Total number of predictions",
    ["result"],
)
PREDICTION_DURATION = Histogram(
    "prediction_duration_seconds",
    "Time spent on ML model inference",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
PREDICTION_ERRORS_TOTAL = Counter(
    "prediction_errors_total",
    "Total number of prediction errors",
    ["error_type"],
)
DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
)
MODEL_PREDICTION_PROBABILITY = Histogram(
    "model_prediction_probability",
    "Distribution of violation probabilities from model",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)


def observe_prediction_result(is_violation: bool, probability: float) -> None:
    label = "violation" if is_violation else "no_violation"
    PREDICTIONS_TOTAL.labels(result=label).inc()
    MODEL_PREDICTION_PROBABILITY.observe(float(probability))


def observe_prediction_error(error_type: str) -> None:
    PREDICTION_ERRORS_TOTAL.labels(error_type=error_type).inc()


def observe_db_query_duration(query_type: str, started_at: float) -> None:
    DB_QUERY_DURATION.labels(query_type=query_type).observe(time.perf_counter() - started_at)


@contextmanager
def track_prediction_duration() -> Iterator[None]:
    started_at = time.perf_counter()
    try:
        yield
    finally:
        PREDICTION_DURATION.observe(time.perf_counter() - started_at)
