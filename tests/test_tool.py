"""Unit tests for ``QuelvioTool`` on top of CrewAI's ``BaseTool``."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from crewai.tools import BaseTool

from quelvio_crewai import QuelvioClient, QuelvioTool, QuelvioToolInput


def _make_tool(
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    **kwargs: Any,
) -> tuple[QuelvioTool, dict[str, Any]]:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content) if request.content else None
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = QuelvioClient(api_key=api_key, base_url=base_url, http_client=http_client)
    return QuelvioTool(client=client, **kwargs), captured


def test_tool_metadata_defaults_and_basetool_subclass() -> None:
    tool = QuelvioTool(api_key="qlv_pat_x")
    assert isinstance(tool, BaseTool)
    assert tool.name == "quelvio_query"
    assert "knowledge brain" in tool.description.lower()
    assert tool.args_schema is QuelvioToolInput


def test_tool_run_returns_formatted_string_with_sources(
    api_key: str, base_url: str, query_response_payload: dict[str, Any]
) -> None:
    tool, captured = _make_tool(api_key, base_url, query_response_payload)
    result = tool._run(question="what's our refund policy?")

    assert "Refunds are processed within 14 days" in result
    assert "Sources:" in result
    assert "[1] Refund Policy v3" in result
    assert "https://drive.example/refund-policy-v3" in result

    # And we hit the right path with the right body.
    assert captured["path"] == "/v1/enterprise/query"
    assert captured["body"]["query"] == "what's our refund policy?"
    # Confirm the agent's bearer token reached the wire.
    assert captured["auth"] == f"Bearer {api_key}"


def test_tool_passes_optional_fields_to_request(
    api_key: str, base_url: str, query_response_payload: dict[str, Any]
) -> None:
    tool, captured = _make_tool(api_key, base_url, query_response_payload)
    tool._run(
        question="who owns finance?",
        mode="fast",
        max_sources=3,
        domain="finance",
    )
    assert captured["body"]["mode"] == "fast"
    assert captured["body"]["limit"] == 3
    assert captured["body"]["domain_filter"] == "finance"


def test_tool_empty_question_raises_and_does_not_hit_network(
    api_key: str, base_url: str, query_response_payload: dict[str, Any]
) -> None:
    tool, captured = _make_tool(api_key, base_url, query_response_payload)
    with pytest.raises(ValueError):
        tool._run(question="   ")
    assert "path" not in captured


def test_tool_repr_and_errors_do_not_leak_api_key(api_key: str, base_url: str) -> None:
    """The bearer token must never surface in ``repr()`` nor in any exception
    raised from inside ``_run``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "bad token"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = QuelvioClient(
        api_key=api_key, base_url=base_url, http_client=http_client, max_retries=0
    )
    tool = QuelvioTool(client=client)

    assert api_key not in repr(tool)

    with pytest.raises(Exception) as exc_info:
        tool._run(question="anything")
    assert api_key not in str(exc_info.value)


def test_tool_is_usable_inside_crewai_agent(
    api_key: str, base_url: str, query_response_payload: dict[str, Any]
) -> None:
    """Smoke test: construct a CrewAI ``Agent`` with ``QuelvioTool`` so we
    fail loudly if the BaseTool contract drifts."""

    pytest.importorskip("crewai")
    from crewai import Agent

    tool, _ = _make_tool(api_key, base_url, query_response_payload)

    # No LLM call is issued — we only assert that the Agent accepts the
    # tool and exposes it via the ``tools`` attribute.
    agent = Agent(
        role="Knowledge analyst",
        goal="Find authoritative answers from company knowledge",
        backstory="You answer questions using the company's knowledge brain.",
        tools=[tool],
        allow_delegation=False,
        llm="gpt-4o-mini",  # never invoked
    )
    assert tool in agent.tools

    # And the tool still runs against our mock transport.
    out = tool._run(question="what's our refund policy?")
    assert "Refund Policy v3" in out
