"""Bounded input and unambiguous JSON for policies, exports and baselines."""

import json
import math
from pathlib import Path


class InputError(ValueError):
    """Input cannot be evaluated without guessing."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("Duplicate JSON object member")
        result[key] = value
    return result


def _constant(value):
    raise InputError("Non-finite JSON number")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InputError("Non-finite JSON number")
    return result


def decode(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float)
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError("Invalid JSON document") from exc


def read_text(path, limit=64 * 1024 * 1024):
    try:
        with Path(path).open("rb") as source:
            data = source.read(limit + 1)
        if len(data) > limit:
            raise InputError("Input exceeds byte limit")
        return data.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputError("Input cannot be read as UTF-8") from exc


def read_json(path, limit=1024 * 1024):
    return decode(read_text(path, limit))
