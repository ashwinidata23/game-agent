# 🎮 Agentic Game Builder (Dockerized AI System)

An agentic AI system that takes a natural-language game idea and generates a **fully playable browser game** (`index.html`, `style.css`, `game.js`) through a structured multi-phase pipeline.

The project is fully containerized using Docker and can be executed with a single command.

---

## 🚀 Overview

This system implements a multi-agent architecture where specialized AI agents collaborate to transform a vague user idea into executable game code.

Instead of using a single large prompt, reasoning is divided into structured phases:

1. Clarification
2. Planning
3. Code Generation
4. Validation
5. File Output

This makes the workflow transparent, deterministic, and easy to evaluate.

---

## ▶️ How to Run the Agent

### Prerequisites

* Docker installed
* OpenAI API Key

---

### 1. Clone the Repository

```bash
git clone <repo-url>
cd game-agent
```

---

### 2. Build Docker Image

```bash
docker build -t game-agent .
```

---

### 3. Run Interactively (Recommended)

```bash
docker run -it \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/output:/app/output \
  game-agent
```

The agent will ask clarification questions before generating the game.

---

### 4. Run With Direct Game Idea

```bash
docker run -it \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/output:/app/output \
  game-agent "make a space shooter where I dodge asteroids"
```

---

### 🎮 After Running

Open the generated file:

```
output/index.html
```

in your browser to play the game.

Generated artifacts:

* `output/requirements.json` — structured requirements from clarification
* `output/plan.json` — technical game plan
* `output/index.html` — playable game
* `output/style.css`
* `output/game.js`

---

## 🧠 Agent Architecture

The system follows a linear pipeline coordinated by a central **Orchestrator**.

```
User Input
    │
    ▼
Orchestrator
    │
    ├── ClarifierAgent
    ├── PlannerAgent
    ├── CoderAgent
    ├── OutputValidator
    └── FileWriter
```

### Orchestrator

Controls phase transitions and routes structured data between agents.
Agents never communicate directly, keeping the system modular and testable.

---

### ClarifierAgent

* Multi-turn Q&A loop
* Dynamic stopping condition:

  * rule checks
  * LLM completeness scoring
  * hard cap at 6 questions
* User override supported via keywords like **"ready"** or **"go"**

Outputs a typed `RequirementsSchema`.

---

### PlannerAgent

* Consumes structured requirements
* Chooses framework (Phaser vs Vanilla JS) using heuristics
* Defines entities, systems, and state machine
* Writes reasoning into `framework_reason` for transparency

Outputs `PlanSchema`.

---

### CoderAgent

* Reads only the technical plan (never chat history)
* Generates all game files
* Runs a single self-review pass to catch structural issues

---

### OutputValidator

Python-based validation (no LLM):

1. File existence and size checks
2. Syntax markers (DOCTYPE, script tags, etc.)
3. Cross-file coherence validation

---

### FileWriter

Writes all outputs into `/app/output` using Docker volume mounting.

---

## 🏗 Key Design Decisions

**Orchestrator as sole coordinator**
All routing passes through the orchestrator for explicit control flow.

**Typed JSON contracts**
Agents communicate using Pydantic schemas instead of raw text, ensuring reliable structured outputs.

**Abstraction separation**

* Clarifier → structured requirements
* Planner → technical architecture
* Coder → implementation only

Each stage receives only the information it needs.

**Procedural assets only**
Games use Canvas 2D or Phaser Graphics — no external sprites — ensuring offline playability.

**Explicit framework decision**
Planner records why Phaser or Vanilla JS was selected.

---

## ⚖️ Trade-offs Made

| Decision                | Trade-off                                              |
| ----------------------- | ------------------------------------------------------ |
| Linear pipeline         | Predictable execution but no automatic recovery loop   |
| Single self-review pass | Prevents infinite loops but limits deep semantic fixes |
| Procedural graphics     | Reliable offline execution but less visual polish      |
| Phaser via CDN          | Requires internet when Phaser is selected              |
| Python validation only  | Cannot detect runtime JS errors                        |

---

## 🔧 Improvements With More Time

* Headless browser validation using Playwright
* Automatic retry loop with targeted error feedback
* Streaming generation output
* Built-in preview web server
* Multi-level game support
* AI-generated sprite assets
* Persistent conversation memory across sessions

---

## 📁 Project Structure

```
game-agent/
├── Dockerfile
├── README.md
├── requirements.txt
├── main.py
│
├── agent/
│   ├── orchestrator.py
│   ├── clarifier.py
│   ├── planner.py
│   └── coder.py
│
├── schemas/
│   ├── requirements_schema.py
│   └── plan_schema.py
│
├── validators/
│   └── output_validator.py
│
├── utils/
│   ├── llm_client.py
│   └── file_writer.py
│
└── output/
```

---

## 🧩 Additional Design Notes

* Speed and difficulty preferences are captured during clarification and propagated through planning into generated gameplay logic.
* CoderAgent uses generalized game-engine rules (tick-based motion, collision detection, input buffering).
* Prompts were iteratively refined based on observed failure patterns across multiple game genres.
* Architecture supports different models per phase (e.g., lightweight models for planning and stronger models for coding). For this submission, a single model prioritizes reliability.
* Clarification logic evolved to better handle turn-based games (e.g., asking single-player vs two-player for Tic-Tac-Toe).

---

## ✅ Submission

Repository contains:

* Fully Dockerized agent
* Reproducible execution
* Structured multi-agent architecture
* Generated playable output

Run with one command and generate a game from natural language.
