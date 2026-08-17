"""
E2E test for question generation with REAL LLM call.

Requires OPENAI_API_KEY environment variable.
Skipped if key is not available or is fake.

Tests the full pipeline:
  LLM generates → validate_node checks format → duplicate_check → persist as Question model
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Load .env if available
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().strip().splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key, val)

# Skip if no real OpenAI key
_key = os.environ.get("OPENAI_API_KEY", "")
_has_real_key = _key.startswith("sk-") and "fake" not in _key and len(_key) > 20

pytestmark = pytest.mark.skipif(
    not _has_real_key,
    reason="Requires real OPENAI_API_KEY (set in .env)",
)


@pytest.mark.asyncio
async def test_generate_question_computer_vision():
    """Generate a Computer Vision question via LLM, validate, check dups."""
    from src.ai.agents.generator_agent.nodes.generate_node import generate_node
    from src.ai.agents.generator_agent.nodes.validate_node import validate_node
    from src.ai.agents.generator_agent.tools.duplicate_check_tool import check_duplicate
    from src.api.domain.models.question import Question
    from src.seed.loader import load_seed_file, validate_questions

    # Load examples
    raw = load_seed_file()
    validated = validate_questions(raw)
    examples = [q.model_dump() for q in validated[:3]]

    state = {
        "certification": "AI-103",
        "target_domain": "Computer Vision",
        "example_questions": examples,
        "feedback_context": None,
        "generated_question": None,
        "is_valid": False,
        "validation_errors": [],
    }

    # Generate
    gen_result = await generate_node(state)
    assert gen_result.get("generated_question") is not None, (
        f"Generation failed: {gen_result.get('validation_errors')}"
    )

    question = gen_result["generated_question"]

    # Validate format
    val_result = validate_node({**state, "generated_question": question})
    assert val_result["is_valid"], f"Validation failed: {val_result['validation_errors']}"

    # Check not a duplicate of seed
    dup_result = check_duplicate(question["text"], [q.model_dump() for q in validated])
    assert not dup_result["is_duplicate"], (
        f"Generated duplicate (score={dup_result['similarity_score']:.2f})"
    )

    # Persist as model
    question["id"] = str(uuid.uuid4())
    question["created_at"] = datetime.now(timezone.utc).isoformat()
    question["quality_score"] = 1.0
    question["is_active"] = True
    question["generated_by"] = "generator_agent"

    persisted = Question(**question)
    assert persisted.domain == "Computer Vision"
    assert persisted.certification == "AI-103"
    assert len(persisted.options) == 4
    assert 0 <= persisted.correct_answer_index <= 3
    assert len(persisted.short_explanation) <= 200
    assert persisted.generated_by == "generator_agent"


@pytest.mark.asyncio
async def test_generate_question_with_feedback_context():
    """Generate with feedback context (simulating quality improvement loop)."""
    from src.ai.agents.generator_agent.nodes.generate_node import generate_node
    from src.ai.agents.generator_agent.nodes.validate_node import validate_node
    from src.api.domain.models.question import Question
    from src.seed.loader import load_seed_file, validate_questions

    raw = load_seed_file()
    validated = validate_questions(raw)
    examples = [q.model_dump() for q in validated if q.domain == "Text Analysis"]

    state = {
        "certification": "AI-103",
        "target_domain": "Text Analysis",
        "example_questions": examples,
        "feedback_context": [
            {"flag_type": "too_easy", "count": 3, "comment": "Questions are too basic"},
            {"flag_type": "ambiguous", "count": 2, "comment": "Wording is confusing"},
        ],
        "generated_question": None,
        "is_valid": False,
        "validation_errors": [],
    }

    gen_result = await generate_node(state)
    assert gen_result.get("generated_question") is not None

    question = gen_result["generated_question"]
    val_result = validate_node({**state, "generated_question": question})
    assert val_result["is_valid"], f"Validation failed: {val_result['validation_errors']}"

    # Verify it can be persisted
    question["id"] = str(uuid.uuid4())
    question["created_at"] = datetime.now(timezone.utc).isoformat()
    question["quality_score"] = 1.0
    question["is_active"] = True
    question["generated_by"] = "generator_agent"

    persisted = Question(**question)
    assert persisted.domain == "Text Analysis"
    assert persisted.generated_by == "generator_agent"


@pytest.mark.asyncio
async def test_full_generator_graph_execution():
    """Run the complete Generator Agent graph (generate → validate)."""
    from src.ai.agents.generator_agent.graph import build_generator_graph
    from src.seed.loader import load_seed_file, validate_questions

    raw = load_seed_file()
    validated = validate_questions(raw)
    examples = [q.model_dump() for q in validated[:2]]

    graph = build_generator_graph()

    result = await graph.ainvoke({
        "certification": "AI-103",
        "target_domain": "Information Extraction",
        "example_questions": examples,
        "feedback_context": None,
        "generated_question": None,
        "is_valid": False,
        "validation_errors": [],
    })

    # The graph should have generated and validated
    assert result["generated_question"] is not None
    assert result["is_valid"] is True
    assert result["validation_errors"] == []
    assert result["generated_question"]["domain"] == "Information Extraction"
    assert result["generated_question"]["certification"] == "AI-103"
