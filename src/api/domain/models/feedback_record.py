from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class FeedbackRecord(BaseModel):
    id: str  # UUID
    user_id: str  # Partition key
    question_id: str
    rating: str  # "positive", "negative"
    flag_type: Optional[str] = None  # "incorrect_answer", "ambiguous", "too_easy", "too_hard", "off_topic"
    comment: Optional[str] = None  # Max 200 chars
    created_at: datetime

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError("Comment must be at most 200 characters")
        return v
