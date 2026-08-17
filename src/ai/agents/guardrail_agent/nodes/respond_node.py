"""Response node for the Guardrail Agent.

Determines the output based on the safety classification:
- If unsafe: returns the static FALLBACK_RESPONSE.
- If safe: passes through the original user input unchanged.
"""

from src.ai.agents.guardrail_agent.state import FALLBACK_RESPONSE, GuardrailState


async def respond_node(state: GuardrailState) -> dict:
    """Produce the final output based on safety classification.

    If is_safe is False: sets output_message to FALLBACK_RESPONSE.
    If is_safe is True: sets output_message to None (pass-through signal).
    """
    if state["is_safe"]:
        return {"output_message": None}
    else:
        return {"output_message": FALLBACK_RESPONSE}
