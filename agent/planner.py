import json
from utils.llm_client import LLMClient
from schemas.requirements_schema import RequirementsSchema
from schemas.plan_schema import PlanSchema

SYSTEM_PROMPT = """You are a game architect for an AI game-building agent.

You receive a structured game requirements object and must produce a complete technical game plan.

FRAMEWORK DECISION RULES (apply in order):
1. Use "phaser" if: genre is platformer, top-down, or RPG, OR complexity is "complex", OR entities require physics (gravity, bounce, velocity)
2. Use "vanilla" if: genre is snake, pong, puzzle, memory, runner, or arcade, OR complexity is "simple"
3. Default to "vanilla" when uncertain

ASSET RULE: ALL assets must be procedural canvas shapes. No external images. No placeholders.
- Players: colored rectangles or circles
- Enemies: different colored shapes
- Collectibles: small circles or stars drawn with canvas
- Platforms: rectangles

ENTITY SPEC RULE: For each entity, describe EXACTLY:
- Shape (rect, circle)
- Size in pixels
- Color (hex or named)
- Behavior in one sentence

You must return a valid JSON object matching this schema exactly:
{
  "title": "<game title>",
  "framework": "vanilla" or "phaser",
  "framework_reason": "<one sentence>",
  "canvas_width": 800,
  "canvas_height": 480,
  "file_structure": {
    "index.html": "<description>",
    "style.css": "<description>",
    "game.js": "<description>"
  },
  "game_loop": "<description of game loop>",
  "state_machine": ["<state1>", "<state2>", ...],
  "systems": ["<system1>", ...],
  "entities": [
    {"name": "<name>", "description": "<shape, size, color, behavior>"},
    ...
  ],
  "controls": {"<key>": "<action>", ...},
  "win_condition": "<win condition>",
  "lose_condition": "<lose condition>",
  "asset_strategy": "procedural canvas shapes, no external files",
  "phaser_version": "3.60.0",
  "implementation_notes": "<any special guidance for the coder, or null>"
}

Return ONLY the JSON. No markdown, no explanation."""


class PlannerAgent:
    """
    Reads RequirementsSchema → produces PlanSchema (saved as plan.json).
    Makes the framework decision and specifies all entity visuals.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, reqs: RequirementsSchema) -> PlanSchema:
        print("🗺️  Planning Phase")
        print("=" * 50)
        print(f"   Genre: {reqs.genre} | Complexity: {reqs.complexity}")

        requirements_json = reqs.model_dump_json(indent=2)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Create a complete game plan for these requirements:\n\n{requirements_json}",
            },
        ]

        raw = self.llm.chat_json(messages, temperature=0.3, call_name="planner")

        try:
            plan = PlanSchema(**raw)
            print(f"   Framework chosen: {plan.framework} — {plan.framework_reason}")
            print(f"   States: {' → '.join(plan.state_machine)}")
            print(f"   Entities: {[e.name for e in plan.entities]}")
            print("   ✅ Plan complete\n")
            return plan
        except Exception as e:
            raise ValueError(f"Failed to parse plan into schema: {e}\nRaw: {raw}")