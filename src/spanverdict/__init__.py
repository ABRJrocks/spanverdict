"""Deterministic contracts for recorded agent telemetry."""

__version__ = "0.1.0"

from .baseline import capture_baseline
from .engine import evaluate
from .jsonio import InputError
from .otlp import load_spans, parse_batches
from .policy import load_policy, validate_policy
from .reports import OutputError, atomic_write, json_report, junit_report

__all__ = ["__version__", "capture_baseline", "evaluate", "InputError", "OutputError",
           "load_spans", "parse_batches", "load_policy", "validate_policy", "atomic_write",
           "json_report", "junit_report"]
