from pydantic import BaseModel, Field
from typing import Optional


class EntitySpec(BaseModel):
    name: str
    description: str = Field(
        ...,
        description="Visual appearance (shape, color, size) and behavior in plain English",
    )


class PlanSchema(BaseModel):
    model_config = {"extra": "ignore"}  # ignore unexpected fields from LLM
    """
    Structured output of the PlannerAgent.
    This is the complete technical game plan. CoderAgent reads ONLY this — never raw chat.
    Saved to output/plan.json so it's visible to evaluators.
    """

    title: str
    framework: str = Field(..., description="'vanilla' or 'phaser'")
    framework_reason: str = Field(
        ..., description="One sentence explaining why this framework was chosen"
    )
    canvas_width: int = Field(default=800)
    canvas_height: int = Field(default=480)

    file_structure: dict[str, str] = Field(
        ...,
        description="Description of each file's role e.g. {'index.html': 'canvas container, loads game.js'}",
    )

    game_loop: str = Field(
        ...,
        description="How the game loop works e.g. 'requestAnimationFrame at 60fps' or 'Phaser Scene update()'",
    )

    state_machine: list[str] = Field(
        ...,
        description="Ordered list of game states e.g. ['menu', 'playing', 'gameOver', 'win']",
    )

    systems: list[str] = Field(
        ...,
        description="Core systems to implement e.g. ['input', 'physics', 'collision', 'score', 'render']",
    )

    entities: list[EntitySpec] = Field(
        ..., description="Full spec for each entity — what it looks like and how it behaves"
    )

    controls: dict[str, str] = Field(
        ..., description="Mapping of key to action, carried forward from requirements"
    )

    win_condition: str
    lose_condition: str

    asset_strategy: str = Field(
        default="procedural canvas shapes, no external files",
        description="How assets are handled — always procedural for this agent",
    )

    phaser_version: Optional[str] = Field(
        default="3.60.0",
        description="Phaser CDN version to use. Only relevant if framework is 'phaser'",
    )

    implementation_notes: Optional[str] = Field(
        default=None,
        description="Any special implementation guidance for the CoderAgent",
    )