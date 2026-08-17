"""State definition for the Guardrail Agent."""

from typing import Optional, TypedDict

FALLBACK_RESPONSE = (
    "I can only help with Azure certification questions. "
    "Please ask a relevant question."
)


class GuardrailState(TypedDict):
    """Typed state for the Guardrail Agent graph.

    Attributes:
        user_message: Raw user input (no user IDs or session metadata).
        is_safe: LLM classification result — True if input is safe.
        block_reason: Category of blocked content, if any.
            One of: "prompt_injection", "manipulation", "off_topic_harmful", or None.
        output_message: Either None (pass-through) or FALLBACK_RESPONSE when blocked.
    """

    user_message: str
    is_safe: bool
    block_reason: Optional[str]
    output_message: Optional[str]
