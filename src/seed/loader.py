"""Seed question loader for Certification Genie.

Validates seed questions against the Question model schema and loads
them into the CosmosDB questions container. Can be run as a standalone
script or imported as a module.

Usage:
    python -m src.seed.loader
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.api.domain.models.question import Question
from src.api.infrastructure.cosmos_client import CosmosDBClient, get_cosmos_client


SEED_FILE = Path(__file__).parent / "seed_questions.json"

VALID_DOMAINS = {
    "Generative AI and Agents",
    "Computer Vision",
    "Text Analysis",
    "Information Extraction",
    "Plan and Manage",
}


def load_seed_file(path: Path | None = None) -> list[dict]:
    """Load and parse the seed questions JSON file.

    Args:
        path: Optional path to the JSON file. Defaults to seed_questions.json
              in the same directory as this module.

    Returns:
        List of raw question dictionaries.

    Raises:
        FileNotFoundError: If the seed file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    file_path = path or SEED_FILE
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_questions(raw_questions: list[dict]) -> list[Question]:
    """Validate raw question dictionaries against the Question model.

    Adds created_at timestamp and default fields (quality_score, is_active,
    generated_by) if not present in the raw data.

    Args:
        raw_questions: List of dictionaries from the seed JSON file.

    Returns:
        List of validated Question model instances.

    Raises:
        ValueError: If any question fails validation, with details about
                    which question and what validation error occurred.
    """
    validated: list[Question] = []
    errors: list[str] = []

    for i, raw in enumerate(raw_questions):
        question_id = raw.get("id", f"index-{i}")
        try:
            # Ensure required defaults are set
            if "created_at" not in raw:
                raw["created_at"] = datetime.now(timezone.utc).isoformat()
            if "quality_score" not in raw:
                raw["quality_score"] = 1.0
            if "is_active" not in raw:
                raw["is_active"] = True
            if "generated_by" not in raw:
                raw["generated_by"] = "seed"

            # Validate domain is one of the expected AI-103 domains
            domain = raw.get("domain", "")
            if domain not in VALID_DOMAINS:
                errors.append(
                    f"Question '{question_id}': invalid domain '{domain}'. "
                    f"Must be one of: {sorted(VALID_DOMAINS)}"
                )
                continue

            # Validate certification is AI-103
            certification = raw.get("certification", "")
            if certification != "AI-103":
                errors.append(
                    f"Question '{question_id}': certification must be 'AI-103', "
                    f"got '{certification}'"
                )
                continue

            question = Question(**raw)
            validated.append(question)

        except Exception as e:
            errors.append(f"Question '{question_id}': {e}")

    if errors:
        error_msg = "Seed question validation failed:\n" + "\n".join(
            f"  - {err}" for err in errors
        )
        raise ValueError(error_msg)

    return validated


async def load_to_cosmos(
    questions: list[Question],
    client: CosmosDBClient | None = None,
) -> int:
    """Load validated questions into the CosmosDB questions container.

    Uses upsert to avoid duplicates — if a question with the same id
    already exists, it will be updated.

    Args:
        questions: List of validated Question model instances.
        client: Optional CosmosDBClient instance. If None, uses the
                module-level singleton.

    Returns:
        Number of questions successfully loaded.
    """
    cosmos = client or get_cosmos_client()
    await cosmos.initialize()

    loaded_count = 0
    container = cosmos.questions

    for question in questions:
        doc = question.model_dump(mode="json")
        # CosmosDB requires a string id and partition key
        doc["id"] = question.id
        await container.upsert_item(doc)
        loaded_count += 1

    return loaded_count


async def run_loader(path: Path | None = None) -> None:
    """Full seed loading pipeline: load file, validate, persist to CosmosDB.

    Args:
        path: Optional path to the seed questions JSON file.
    """
    print("Loading seed questions...")
    raw_questions = load_seed_file(path)
    print(f"  Found {len(raw_questions)} questions in seed file.")

    print("Validating questions...")
    validated = validate_questions(raw_questions)
    print(f"  All {len(validated)} questions passed validation.")

    # Check domain distribution
    domain_counts: dict[str, int] = {}
    for q in validated:
        domain_counts[q.domain] = domain_counts.get(q.domain, 0) + 1
    print("  Domain distribution:")
    for domain, count in sorted(domain_counts.items()):
        print(f"    - {domain}: {count}")

    print("Loading into CosmosDB...")
    cosmos = get_cosmos_client()
    try:
        count = await load_to_cosmos(validated, cosmos)
        print(f"  Successfully loaded {count} questions.")
    finally:
        await cosmos.close()


def main() -> None:
    """Entry point for running the loader as a script."""
    try:
        asyncio.run(run_loader())
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load seed questions: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
