"""Self-contained, script-free release evidence for human review."""

from html import escape
import json

from . import __version__

MESSAGES = {
    "budget_exceeded": "Run exceeded its metric budget",
    "missing_measurement": "Required usage measurement was not recorded",
    "tool_not_allowed": "Tool was outside the reviewed allow list",
    "required_tool_missing": "Required successful tool execution was missing",
    "tool_calls_exceeded": "Tool call count exceeded its allowance",
    "tool_order": "Successful prerequisite did not finish before this call",
    "case_coverage": "Expected case has insufficient recorded runs",
    "unexpected_case": "Recorded case is outside the reviewed suite",
    "regression": "Case p95 exceeded the approved baseline allowance",
}

CSS = """
:root{color-scheme:light;--paper:#fbfbfa;--ink:#2f3437;--muted:#686864;--line:#eaeaea;--bad:#9f2f2d;--good:#346538}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 'Helvetica Neue',Arial,sans-serif}
main{max-width:1120px;margin:auto;padding:40px 48px 72px}header{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:18px}
.brand{font-weight:700;letter-spacing:-.04em;font-size:21px}.meta,.eyebrow{font:11px/1.6 'SF Mono',Consolas,monospace;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.hero{padding:52px 0 36px;border-bottom:1px solid var(--line)}h1{font:clamp(42px,6vw,72px)/1.06 Georgia,serif;letter-spacing:-.045em;margin:14px 0 20px;max-width:900px}
.intro{max-width:700px;color:var(--muted)}.status{display:inline-block;padding:3px 9px;background:#edf3ec;color:var(--good);font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;border-radius:4px}
.status.bad{background:#fdebec;color:var(--bad)}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;padding:30px 0}.stat b{display:block;font-size:32px;letter-spacing:-.04em;font-weight:500}.stat span{color:var(--muted);font-size:12px}
h2{font-size:20px;letter-spacing:-.025em;margin:40px 0 14px}h3{font-size:18px;margin:0}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap}th,td{text-align:left;padding:13px 16px 13px 0;border-bottom:1px solid var(--line);font-size:13px}
th{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:500}td.number{font-variant-numeric:tabular-nums}code{font:12px/1.6 'SF Mono',Consolas,monospace;overflow-wrap:anywhere}
.case{border-top:1px solid var(--line);padding:26px 0}.case-head{display:flex;align-items:center;justify-content:space-between;gap:20px}.issue{padding:14px 0;border-bottom:1px solid var(--line)}.issue p{margin:2px 0;color:var(--muted);font-size:13px}.issue strong{font-size:14px;color:var(--bad)}
details{border-bottom:1px solid var(--line);padding:16px 0}summary{cursor:pointer;display:list-item;font-size:13px}summary code{margin-left:8px}details p{font-size:13px;color:var(--muted)}.hash{color:var(--muted);font-size:11px;margin-top:24px}
footer{margin-top:48px;border-top:1px solid var(--line);padding-top:20px;color:var(--muted);font-size:12px;max-width:800px}
@media(max-width:600px){main{padding:24px 20px 48px}.hero{padding-top:36px}.stats{gap:12px}.stat b{font-size:26px}.case-head{align-items:flex-start}.meta{font-size:9px}}
@media print{main{padding:0;max-width:none}body{background:white}details{break-inside:avoid}.case{break-inside:avoid}}
"""


def _value(value):
    if value is None:
        return "Unmeasured"
    return f"{value:,.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"


def _issues(values):
    result = []
    for issue in values:
        details = {key: value for key, value in issue.items() if key != "code"}
        result.append('<div class="issue"><strong>' + escape(MESSAGES.get(issue["code"],issue["code"])) +
                      '</strong><p><code>' + escape(json.dumps(details,sort_keys=True)) + '</code></p></div>')
    return "".join(result)


def html_report(result):
    passed = result["passed"]
    badge = '<span class="status' + ('' if passed else ' bad') + '">' + ('Accepted' if passed else 'Blocked') + '</span>'
    title = 'Recorded runs meet the contract.' if passed else 'This release needs attention.'
    output = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
              '<title>SpanVerdict / ' + escape(result["name"]) + '</title><style>' + CSS + '</style></head><body><main>',
              '<header><div class="brand">SpanVerdict</div><div class="meta">Agent execution report / ' + __version__ + '</div></header>',
              '<section class="hero"><div class="eyebrow">' + escape(result["name"]) + ' / Release evidence</div>',
              '<h1>' + title + '</h1>' + badge + '<p class="intro">Deterministic checks against recorded OpenTelemetry spans. ',
              'Review the failed cases before approving a change to the agent, prompt or tool routing.</p></section><section class="stats">']
    for key, caption in (("cases","Cases checked"),("runs","Recorded runs"),("failures","Failed checks")):
        output.append('<div class="stat"><b>' + str(result["summary"][key]) + '</b><span>' + caption + '</span></div>')
    output.append('</section><h2>Case comparison</h2><p class="intro">Nearest-rank p95 for each case. Run budgets are checked individually.</p><div class="table-wrap"><table><thead><tr><th>Case</th><th>Verdict</th><th>Runs</th><th>Latency, ms</th><th>Input tokens</th><th>Output tokens</th></tr></thead><tbody>')
    for case in result["cases"]:
        failures = len(case["issues"]) + sum(len(run["issues"]) for run in case["runs"])
        output.append('<tr><td><code>' + escape(case["id"]) + '</code></td><td>' + ('Blocked' if failures else 'Accepted') + '</td><td>' + str(len(case["runs"])) + '</td>')
        for metric in ("duration_ms","input_tokens","output_tokens"):
            output.append('<td class="number">' + _value(case["p95"][metric]) + '</td>')
        output.append('</tr>')
    output.append('</tbody></table></div><h2>Execution findings</h2>')
    for case in result["cases"]:
        output.append('<section class="case"><div class="case-head"><h3>' + escape(case["id"]) + '</h3><span class="meta">' + str(len(case["runs"])) + ' recorded runs</span></div>')
        output.append(_issues(case["issues"]))
        for run in case["runs"]:
            output.append('<details' + (' open' if run["issues"] else '') + '><summary>' + ('Blocked run' if run["issues"] else 'Accepted run') + '<code>' + escape(run["trace_id"]) + '</code></summary>')
            output.append('<p>' + ' &middot; '.join(escape(key.replace('_',' ')) + ': ' + _value(value) for key,value in sorted(run["metrics"].items())) + '</p>')
            output.append(_issues(run["issues"]) + '</details>')
        output.append('</section>')
    output.append('<p class="hash">Policy SHA-256<br><code>' + escape(result["policy_sha256"]) + '</code><br>Evidence projection SHA-256<br><code>' + escape(result["evidence_sha256"]) + '</code></p>')
    output.append('<footer>SpanVerdict checks observed execution, not answer correctness or runtime authorization. Sampling and unrecorded operations can hide behavior. Reports omit prompts, responses, tool arguments and arbitrary attributes; case IDs, trace IDs, tool labels and measured usage remain. Review before sharing.</footer></main></body></html>\n')
    return ''.join(output)
