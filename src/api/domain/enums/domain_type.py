from enum import Enum


class DomainType(Enum):
    """AI-103 exam domains with their weight percentages.

    Weights represent the proportion of questions from each domain
    in the certification exam and are used for simulation distribution.
    """

    GENERATIVE_AI_AND_AGENTS = "Generative AI and Agents"
    COMPUTER_VISION = "Computer Vision"
    TEXT_ANALYSIS = "Text Analysis"
    INFORMATION_EXTRACTION = "Information Extraction"
    PLAN_AND_MANAGE = "Plan and Manage"

    @property
    def weight(self) -> float:
        """Return the exam weight percentage for this domain."""
        return _DOMAIN_WEIGHTS[self]


_DOMAIN_WEIGHTS: dict["DomainType", float] = {
    DomainType.GENERATIVE_AI_AND_AGENTS: 0.35,
    DomainType.COMPUTER_VISION: 0.15,
    DomainType.TEXT_ANALYSIS: 0.20,
    DomainType.INFORMATION_EXTRACTION: 0.15,
    DomainType.PLAN_AND_MANAGE: 0.15,
}


def get_domain_weights() -> dict["DomainType", float]:
    """Return a copy of domain weights mapping."""
    return dict(_DOMAIN_WEIGHTS)
