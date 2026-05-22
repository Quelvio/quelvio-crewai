# quelvio-crewai

> Quelvio for CrewAI — your company's brain as a CrewAI tool.

`quelvio-crewai` is the official Python integration that plugs Quelvio's
enterprise knowledge API into [CrewAI](https://docs.crewai.com). It ships
a single first-class building block — `QuelvioTool` — that drops onto
any CrewAI `Agent` and gives it on-demand access to your organization's
connected sources (Google Drive, SharePoint, Confluence, Slack, Notion,
and the rest of your content fabric), scoped to the running user's
individual permissions.

[![PyPI version](https://img.shields.io/pypi/v/quelvio-crewai.svg)](https://pypi.org/project/quelvio-crewai/)
[![Python versions](https://img.shields.io/pypi/pyversions/quelvio-crewai.svg)](https://pypi.org/project/quelvio-crewai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Why Quelvio (and not vanilla RAG)?

A naive RAG pipeline embeds every chunk it can find and ranks by cosine
similarity. That's why most internal copilots confidently quote a
three-year-old draft. Quelvio is a managed company-brain that does the
work a generic vector store can't:

- **Authority scoring.** Every chunk is ranked by *who authored it*, *how
  fresh it is*, and *how many downstream documents reference it* — not just
  semantic similarity to the question.
- **Lifecycle awareness.** Drafts, deprecated docs, and superseded
  decisions are demoted automatically; chunks return a `lifecycle_state`
  the LLM can quote when hedging.
- **Per-employee permissioning.** Every query is scoped to the running
  user's identity. Results never include documents the user can't already
  read in the source system (Drive ACLs, Confluence space restrictions,
  SharePoint groups).
- **Synthesized answers with citations.** The API returns a final answer
  *plus* the chunks that informed it, so your agent can hand the user a
  link to the source of truth, not a hallucination.

## Install

```bash
pip install quelvio-crewai crewai
```

Requires Python 3.10+ and `crewai>=0.55.0`.

## Quickstart

```python
from crewai import Agent, Task, Crew
from quelvio_crewai import QuelvioTool

researcher = Agent(
    role="Knowledge analyst",
    goal="Find authoritative answers from company knowledge",
    backstory=(
        "You answer questions using the company's connected knowledge "
        "brain and always cite the source URL you used."
    ),
    tools=[QuelvioTool(api_key="qlv_pat_...")],  # or set QUELVIO_API_KEY
)

task = Task(
    description="What's our refund policy?",
    expected_output="A short answer plus the source URLs that back it up.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
print(result)
```

The tool's name is `quelvio_query` and its schema accepts `question`
(required) plus optional `mode` (`fast` | `standard` | `deep`),
`max_sources` (1–50), and `domain` (taxonomy domain filter).

## Authentication

`quelvio-crewai` resolves a bearer token from the first non-empty
source, in order:

| Precedence | Source                          | Notes                                              |
| ---------- | ------------------------------- | -------------------------------------------------- |
| 1          | `api_key=...` constructor arg   | Highest priority; never persisted, never logged.   |
| 2          | `QUELVIO_API_KEY` env var       | Best for CI, notebooks, and one-off scripts.       |

Three token types are accepted — the wire format is identical, so the
library does not need to know which kind you provided:

- **Personal Access Token (PAT).** Long-lived bearer tied to a human
  user. Generate at <https://enterprise.quelvio.com/account> → *Personal
  API Keys* → *Create token*. Best for ad-hoc use and CI.
- **OAuth access token.** Short-lived token from the device-code flow
  (`quelvio login` in the [CLI](https://github.com/Quelvio/quelvio-cli)).
- **Service Account key.** Long-lived, machine-scoped. Generate at
  *Settings* → *Service Accounts*. Best for production agents.

The token is held privately on the client; it never appears in
`repr()`, exception messages, or any log line emitted by this library.

## Configuration

| Constructor arg / env var       | Default                       | Purpose                                            |
| ------------------------------- | ----------------------------- | -------------------------------------------------- |
| `api_key` / `QUELVIO_API_KEY`   | *(required)*                  | Bearer token (PAT, OAuth, or Service Account).     |
| `base_url` / `QUELVIO_API_BASE` | `https://api.quelvio.com`     | API base — point at `api-dev` for staging.         |
| `timeout`                       | `30.0` seconds                | Per-request HTTP timeout.                          |
| `default_max_sources`           | `5`                           | Chunks returned per query (1–50) if the agent omits `max_sources`. |
| `default_mode`                  | `"standard"`                  | `fast` / `standard` / `deep` if the agent omits `mode`. |

## Authority & lifecycle

Every chunk returned to the agent carries Quelvio's authority signals,
and the tool's formatted output preserves them in the citation list so
your agent can quote them back to the user:

- **Authority score.** A 0–1 ranking that blends author seniority,
  source freshness, and downstream reference count. Chunks below
  ~0.3 are surfaced with an explicit `risk_flag.low_authority` so the
  agent can hedge.
- **Lifecycle state.** Drafts, deprecated docs, and superseded
  decisions are demoted automatically and labeled so the agent does
  not quote a doc that has been retired.
- **Coverage.** The `coverage` field tells the agent whether the
  taxonomy domain it queried is `complete`, `partial`, or `sparse` —
  useful to gate confident answers.

The Quelvio team rolls authority recomputes on a nightly cadence; you
don't need to maintain anything client-side.

## Examples

### 1. Single-agent Q&A

```python
from crewai import Agent, Task, Crew
from quelvio_crewai import QuelvioTool

agent = Agent(
    role="Onboarding buddy",
    goal="Answer new hires' questions about company policies",
    backstory="You always cite the policy doc you used.",
    tools=[QuelvioTool()],  # reads QUELVIO_API_KEY
)

task = Task(
    description="What's our parental leave policy?",
    expected_output="The current policy plus a link to the source doc.",
    agent=agent,
)

print(Crew(agents=[agent], tasks=[task]).kickoff())
```

### 2. Multi-agent crew (Quelvio + web research + writer)

```python
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool
from quelvio_crewai import QuelvioTool

quelvio = QuelvioTool()
web = SerperDevTool()

researcher = Agent(
    role="Internal researcher",
    goal="Find what THIS company has said about the topic",
    backstory="You only quote internal company sources.",
    tools=[quelvio],
)

analyst = Agent(
    role="Market analyst",
    goal="Find how competitors and the industry approach the topic",
    backstory="You only quote public web sources.",
    tools=[web],
)

writer = Agent(
    role="Executive brief writer",
    goal="Synthesize an internal vs. industry comparison",
    backstory="You always cite which research came from inside vs. outside.",
)

tasks = [
    Task(
        description="Summarize our current refund policy and its rationale.",
        expected_output="A short internal summary with source URLs.",
        agent=researcher,
    ),
    Task(
        description="Find how 3 industry peers handle refunds.",
        expected_output="Bullet list with URLs.",
        agent=analyst,
    ),
    Task(
        description="Write an executive brief comparing the two.",
        expected_output="A 2-paragraph brief.",
        agent=writer,
    ),
]

result = Crew(agents=[researcher, analyst, writer], tasks=tasks).kickoff()
print(result)
```

### 3. Hierarchical crew with a manager delegating to Quelvio specialists

```python
from crewai import Agent, Crew, Process, Task
from quelvio_crewai import QuelvioTool

quelvio = QuelvioTool()

finance_specialist = Agent(
    role="Finance knowledge specialist",
    goal="Answer finance-domain questions using Quelvio",
    backstory="You restrict Quelvio queries to the finance domain.",
    tools=[quelvio],
)

eng_specialist = Agent(
    role="Engineering knowledge specialist",
    goal="Answer engineering-domain questions using Quelvio",
    backstory="You restrict Quelvio queries to the engineering domain.",
    tools=[quelvio],
)

task = Task(
    description=(
        "An employee asks: 'What's our approval process for buying a new "
        "GPU cluster?'. Delegate to whichever specialist is best placed "
        "to answer."
    ),
    expected_output="A consolidated answer plus the source URLs used.",
)

crew = Crew(
    agents=[finance_specialist, eng_specialist],
    tasks=[task],
    process=Process.hierarchical,
    manager_llm="gpt-4o",  # the routing model
)

print(crew.kickoff())
```

## Related packages

- **[`quelvio-langchain`](https://github.com/Quelvio/quelvio-langchain-python)** —
  the same brain as a LangChain `Retriever` and `Tool`.
- **[`@quelvio/cli`](https://github.com/Quelvio/quelvio-cli)** — query the
  brain from your terminal, scriptable in CI, JSON output.
- **[`@quelvio/mcp-server`](https://github.com/Quelvio/quelvio-mcp-server)** —
  use Quelvio from any Model Context Protocol client (Claude Desktop,
  Cursor, VS Code, etc.).
- **[Quelvio docs](https://docs.quelvio.com)** — concepts, API reference,
  source connectors.

## Development

```bash
git clone https://github.com/Quelvio/quelvio-crewai-python
cd quelvio-crewai-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Linting and type-checking:

```bash
ruff check src tests
ruff format --check src tests
mypy src
```

## Contributing

Issues and pull requests welcome at
<https://github.com/Quelvio/quelvio-crewai-python>. Please run `ruff
check`, `ruff format`, `mypy`, and `pytest` before opening a PR.

## License

MIT — see [LICENSE](./LICENSE).
