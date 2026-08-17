from pydantic import BaseModel
from datetime import datetime


class AnswerRecord(BaseModel):
    id: str  # UUID
    user_id: str  # Partition key
    question_id: str
    selected_answer: int  # 0-3
    is_correct: bool
    context: str  # "training" or "simulation"
    session_id: str
    answered_at: datetime
