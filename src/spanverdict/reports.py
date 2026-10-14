"""Private atomic report writes that protect evaluation evidence."""

import json
import os
from pathlib import Path
import tempfile
from xml.etree import ElementTree as ET


class OutputError(ValueError):
    """Output cannot be safely written."""


def protect_destinations(paths, protected=()):
    destinations = [Path(path) for path in paths]
    sources = [Path(path) for path in protected]
    for index, path in enumerate(destinations):
        if path.is_symlink():
            raise OutputError("Output destination must not be a symlink")
        for other in sources + destinations[:index]:
            try:
                same = path.resolve() == other.resolve() or (
                    path.exists() and other.exists() and os.path.samefile(path, other))
            except OSError as exc:
                raise OutputError("Cannot verify output destination") from exc
            if same:
                raise OutputError("Output conflicts with input or another report")


def atomic_write(path, text, *, protected=(), overwrite=True):
    path = Path(path)
    protect_destinations([path], protected)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".spanverdict-", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
        return path
    except (OSError, UnicodeError) as exc:
        raise OutputError("Cannot write output; existing baseline may require explicit replacement") from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def json_report(result):
    return json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"


def junit_report(result):
    suite = ET.Element("testsuite", name=result["name"])
    failed, total = 0, 0
    for case in result["cases"]:
        records = [("coverage-and-regressions", case["issues"])]
        records += [(run["trace_id"], run["issues"]) for run in case["runs"]]
        for name, issues in records:
            total += 1
            test = ET.SubElement(suite, "testcase", classname=case["id"], name=name)
            if issues:
                failed += 1
                ET.SubElement(test, "failure", message=", ".join(i["code"] for i in issues)).text = json_report(issues)
    suite.set("tests", str(total))
    suite.set("failures", str(failed))
    return ET.tostring(suite, encoding="unicode", xml_declaration=True) + "\n"
