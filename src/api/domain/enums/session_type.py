from enum import Enum


class SessionType(Enum):
    """Types of user study sessions."""

    TRAINING = "training"
    SIMULATION = "simulation"
    FREE_QA = "free_qa"
