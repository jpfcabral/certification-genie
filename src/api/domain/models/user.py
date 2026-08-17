from pydantic import BaseModel
from datetime import datetime


class User(BaseModel):
    id: str  # Internal UUID
    telegram_id: int  # Numeric Telegram identifier
    registered_at: datetime
    reminders_enabled: bool = True
    last_interaction_at: datetime | None = None
