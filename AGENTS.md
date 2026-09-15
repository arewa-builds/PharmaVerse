# Agent Rules

## Token-Consuming Operations

- Run any operation that consumes tokens, credits, quota, or other billable usage only after explicit user confirmation.
- Run a confirmed token-consuming operation once only. Do not retry or rerun it automatically after success, partial success, timeout, or ambiguous output.
- Treat operations run by the user as part of the same usage budget. Do not run another consuming operation unless the user explicitly confirms again.
- Before requesting confirmation, prefer non-consuming checks such as dry runs, status queries, payload inspection, local validation, and metadata inspection.
- Clearly identify when a proposed command will consume tokens, credits, quota, or other billable usage.
