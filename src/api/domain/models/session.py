from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class Session(BaseModel):
    id: str
    user_id: str
    session_type: str  # "training", "simulation", "free_qa"
    started_at: datetime
    ended_at: Optional[datetime] = None
    questions_served: list[str] = []  # Question IDs
    current_question_index: int = 0
    total_questions: int | None = None  # For simulation mode
    is_active: bool = True
