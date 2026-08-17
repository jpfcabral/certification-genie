from pydantic import BaseModel, field_validator
from datetime import datetime


class Question(BaseModel):
    id: str  # UUID
    certification: str  # e.g., "AI-103"
    domain: str  # e.g., "Generative AI and Agents"
    text: str  # Question body
    options: list[str]  # Exactly 4 options
    correct_answer_index: int  # 0-3
    short_explanation: str  # Max 200 chars
    detailed_explanation: str  # Full explanation
    created_at: datetime
    quality_score: float = 1.0  # Aggregated feedback score
    is_active: bool = True  # Deactivated if quality too low
    generated_by: str = "seed"  # "seed" or "generator_agent"

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str]) -> list[str]:
        if len(v) != 4:
            raise ValueError("Question must have exactly 4 options")
        return v

    @field_validator("correct_answer_index")
    @classmethod
    def validate_answer_index(cls, v: int) -> int:
        if v < 0 or v > 3:
            raise ValueError("Correct answer index must be between 0 and 3")
        return v

    @field_validator("short_explanation")
    @classmethod
    def validate_short_explanation(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("Short explanation must be at most 200 characters")
        return v
