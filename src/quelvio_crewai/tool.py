"""``QuelvioTool`` — a CrewAI ``BaseTool`` for agents.

Drop this tool onto a CrewAI ``Agent`` and the agent will be able to
*decide* whether to query the company's knowledge brain. The tool
returns a synthesized natural-language answer plus a list of cited
sources (titles + URLs), which the agent can quote back to the user.
"""

from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from .client import QuelvioClient
from .types import QueryResponse

_DEFAULT_DESCRIPTION = (
    "Query your company's knowledge brain. Searches the organization's "
    "connected sources (Google Drive, SharePoint, Confluence, Slack, "
    "Notion, and other internal systems) for an authoritative, cited "
    "answer. Use this whenever the user asks about internal company "
    "information — policies, processes, decisions, people, products, "
    "projects, or anything else that lives in the company's systems "
    "rather than on the public internet. The answer is scoped to the "
    "running user's individual access permissions, so results never "
    "include documents they cannot already see. Returns a synthesized "
    "answer plus a list of cited sources (titles + URLs)."
)


class QuelvioToolInput(BaseModel):
    """Arguments schema for :class:`QuelvioTool`.

    Modeled with Pydantic so CrewAI agents get a well-typed JSON Schema
    for function-calling.
    """

    model_config = ConfigDict(extra="ignore")

    question: str = Field(
        ...,
        description=(
            "The natural-language question to ask the company's knowledge "
            "brain. Phrase it as the user would ask it — do not pre-process "
            "or keyword-extract."
        ),
    )
    mode: str | None = Field(
        default=None,
        description=(
            "Synthesis depth: 'fast' for low-latency retrieval-only, "
            "'standard' (default) for retrieval + synthesis, 'deep' for "
            "multi-pass reasoning over a wider window."
        ),
    )
    max_sources: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Maximum number of source chunks to retrieve (1 to 50, default 5).",
    )
    domain: str | None = Field(
        default=None,
        description=(
            "Optional taxonomy domain to restrict retrieval to "
            "(e.g. 'engineering', 'legal', 'people-ops')."
        ),
    )


def _format_response(response: QueryResponse) -> str:
    """Render a :class:`QueryResponse` as a single string for the agent."""
    lines: list[str] = []
    if response.synthesis:
        lines.append(response.synthesis.strip())
        lines.append("")
    if response.results:
        lines.append("Sources:")
        for idx, chunk in enumerate(response.results, start=1):
            label = chunk.title or chunk.chunk_id
            if chunk.source_url:
                lines.append(f"  [{idx}] {label} — {chunk.source_url}")
            else:
                lines.append(f"  [{idx}] {label}")
    if not lines:
        return "No matching content was found in the company's knowledge brain."
    return "\n".join(lines).rstrip()


class QuelvioTool(BaseTool):
    """CrewAI agent tool backed by the Quelvio enterprise knowledge API.

    Example:
        >>> from crewai import Agent, Task, Crew
        >>> from quelvio_crewai import QuelvioTool
        >>> researcher = Agent(
        ...     role="Knowledge analyst",
        ...     goal="Find authoritative answers from company knowledge",
        ...     tools=[QuelvioTool(api_key="qlv_pat_...")],
        ... )

    Args:
        api_key: Quelvio Personal Access Token, OAuth access token, or
            Service Account key. Falls back to ``QUELVIO_API_KEY``.
        base_url: Override the API base URL.
        timeout: Per-request timeout in seconds.
        default_mode: Default synthesis mode if the agent omits ``mode``.
        default_max_sources: Default chunk limit if the agent omits ``max_sources``.
        client: Optionally inject a pre-built :class:`QuelvioClient`.
    """

    name: str = "quelvio_query"
    description: str = _DEFAULT_DESCRIPTION
    args_schema: type[BaseModel] = QuelvioToolInput

    api_key: str | None = Field(default=None, exclude=True, repr=False)
    base_url: str | None = None
    timeout: float = 30.0
    default_mode: str = "standard"
    default_max_sources: int = 5

    _client: QuelvioClient = PrivateAttr()

    def __init__(
        self,
        *,
        client: QuelvioClient | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if client is not None:
            self._client = client
        else:
            self._client = QuelvioClient(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        # Token now lives privately on ``self._client``; drop the public copy
        # so it can never leak via ``repr`` or model_dump.
        object.__setattr__(self, "api_key", None)

    def _run(
        self,
        question: str,
        mode: str | None = None,
        max_sources: int | None = None,
        domain: str | None = None,
    ) -> str:
        if not question or not question.strip():
            raise ValueError("question must be a non-empty string")
        response = self._client.query(
            query=question,
            limit=max_sources if max_sources is not None else self.default_max_sources,
            mode=mode or self.default_mode,
            domain_filter=domain,
        )
        return _format_response(response)
