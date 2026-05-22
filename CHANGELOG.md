# Changelog

All notable changes to `quelvio-crewai` will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-23

Initial release.

### Added
- `QuelvioTool` — `crewai.tools.BaseTool` subclass for use inside CrewAI
  `Agent`s and `Crew`s. Returns a synthesized answer plus cited sources.
- `QuelvioClient` — thin httpx-based HTTP client (sync + async) for the
  Quelvio enterprise REST API. Bearer-token auth, `User-Agent` includes the
  package version, retries 502/503/504 with jittered exponential backoff.
- Typed exception hierarchy: `QuelvioError`, `QuelvioAuthError`,
  `QuelvioRateLimitError`, `QuelvioBadRequestError`, `QuelvioServerError`,
  `QuelvioNotFoundError`, `QuelvioTimeoutError`, `QuelvioNetworkError`.
- API key redaction in `repr()`, exception messages, and User-Agent — keys
  never appear in any log line.
- Configuration via `QUELVIO_API_KEY` and `QUELVIO_API_BASE` env vars.
- Pydantic v2 request / response models in `quelvio_crewai.types`.

[0.1.0]: https://github.com/Quelvio/quelvio-crewai-python/releases/tag/v0.1.0
