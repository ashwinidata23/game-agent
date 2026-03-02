from pydantic import BaseModel, Field
from typing import Optional


class RequirementsSchema(BaseModel):
    model_config = {"extra": "ignore"}  # ignore unexpected fields from LLM
    """
    Structured output of the ClarifierAgent.
    This is the resolved, unambiguous game requirements object.
    Passed directly to PlannerAgent — Planner never sees raw chat history.
    """

    title: str = Field(..., description="Short name for the game")
    genre: str = Field(
        ...,
        description="Game genre e.g. platformer, shooter, puzzle, arcade, snake, pong",
    )
    objective: str = Field(
        ..., description="Clear one-sentence description of what the player must do"
    )
    controls: dict[str, str] = Field(
        ...,
        description="Mapping of key/input to action e.g. {'ArrowLeft': 'move left', 'Space': 'jump'}",
    )
    entities: list[str] = Field(
        ...,
        description="List of game entities e.g. ['player', 'enemy', 'coin', 'platform']",
    )
    levels: int = Field(default=1, description="Number of levels. Default 1.")
    win_condition: str = Field(
        ..., description="Condition that causes the player to win"
    )
    lose_condition: str = Field(
        ..., description="Condition that causes the player to lose"
    )
    complexity: str = Field(
        ...,
        description="One of: simple | medium | complex. Drives framework selection downstream.",
    )
    extra_notes: Optional[str] = Field(
        default=None,
        description="Any additional notes or preferences from the user not captured above",
    )