from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag.rag.agent.graph import build_graph


@dataclass
class EvaluationSample:
    question: str
    ground_truth: str


@dataclass
class EvaluationResult:
    faithfulness: float | None
    answer_relevancy: float | None
    context_recall: float | None
    raw: dict


async def run_evaluation(
    samples: list[EvaluationSample],
    db: AsyncSession,
) -> EvaluationResult:
    """Run a Ragas evaluation over a set of question/ground-truth pairs.

    For each sample the full agent graph is invoked to get an answer and contexts.
    """
    graph = build_graph(db)
    questions, answers, contexts, ground_truths = [], [], [], []

    for sample in samples:
        from rag.db.models.conversation import Conversation

        conversation = Conversation()
        db.add(conversation)
        await db.flush()

        state = await graph.ainvoke(
            {
                "conversation_id": str(conversation.id),
                "user_message": sample.question,
                "messages": [],
                "retrieved_chunks": [],
                "answer": "",
                "sources": [],
                "needs_retrieval": False,
            }
        )

        questions.append(sample.question)
        answers.append(state["answer"])
        contexts.append([c["content"] for c in state.get("retrieved_chunks", [])] or [""])
        ground_truths.append(sample.ground_truth)

    # Lazy imports to avoid ragas/mistralai version conflict at app startup
    from datasets import Dataset  # noqa: PLC0415
    from ragas import evaluate  # noqa: PLC0415
    from ragas.metrics import (  # noqa: PLC0415
        answer_relevancy,
        context_recall,
        faithfulness,
    )

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
    )

    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_recall])
    scores = result.to_pandas().mean(numeric_only=True).to_dict()

    return EvaluationResult(
        faithfulness=scores.get("faithfulness"),
        answer_relevancy=scores.get("answer_relevancy"),
        context_recall=scores.get("context_recall"),
        raw=scores,
    )
