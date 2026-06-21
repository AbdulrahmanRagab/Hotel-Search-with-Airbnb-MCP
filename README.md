# Hotel Search AI Assistant — MCP + LangGraph

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![LangGraph](https://img.shields.io/badge/langgraph-v1.1%2B-purple)
![LangChain](https://img.shields.io/badge/langchain-v1.2%2B-green)
![Gradio](https://img.shields.io/badge/gradio-v4%2B-orange)
![Groq](https://img.shields.io/badge/llm-groq%20llama--3.3--70b-yellow)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

---

## Overview

A production-grade terminal chatbot that lets users search for hotels and accommodations on Airbnb using **natural language**. It leverages the **Model Context Protocol (MCP)** to connect to an Airbnb MCP server, uses a **LangGraph state machine** to orchestrate a multi-step AI workflow, and provides both a **Rich-powered terminal UI** and a **Gradio web interface**.

The system parses free-form queries (e.g., *"Find a 2-bedroom apartment in Paris under $300 for next weekend with good reviews"*), validates the extracted search parameters through a two-layer validation pipeline, executes the relevant tools, and synthesizes a human-friendly markdown response — all with optional human-in-the-loop confirmation.

---

## Architecture / Data Flow

```
START
  │
  ▼
input ──► intent_parser ──► validator ──► tool_call ──► tool_executor
  │                            │              │               │
  │                            │              │               │
  └──► error_handler ◄─────────┘◄─────────────┘               │
       (if too many retries)                                   │
                                                               │
                                          ◄────────────────────┘
                                          │
                                          ▼
                                      response ──► human_review ──► persist ──► END
                                                      │
                                                      └──► END (if not approved)
```

> **Placeholder:** Insert architecture infographic / pipeline flowchart here.

The graph consists of 9 nodes with conditional routing and a maximum of 3 retries before the error handler is invoked. The `human_review_node` uses LangGraph's `interrupt()` to pause execution and ask for user confirmation before finalizing.

### Technologies

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| State Machine | LangGraph v1.1+ |
| LLM Framework | LangChain v1.2+ |
| LLM Provider | Groq (`llama-3.3-70b-versatile`) |
| MCP Protocol | Model Context Protocol via `mcp>=1.0.0` |
| Web UI | Gradio v4+ |
| Prompt Templating | Jinja2 |
| Validation | Pydantic v2 |
| Web Search | Tavily API |
| Terminal UI | Rich v13.7+ |
| Persistence | Postgres (optional) / In-memory |
| Retry Logic | Tenacity |

---

## Key Features

- **9-node LangGraph state machine** with conditional routing and retry logic
- **MCP integration** for real Airbnb data (falls back to realistic mock data if no MCP server is available)
- **Jinja2 dynamic prompts** — 4 separate `.j2` templates decoupled from Python code
- **Two-layer validation** — Pydantic structural validation + LLM semantic validation
- **Human-in-the-loop** via `interrupt()` — pauses before finalizing or booking
- **Postgres checkpointing** for persistent conversations across sessions (or in-memory for development)
- **Rich debug output** toggleable with `/debug on|off`
- **Slash commands** — `/help`, `/clear`, `/state`, `/history`, `/debug`, `/memory`, `/quit`
- **Gradio web UI** as an alternative to the terminal client
- **Retry logic** with exponential backoff via Tenacity on LLM calls
- **Error categorization** — date errors, location errors, and guest count errors each get specific friendly messages

### Available Tools

| Tool | Description |
|---|---|
| `airbnb_search` | Search Airbnb listings via MCP |
| `web_search` | General web search (travel guides, local info) |
| `get_weather` | Current weather + 3-day forecast |
| `format_results` | Sort/filter hotel listings |

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- A [Groq API key](https://console.groq.com/) (required)
- A [Tavily API key](https://tavily.com/) (recommended for web search)
- An [OpenWeatherMap API key](https://openweathermap.org/api) (optional, for weather)
- Node.js (optional, for the real Airbnb MCP server via npx)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/Hotel_search_with_AirbnbMCP.git
cd Hotel_search_with_AirbnbMCP

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
# Create a .env file in the project root with the following:
# At minimum, GROQ_API_KEY is required.
echo GROQ_API_KEY=gsk_your_key_here > .env
echo LLM_MODEL=llama-3.3-70b-versatile >> .env
echo LLM_TEMPERATURE=0.0 >> .env
echo CHECKPOINTER=memory >> .env
```

### Full `.env` Reference

```ini
GROQ_API_KEY=gsk_your_key_here
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.0
TAVILY_API_KEY=tvly_your_key_here
OPENWEATHER_API_KEY=your_key_here
MCP_SERVERS=airbnb:stdio://airbnb-mcp
AIRBNB_MCP_COMMAND=npx
AIRBNB_MCP_ARGS=-y,@airbnb_search/mcp-server-airbnb
POSTGRES_URL=postgresql://user:pass@localhost:5432/hotel_db
CHECKPOINTER=memory
DEBUG_MODE=true
LOG_LEVEL=INFO
```

---

## Usage

### Terminal Chatbot

```bash
# Default mode (debug ON, in-memory checkpointer)
python airbnb_mcp.py

# Clean output (no debug panels)
python airbnb_mcp.py --no-debug

# Force in-memory checkpointer (no Postgres needed)
python airbnb_mcp.py --memory
```

Once running, simply type your query in natural language:

```
You: Find a 2-bedroom apartment in Paris under $300 for next weekend
```

### Slash Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/clear` | Start a new conversation (new thread_id) |
| `/debug on/off` | Toggle Rich debug output |
| `/state` | Inspect current graph state |
| `/history` | Show full debug trace from last turn |
| `/memory` | Switch to in-memory checkpointer |
| `/quit` or `exit` | Exit the chatbot |

### Gradio Web UI

```bash
python gradio_app.py
```

Opens a web interface at `http://0.0.0.0:7860`.

### Example Session

```
╔══════════════════════════════════════════╗
║     Hotel Search AI — MCP + LangGraph    ║
║         Type /help for commands          ║
╚══════════════════════════════════════════╝

You: Find pet-friendly hotels in Barcelona with pool, check-in June 15, check-out June 18, budget €500

🤖 Intent parsed: location=Barcelona, check_in=2026-06-15, check_out=2026-06-18,
   max_price=500, currency=EUR, guests=2, pets_allowed=true

🔍 Searching Airbnb...
✅ Found 8 listings

📋 Top pick: Beachfront Apartment with Pool – €180/night – ★4.8 (120 reviews)
   → Walkable to Gothic Quarter, pet fee €50 total

Do you approve these results? (yes/no): yes
```

---

## Project Structure

```
Hotel_search_with_AirbnbMCP/
├── airbnb_mcp.py                 # CLI entry point
├── gradio_app.py                 # Web UI entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment configuration
├── scripts/
│   ├── state.py                  # Typed state definitions
│   ├── graph.py                  # LangGraph graph assembly & routing
│   ├── debug.py                  # Rich debug logger
│   ├── json_utils.py             # JSON extraction from LLM output
│   ├── nodes/                    # LangGraph node functions
│   │   ├── input_node.py
│   │   ├── intent_parser_node.py
│   │   ├── validator_node.py
│   │   ├── tool_call_node.py
│   │   ├── tool_executor_node.py
│   │   ├── response_node.py
│   │   ├── human_review_node.py
│   │   ├── error_handler_node.py
│   │   ├── persist_node.py
│   │   └── debug_node.py
│   ├── tools/                    # LangChain Tool definitions
│   │   ├── airbnb_tool.py
│   │   ├── web_search_tool.py
│   │   ├── weather_tool.py
│   │   └── format_results_tool.py
│   ├── prompts/                  # Jinja2 prompt templates
│   │   ├── prompt_builder.py
│   │   └── templates/
│   │       ├── system.j2
│   │       ├── intent_parser.j2
│   │       ├── validator.j2
│   │       └── response_formatter.j2
│   └── config/
│       ├── settings.py           # Pydantic settings
│       ├── mcp_loader.py         # MCP server config loader
│       └── mcp_config.json
└── .venv/                        # Virtual environment
```

---

## Future Enhancements

- [ ] Multi-city / itinerary planning across multiple searches
- [ ] Direct booking integration via Airbnb MCP (confirmed reservations)
- [ ] Price history and trend analysis for listings
- [ ] Docker Compose setup for one-command deployment (app + Postgres)
- [ ] Streaming LLM responses in the Gradio UI
- [ ] Support for additional LLM providers (OpenAI, Anthropic, local Ollama)
- [ ] Unit test suite with pytest
- [ ] CI/CD pipeline with GitHub Actions
- [ ] User authentication and multi-tenancy for hosted deployments
