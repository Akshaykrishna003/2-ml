# PS-23 Security and Robustness Findings

## Scope and result

Checks were local and static/dynamic with non-executable source strings. No student submission was run, no external service contacted, and no serialized model artifact was loaded. The inspected project contains no trained model file.

### Executed

- Unit regression for malformed and deeply nested Python syntax.
- Oversized text handling (2,000,000-character processor ceiling).
- Marker-file test confirming AST, token, and identifier analysis do not execute source.
- Dataset JSONL round-trip using the standard JSON parser; malformed JSON raises its documented decode error.
- Invalid dataset destination test verifies filesystem errors propagate rather than returning success.
- Source scan for `eval`, `exec`, `pickle`, `marshal`, `shelve`, subprocess use, and `os.system`; no matches in Python source.
- Full pytest suite: 32 passed.

### Findings

| Severity | Finding | Status |
|---|---|---|
| Informational | No executable-code evaluation or unsafe deserialization is used by the source-analysis utilities or synthetic data writer. | No issue observed in tested paths. |
| Low | The 2,000,000-character limit bounds each source string, but callers can still submit many sources concurrently; no aggregate request quota or concurrency limiter is in scope. | Unresolved integration risk. |
| Low | `tracemalloc` performance measurements exclude native allocations and process resident memory. | Measurement limitation, not a discovered vulnerability. |

No dedicated security scanner was available in the environment (Bandit, Semgrep, pip-audit, and Safety were not found). Dependency vulnerability scanning, concurrent-request exhaustion tests, filesystem symlink/race testing, and deployment/API boundary review were not performed.

## Limitations

- `ast.parse` and tokenization do not execute submission code, but this does not establish safety for other application components that may later execute or import submissions.
- Input size limits apply per string and do not guarantee protection against aggregate memory pressure in an unbounded caller.
- No claim is made about deployment hardening or third-party dependency vulnerability status.
