"""Generator Agent graph — compiles the StateGraph: generate → validate.

The Generator Agent is responsible for producing new certification questions.
It uses an LLM to generate questions with domain context and examples, then
validates the output format before the question can be persisted.
"""

from langgraph.graph import END, StateGraph

from src.ai.agents.generator_agent.nodes.generate_node import generate_node
from src.ai.agents.generator_agent.nodes.validate_node import validate_node
from src.ai.agents.generator_agent.state import GeneratorState


def build_generator_graph() -> StateGraph:
    """Build and compile the Generator Agent graph.

    Graph flow:
        generate → validate → END

    The generate node invokes an LLM to produce a question dict.
    The validate node checks format constraints (4 options, correct index,
    explanation lengths). The resulting state indicates whether the question
    is valid via `is_valid` and any errors via `validation_errors`.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = StateGraph(GeneratorState)

    graph.add_node("generate", generate_node)
    graph.add_node("validate", validate_node)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", END)

    return graph.compile()
