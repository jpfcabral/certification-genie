"""Classification node for the Guardrail Agent.

Uses an LLM to classify user input as safe or unsafe. Implements
fail-closed behavior: if the LLM call fails for any reason, the
input is treated as unsafe and blocked.
"""

import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.ai.agents.guardrail_agent.prompts.guardrail_prompt import (
    GUARDRAIL_SYSTEM_PROMPT,
)
from src.ai.agents.guardrail_agent.state import GuardrailState

logger = logging.getLogger(__name__)

# Threat categories that map to unsafe classification
_UNSAFE_CATEGORIES = {"prompt_injection", "manipulation", "off_topic_harmful"}


async def classify_node(state: GuardrailState) -> dict:
    """Classify user input for safety using an LLM.

    Detects:
    - Prompt injection attempts
    - Manipulation attempts (extracting system info, social engineering)
    - Off-topic harmful content

    Sets is_safe=True if none detected, is_safe=False otherwise.
    Fail-closed: any error during classification results in is_safe=False.
    """
    user_message = state["user_message"]

    try:
        from src.api.infrastructure.config import get_settings
        llm = ChatOpenAI(model=get_settings().OPENAI_MODEL, temperature=0)

        messages = [
            SystemMessage(content=GUARDRAIL_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]

        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse the JSON response from the LLM
        result = json.loads(content)
        category = result.get("category", "").lower().strip()

        if category == "safe":
            return {"is_safe": True, "block_reason": None}
        elif category in _UNSAFE_CATEGORIES:
            logger.warning(
                "Guardrail blocked input — category: %s", category
            )
            return {"is_safe": False, "block_reason": category}
        else:
            # Unexpected category — fail closed
            logger.warning(
                "Guardrail received unexpected category '%s' — blocking",
                category,
            )
            return {"is_safe": False, "block_reason": "unknown"}

    except Exception:
        # Fail-closed: if LLM call fails, treat as unsafe
        logger.exception("Guardrail LLM call failed — blocking request")
        return {"is_safe": False, "block_reason": "classification_error"}
