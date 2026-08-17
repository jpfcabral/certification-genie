# 🧞‍♂️ Certification Genie

**Your AI-powered study partner for Azure cloud certifications.**

Certification Genie is a Telegram bot that helps you prepare for the Microsoft AI-103 (Azure AI Apps and Agents Developer Associate) exam through interactive quizzes, exam simulations, and free-form Q&A grounded in official Azure documentation.

Stop passively reading docs. Start actively testing your knowledge with instant feedback, detailed explanations, and AI-generated questions that adapt to your weak areas.

---

## What it does

**📚 Training Mode** — Answer questions one at a time with immediate feedback. Got it wrong? Get a short explanation right away, or ask "why" for a deep-dive with documentation references.

**📝 Exam Simulation** — Take a timed mock exam with 20 questions distributed across all AI-103 domains (weighted like the real exam). No peeking at answers until the end.

**💬 Free Q&A** — Ask anything about Azure AI Services. The bot searches official documentation via RAG and gives you grounded answers with source citations.

**🃏 Flashcards & Study Aids** — Quick concept cards, domain breakdowns with your performance stats, and weak-area identification to focus your study time.

**🤖 AI-Generated Questions** — When you exhaust the question bank, new certification-level questions are generated on the fly. They're validated, checked for duplicates, and improved over time based on user feedback.

---

## How it works

The bot is built around **5 specialized AI agents**, each handling a specific responsibility:

| Agent | Role |
|-------|------|
| **Guardrail** | Screens every input for prompt injection and off-topic content before any other agent sees it |
| **Orchestrator** | Manages session flow and decides which question to serve next |
| **Generator** | Creates new exam-quality questions using LLM with domain context and feedback |
| **QA** | Answers free-form questions using RAG over Azure documentation |
| **Explainer** | Provides detailed explanations with documentation references when you answer incorrectly |

All agents follow a **privacy-by-design** principle: user identifiers never reach the LLM. Agents operate only on content data.

---

## Key features

- Multi-mode study: training, simulation, free Q&A
- AI-103 domain-weighted question distribution (Generative AI 35%, Text Analysis 20%, Computer Vision 15%, Information Extraction 15%, Plan and Manage 15%)
- Question quality feedback loop (thumbs up/down, flagging) with automatic deactivation of low-quality questions
- Progress tracking with per-domain breakdown and weak-area analysis
- Input guardrails with fail-closed security (LLM failure = block)
- Serverless infrastructure: scales to zero, pay only for what you use
- Extensible to other certifications (AZ-900, DP-100, etc.)

---

## Quick Start

```bash
# Clone and set up environment
git clone <repo-url>
cd certification-genie
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Run
docker compose up --build -d

# Open
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

---

## Technical Details

### Architecture

```
┌───────────────┐     ┌───────────┐     ┌────────────────────────┐
│   Telegram    │────▶│  FastAPI   │────▶│  LangGraph AI Agents   │
│   (or local   │     │  Webhook   │     │  (Guardrail, QA, Gen)  │
│    frontend)  │     │  + Auth    │     └───────────┬────────────┘
└───────────────┘     └───────────┘                  │
                                         ┌───────────▼────────────┐
                                         │   Azure CosmosDB       │
                                         │   (Serverless)         │
                                         └────────────────────────┘
```

### Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| AI Agents | LangGraph + LangChain + OpenAI |
| Database | Azure CosmosDB (serverless) |
| Bot Interface | python-telegram-bot |
| Infrastructure | Azure Container Apps (consumption) + Terraform |
| Testing | pytest + hypothesis (property-based testing) |

### Project Structure

```
src/
├── api/              # FastAPI app, services, repositories, domain models
├── ai/agents/        # LangGraph agents (guardrail, orchestrator, generator, qa, explainer)
├── bot/              # Telegram handlers, keyboards, formatters
├── frontend/         # Local test UI (Telegram simulator)
├── seed/             # Initial question bank (12 questions across 5 domains)
└── main.py           # Application entrypoint

infra/                # Terraform modules (CosmosDB, Container Apps, ACR, VNet)
tests/                # 280+ tests (unit, property-based, integration, e2e)
```

### Running Tests

```bash
pip install -e ".[dev]"

# All tests (unit + property + integration)
pytest tests/

# End-to-end only (includes live LLM calls if OPENAI_API_KEY is set)
pytest tests/e2e/ -v
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for all agents |
| `TELEGRAM_BOT_TOKEN` | For production | Telegram bot token |
| `TELEGRAM_WEBHOOK_SECRET` | For production | Webhook signature secret |
| `COSMOS_CONNECTION_STRING` | For production | Azure CosmosDB connection |
| `AZURE_SEARCH_ENDPOINT` | For RAG | Azure AI Search endpoint |
| `AZURE_SEARCH_KEY` | For RAG | Azure AI Search API key |

### Infrastructure (Terraform)

All resources are serverless/pay-per-use with no fixed monthly costs:

```bash
cd infra
terraform init
terraform plan -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
```

---

## License

This project is licensed under a **Non-Commercial MIT License**. You may use, copy, and modify it freely for personal and educational purposes. Commercial use is prohibited without explicit permission. See [LICENSE](LICENSE) for details.
