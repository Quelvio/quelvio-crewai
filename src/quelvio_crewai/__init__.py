"""Quelvio for CrewAI — your company's brain as a CrewAI tool."""

from __future__ import annotations

from ._version import __version__
from .client import AsyncQuelvioClient, QuelvioClient
from .exceptions import (
    QuelvioAuthError,
    QuelvioBadRequestError,
    QuelvioError,
    QuelvioNetworkError,
    QuelvioNotFoundError,
    QuelvioRateLimitError,
    QuelvioServerError,
    QuelvioTimeoutError,
)
from .tool import QuelvioTool, QuelvioToolInput
from .types import (
    ChunkResult,
    DomainCoverage,
    DomainsListResponse,
    QueryMode,
    QueryRequest,
    QueryResponse,
    SourceChunk,
    SourceDetailResponse,
)

__all__ = [
    "AsyncQuelvioClient",
    "ChunkResult",
    "DomainCoverage",
    "DomainsListResponse",
    "QuelvioAuthError",
    "QuelvioBadRequestError",
    "QuelvioClient",
    "QuelvioError",
    "QuelvioNetworkError",
    "QuelvioNotFoundError",
    "QuelvioRateLimitError",
    "QuelvioServerError",
    "QuelvioTimeoutError",
    "QuelvioTool",
    "QuelvioToolInput",
    "QueryMode",
    "QueryRequest",
    "QueryResponse",
    "SourceChunk",
    "SourceDetailResponse",
    "__version__",
]
