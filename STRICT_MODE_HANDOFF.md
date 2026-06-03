# Strict-Mode Sentinel Handoff (FE-13)

> **Docs PR.** The full reference implementation lives in
> [`Quelvio/quelvio-mcp-server`](https://github.com/Quelvio/quelvio-mcp-server/blob/main/STRICT_MODE_HANDOFF.md).
> This file copies the contract so an engineer touching `quelvio-crewai`
> can mirror the pattern locally without context-switching across repos.

## What backend PR #643 ships

Backend PR #643 emits two response headers globally on the search /
retrieval endpoints:

| Header | Value | Meaning |
| --- | --- | --- |
| `X-Quelvio-API-Version` | `2.0` | API contract version. Informational. |
| `X-Quelvio-Sentinel-Set` | `closed-v1` | Tenant is on the strict (closed) permission model. Some results may be filtered. |

When the sentinel header is present, SDK consumers may see fewer search
results than expected — the strict model only returns chunks for which
the calling employee has explicit access.

## Contract

When this CrewAI tool observes `X-Quelvio-Sentinel-Set` on any response:

1. Log a warning **once per process** (idempotent). Warning text:
   ```
   Quelvio v2 strict permission mode is active for your tenant.
   Some search results may be filtered to enforce explicit permissions.
   Learn more: https://docs.quelvio.com/permission-model
   ```
2. Surface via `logging.getLogger("quelvio_crewai").warning(...)`.
   CrewAI uses stdlib logging. Never raise.
3. Prefix with the structured event token
   `quelvio_sentinel_set_detected sentinel=<value>`.

## Where to wire it in `quelvio-crewai`

This SDK uses `httpx`. Use the `event_hooks` parameter on the
`httpx.Client` constructed in `src/quelvio_crewai/client.py:237`.

Suggested layout (identical to the other two Python SDKs — these three
share `client.py` structure):

- `src/quelvio_crewai/sentinel.py` — module-level `set[str]` of observed
  values + `threading.Lock` + `note_sentinel` function with the
  once-per-process emission.
- Register on both `httpx.Client` and `httpx.AsyncClient` via
  `event_hooks={"response": [note_sentinel]}`.
- Pytest case under `tests/` using `respx` or `httpx.MockTransport` plus
  `caplog`.

## Implementation crib

The full Python pattern (code included) lives in
[`quelvio-langchain-python`](https://github.com/Quelvio/quelvio-langchain-python/blob/main/STRICT_MODE_HANDOFF.md)'s
handoff doc. The TypeScript reference lives in
[`quelvio-mcp-server`](https://github.com/Quelvio/quelvio-mcp-server/blob/main/src/sentinel.ts).

## Owner

FE-13 / antonis@rolle.io. Backend counterpart: PR #643 on
`Quelvio/quelvio-platform`.
