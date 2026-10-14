# Contributing

Use Python 3.10+ and a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . build
python -m unittest discover -s tests -v
```

For the actual SDK/OTLP integration:

```sh
python -m pip install -r requirements-integration.txt
python -m unittest discover -s tests_integration -v
```

Changes to parsing, graph reconstruction, policy validation or verdict logic need a focused accepted and rejected example. Preserve missing-measurement behavior. A failed command alone is insufficient evidence: demonstrate the intended rule code and case in its report.

Changing measurement semantics requires updating the measurement version and documenting baseline compatibility. Do not relax validation to accommodate missing telemetry without an explicit contract and a documented limitation.

All test data must be synthetic. Keep the core runtime dependency-free. Use standard libraries where they fit the task, maintain bounded reads and avoid printing raw trace content. Run `python -m build` and test the installed wheel before proposing package changes. CI checks platform behavior, the SDK integration and the composite Action itself.

The checked-in baseline is only for the synthetic example. Replacing it must be justified by an intentional fixture or contract change. Never generate a user's approved baseline automatically from an unreviewed candidate.
