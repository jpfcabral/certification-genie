"""Generate node — uses LLM to produce a new certification question.

This node takes the domain context, example questions, and optional feedback,
builds a prompt, and invokes the LLM to generate a new question. The output
is parsed from JSON and placed into the state as `generated_question`.
"""

import json
import logging

from langchain_openai import ChatOpenAI

from src.ai.agents.generator_agent.prompts.generator_prompt import (
    build_generator_prompt,
)
from src.ai.agents.generator_agent.state import GeneratorState

logger = logging.getLogger(__name__)


async def generate_node(state: GeneratorState) -> dict:
    """Generate a new certification question using the LLM.

    Builds a prompt from the state context (certification, domain, examples,
    feedback) and invokes the LLM. Parses the JSON response into a question
    dict.

    Args:
        state: Current generator state with domain context and examples.

    Returns:
        Partial state update with generated_question set (or None on failure).
    """
    prompt = build_generator_prompt(
        certification=state["certification"],
        target_domain=state["target_domain"],
        example_questions=state["example_questions"],
        feedback_context=state.get("feedback_context"),
    )

    from src.api.infrastructure.config import get_settings
    llm = ChatOpenAI(
        model=get_settings().OPENAI_MODEL,
        temperature=0.8,
    )

    try:
        response = await llm.ainvoke(
            [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        f"Generate a new {state['certification']} question "
                        f"for the domain: {state['target_domain']}"
                    ),
                },
            ]
        )

        content = response.content
        # Strip markdown fences if present
        if isinstance(content, str):
            content = content.strip()
            if content.startswith("```"):
                # Remove opening fence (with optional language tag)
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        question_data = json.loads(content)

        # Attach metadata
        question_data["domain"] = state["target_domain"]
        question_data["certification"] = state["certification"]

        logger.info(
            "Generated question for domain=%s, certification=%s",
            state["target_domain"],
            state["certification"],
        )

        return {"generated_question": question_data}

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse LLM response: %s", e)
        return {
            "generated_question": None,
            "is_valid": False,
            "validation_errors": [f"LLM response parsing failed: {e}"],
        }
    except Exception as e:
        logger.error("LLM invocation failed: %s", e)
        return {
            "generated_question": None,
            "is_valid": False,
            "validation_errors": [f"LLM invocation error: {e}"],
        }
