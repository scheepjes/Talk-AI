# Talk AI

Two LLMs conversing with each other. Choose a topic, select a depth level, and watch two llama.cpp-powered servers debate.

## Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   talk.py   │    │     app.py       │    │  llama.cpp       │
│  (CLI mode) │    │   (Flask web UI) │    │  Server A:       │
└─────────────┘    └──────────────────┘    │  10.0.0.10:9001  │
      │                      │              └──────────────────┘
      ▼                      │                      ▲
┌──────────────────────────────────────┐             │
│           logic.py                   │◄────────────┘
│  • send_message()                    │
│  • run_single_turn()                 │
│  • run_user_question()               │
│  • truncate_history()                │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│          database.py                 │
│  • SQLite persistence                │
│  • conversations.db                  │
└──────────────────────────────────────┘
```

**How it works:**
1. You provide a topic and depth level
2. Server A generates a response on the topic
3. Server B reacts to Server A's response
4. The turn repeats — both servers build on the growing conversation history
5. History is truncated at 30 messages to stay within context limits

## LLM Servers

This project uses two independent llama.cpp servers with OpenAI-compatible chat/completions API.

### Server Configuration

| Server | URL | Purpose |
|--------|-----|---------|
| Server A | `http://10.0.0.10:9001/v1/chat/completions` | Primary debater — responds to topics and questions |
| Server B | `http://10.0.0.10:9002/v1/chat/completions` | Reactor — responds to Server A's output |

Both servers are configured in `logic.py` and `talk.py`:

```python
SERVER_A_URL = "http://10.0.0.10:9001/v1/chat/completions"
SERVER_B_URL = "http://10.0.0.10:9002/v1/chat/completions"
```

### Running Your Own Servers

Start two llama.cpp servers with different ports, ensuring `--chat-template` is set:

```bash
# Server A
llama-server -m model_a.gguf -p 9001 --host 10.0.0.10 --port 9001 --chat-template <template>

# Server B
llama-server -m model_b.gguf -p 9002 --host 10.0.0.10 --port 9002 --chat-template <template>
```

Replace `model_a.gguf`, `model_b.gguf`, and `<template>` with your model paths and chat template (e.g., `chatml`, `llama3`, `mistral`).

## Prerequisites

- Python 3.8+
- Two llama.cpp servers with chat/completions API enabled
- (Optional) A web browser for the Flask UI

## Installation

```bash
# Install dependencies
pip install requests colorama flask

# Configure server URLs in logic.py (or talk.py)
SERVER_A_URL = "http://10.0.0.10:9001/v1/chat/completions"
SERVER_B_URL = "http://10.0.0.10:9002/v1/chat/completions"
```

**Configuration files:**
- `talk.py` — CLI entry point, also has `DEPTH_TEMPLATES` and server URLs
- `logic.py` — shared logic, also has `DEPTH_TEMPLATES` and server URLs (preferred for web mode)

## Usage

### CLI Mode

```bash
python talk.py
```

1. Enter a topic
2. Choose depth level (1–4)
3. Set max turns (default 50)
4. Watch the conversation
5. Press `Ctrl+C` to stop and start a new conversation

### Web Mode

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

1. Enter a topic and choose depth
2. Click **Start Conversation** — first turn auto-starts
3. Click **Next Round** for continuous auto-debate
4. Use **Ask Question** to inject your own questions
5. Click **History** to view past conversations

## Depth Levels

| Level | Description |
|-------|-------------|
| 1 | **Brief & Concise** — Factual answers without elaboration |
| 2 | **Normal** — Regular conversation, lively and polite |
| 3 | **Deep & Philosophical** — Thorough analysis with attention to nuances |
| 4 | **Expert Level** — Specialist treatment with deep logical reasoning |

## Conversation Flow

### Auto-Debate (Next Round)

```
Turn N:
  User prompt → Server A response → Server B reacts to A
  [history updated with both responses]

Turn N+1:
  User prompt → Server A response → Server B reacts to A
  ...
```

### User Question

You can interrupt the conversation at any time:

```
User question → Server A response → Server B reacts to both question and A
```

### History Truncation

When conversation exceeds 30 messages, the oldest non-system messages are removed to stay within context limits. The system prompt is always preserved.

## Database

Conversations are persisted in **`conversations.db`** (SQLite, located in the project root directory).

**Tables:**
- `conversations` — id, topic, depth_level, created_at
- `messages` — conversation_id, role, content, sender, display, created_at

**Key behaviors:**
- Every new conversation creates a row in `conversations`
- Each message from both servers is saved in `messages`
- `display` flag controls whether a message appears in the UI (user prompts are hidden from display)
- Conversations can be loaded back into the session from the history browser
- Individual or bulk deletion is supported

## API Reference

### Flask Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Render main page |
| POST | `/start` | Start a new conversation |
| POST | `/next_turn` | Execute one auto-debate round |
| POST | `/ask_question` | User injects a question |
| GET | `/api/conversations` | List all saved conversations |
| GET | `/api/conversations/<id>/messages` | Get messages for one conversation |
| POST | `/api/conversations/<id>/load` | Load a saved conversation into session |
| DELETE | `/api/conversations/<id>` | Delete one conversation |
| DELETE | `/api/conversations` | Delete all conversations |

### Core Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `send_message(url, messages, max_tokens, context_length)` | `logic.py:16` | Sends chat request to llama.cpp server |
| `run_single_turn(topic, depth_level, history)` | `logic.py:60` | Executes one debate round |
| `run_user_question(question, depth_level, history)` | `logic.py:104` | Handles user-injected question |
| `truncate_history(history, max_messages)` | `logic.py:47` | Limits history to max_messages |

## Testing

```bash
python test_history.py
```

Tests basic and multi-conversation database operations.

## Troubleshooting

**Server not reachable** — Verify llama.cpp servers are running and URLs in `logic.py` are correct.

**Server timeout** — Large contexts or slow models may exceed the 120s request timeout.

**Same URL for both servers** — `SERVER_A_URL` and `SERVER_B_URL` currently point to the same server. Edit them to use different servers or ports for distinct AI agents.

**Web UI blank** — Ensure Flask is running (`python app.py`) and check `http://localhost:5000`.

**History not loading** — The session stores conversation history in memory. If you close the browser, load from the database using the History browser.
