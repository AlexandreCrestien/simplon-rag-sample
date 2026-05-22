import logging
from functools import partial

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from rag.config.settings import get_settings
from rag.rag.agent.nodes import (
    escalate,
    evaluate,
    generate,
    guard_route,
    load_history,
    retrieve,
    save_turn,
)
from rag.rag.agent.state import AgentState


def _guard_route_decision(state: AgentState) -> str:
    in_scope = state.get("in_scope", True)
    needs_retrieval = state.get("needs_retrieval")
    
    # LOG : On explique pourquoi on choisit ce chemin
    logging.info("Guard route decision", extra={
        "conversation_id": state.get("conversation_id"),
        "node": "guard_route_decision",
        "in_scope": in_scope,
        "needs_retrieval": needs_retrieval
    })

    if not in_scope:
        return "save_turn"
    return "retrieve" if needs_retrieval else "generate"


def _eval_decision(state: AgentState) -> str:
    retry_count = state.get("retry_count", 0)
    max_retries = get_settings().agent_max_retries
    decision = state.get("eval_decision", "answer")
    
    # LOG : On trace l'évaluation pour la reconstitution de session
    logging.info("Evaluation routing decision", extra={
        "conversation_id": state.get("conversation_id"),
        "node": "eval_decision",
        "retry_count": retry_count,
        "decision": decision,
        "score": state.get("eval_score")
    })

    if retry_count >= max_retries:
        # LOG : Niveau WARNING car on a échoué à trouver une réponse après X tentatives
        logging.warning("Max retries reached, escalating to human", extra={
            "conversation_id": state.get("conversation_id"),
            "retry_count": retry_count
        })
        return "escalate"
        
    return decision


def build_graph(db: AsyncSession):
    """Build and compile the LangGraph RAG agent.

    Nodes that need DB access receive it via functools.partial so the graph
    interface stays clean (state-only inputs).

    Graph flow:
        load_history → guard_route → (out_of_scope) ─────────────────────────────────> save_turn
                                   → (no retrieval) → generate → evaluate → answer ──> save_turn
                                   → (retrieval)    → retrieve → generate → evaluate ↗
                                                                           → rewrite → retrieve (max 2)
                                                                           → escalate → escalate → save_turn
    """
    graph = StateGraph(AgentState)

    graph.add_node("load_history", partial(load_history, db=db))
    graph.add_node("guard_route", guard_route)
    graph.add_node("retrieve", partial(retrieve, db=db))
    graph.add_node("generate", generate)
    graph.add_node("evaluate", evaluate)
    graph.add_node("escalate", escalate)
    graph.add_node("save_turn", partial(save_turn, db=db))

    graph.add_edge(START, "load_history")
    graph.add_edge("load_history", "guard_route")
    graph.add_conditional_edges(
        "guard_route",
        _guard_route_decision,
        {"save_turn": "save_turn", "retrieve": "retrieve", "generate": "generate"},
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        _eval_decision,
        {"answer": "save_turn", "rewrite": "retrieve", "escalate": "escalate"},
    )
    graph.add_edge("escalate", "save_turn")
    graph.add_edge("save_turn", END)

    rag_graph = graph.compile()

    return rag_graph
