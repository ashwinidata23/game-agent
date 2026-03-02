# 🕹️ Agentic Game Builder

An agentic AI system that takes a natural-language game idea and generates a fully playable browser game (`index.html`, `style.css`, `game.js`) through a structured multi-phase pipeline.

---

## How to Run the Agent

### Prerequisites
- Docker installed
- An OpenAI API key

### Docker Build & Run

```bash
# 1. Clone the repository
git clone <repo-url>
cd game-agent

# 2. Build the Docker image
docker build -t game-agent .

# 3. Run interactively (recommended)
docker run -it \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/output:/app/output \
  game-agent

# 4. Or pass game idea directly as argument
docker run -it \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/output:/app/output \
  game-agent "make a space shooter where I dodge asteroids"
```

### After Running

Open `output/index.html` in your browser to play the generated game.

The agent also writes:
- `output/requirements.json` — resolved requirements from the clarification phase
- `output/plan.json` — the technical game plan from the planning phase
- `output/index.html`, `output/style.css`, `output/game.js` — the playable game

---

## Agent Architecture

The system is a **linear pipeline of specialized agents**, coordinated by a central Orchestrator. Each agent has a single responsibility, a dedicated system prompt, and communicates via typed Pydantic schemas — not raw text.

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                    Orchestrator                      │
│         (phase transitions + data routing)           │
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────┐
│ ClarifierAgent  │  Multi-turn Q&A loop. Dynamic stopping condition:
│                 │  rule check → LLM completeness score → hard cap at 6 questions.
│                 │  User can override anytime by saying "ready" / "go".
└────────┬────────┘
         │ RequirementsSchema (Pydantic)
         │ → written to output/requirements.json
         ▼
┌─────────────────┐
│  PlannerAgent   │  Reads structured requirements. Decides framework
│                 │  (Phaser vs Vanilla JS) via heuristic rules.
│                 │  Specifies all entities, systems, state machine.
└────────┬────────┘
         │ PlanSchema (Pydantic)
         │ → written to output/plan.json
         ▼
┌─────────────────┐
│   CoderAgent    │  Reads plan only (never raw chat). Generates all
│                 │  three files. Runs a single self-review pass to
│                 │  catch structural issues before writing.
└────────┬────────┘
         │ {index.html, style.css, game.js}
         ▼
┌─────────────────┐
│ OutputValidator │  3-layer structural validation (Python only, no LLM):
│                 │  Layer 1: file existence + size
│                 │  Layer 2: syntax markers (DOCTYPE, script tags, etc)
│                 │  Layer 3: coherence (framework used, states referenced)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FileWriter    │  Writes all files to /app/output (Docker volume)
└─────────────────┘
```

### Key Design Decisions

**Orchestrator as sole coordinator**: No agent imports another agent directly. All routing goes through `orchestrator.py`. This makes the control flow explicit and testable.

**Typed JSON contracts**: Data between phases flows as Pydantic models (`RequirementsSchema`, `PlanSchema`), not raw strings or dicts. If the LLM returns malformed JSON, Pydantic catches it cleanly.

**Prompt restructuring**: The ClarifierAgent converts the vague conversation into a structured `RequirementsSchema` before passing to the Planner. The Planner receives clean structured data, not chat history. The Coder receives a full plan, not requirements. Each stage gets the right level of abstraction.

**Procedural assets only**: All game visuals are drawn with Canvas 2D API or Phaser Graphics — no external images, no CDN sprites, no placeholders. Games run fully offline (except Phaser itself, which is loaded from CDN only when chosen).

**Framework decision is explicit**: The Planner writes `framework_reason` to `plan.json`, so the evaluator can see exactly why Phaser or Vanilla JS was chosen for a given game.

---

## Trade-offs Made

| Decision | Trade-off |
|---|---|
| Linear pipeline (no retry loop) | Simpler, more predictable — but if code generation fails, there's no automatic recovery. A retry loop was considered but rejected because LLM self-validation in a Docker environment without a browser has poor reliability. |
| Single self-review pass in CoderAgent | Catches structural issues without risking infinite loops or compounding hallucinations from multiple passes. Deep semantic validation would require a real execution environment. |
| Procedural canvas assets only | Games look like geometric prototypes, not polished games. The trade-off is zero external dependencies and guaranteed offline playability. |
| Phaser loaded from CDN when chosen | Requires internet access for Phaser games. Trade-off accepted because bundling Phaser (~1MB) in the Docker image adds complexity without much benefit for an evaluation context. |
| Python structural validation (no headless browser) | Can't catch runtime JavaScript errors. Only structural/coherence checks. The alternative — running Puppeteer or Playwright in Docker — adds significant build complexity. |

---

## Improvements With More Time

1. **Headless browser validation** — Run generated `index.html` in Playwright inside Docker, capture console errors, detect if the game loop actually starts. This is the single biggest improvement for reliability.

2. **Retry loop with error feedback** — If validation fails, pass the specific errors back to CoderAgent as a follow-up message for targeted fixes, rather than full regeneration.

3. **Streaming output** — Stream game.js generation to terminal so the user sees progress during what can be a 30-60 second generation step.

4. **Game preview server** — Spin up a simple Python HTTP server inside Docker and print a `localhost:8080` URL so the user can play immediately without finding the output file.

5. **Multi-level support** — Currently generates single-level games. Planner could design level progression and CoderAgent could implement level transitions.

6. **Asset generation** — Integrate an image generation API to produce actual sprites instead of geometric shapes, embedded as base64 in game.js.

7. **Conversation memory across sessions** — Save clarification conversations so returning users don't need to re-describe their game.

---

## Project Structure

```
game-agent/
├── Dockerfile
├── README.md
├── requirements.txt
├── main.py                      # Entry point
│
├── agent/
│   ├── orchestrator.py          # Phase transitions, data routing
│   ├── clarifier.py             # ClarifierAgent + system prompts
│   ├── planner.py               # PlannerAgent + system prompts
│   └── coder.py                 # CoderAgent + system prompts + self-review
│
├── schemas/
│   ├── requirements_schema.py   # Pydantic model: Clarifier → Planner contract
│   └── plan_schema.py           # Pydantic model: Planner → Coder contract
│
├── validators/
│   └── output_validator.py      # 3-layer structural validation
│
├── utils/
│   ├── llm_client.py            # OpenAI wrapper (single place for all API calls)
│   └── file_writer.py           # Writes output files + JSON artifacts
│
└── output/                      # Generated game files land here (Docker volume)
    ├── requirements.json
    ├── plan.json
    ├── index.html
    ├── style.css
    └── game.js
```









"speed/difficulty preference should be captured during clarification and flow through the plan into generated code."

"CoderAgent prompt was strengthened with universal game-engine rules covering tick-based speed control, collision detection patterns, and input buffering — applicable to all game genres rather than game-specific instructions."

"prompt was iteratively strengthened based on observed failure patterns across multiple game types."

"The system is architected to support different models per phase — gpt-4o-mini for clarification/planning, gpt-4o for code generation. This would reduce cost by ~75% per run. For this submission both phases use gpt-4o to prioritize reliability, since a bad plan silently corrupts all downstream output. The model split is a one-line config change when cost optimization becomes the priority."

"for tic tac toe games : Good learning for the clarifier — it should ask "single player vs computer or 2 players?" for turn-based games. Add this note mentally for the README.