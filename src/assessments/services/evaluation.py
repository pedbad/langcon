# src/assessments/services/evaluation.py

from __future__ import annotations

from ..llm_client import get_openai_client
from ..models import Assessment
from ..vendor.evaluation import generate_evaluation as _gen_eval

DEFAULT_MODEL = "gpt-4o-mini"


def _build_evaluation_inputs_from_assessment(
    assessment: Assessment,
) -> tuple[str, str, str, str, str, str, str, str, str]:
    """
    Extract all necessary text fields from an Assessment to feed the vendor evaluation function.

    Returns:
        (stat, q1, a1, q2, a2, lc_trans, lc_ans, rc_trans, rc_ans)
    """
    # Initial statement
    stat = (assessment.writing_answer_final or "").strip()

    # Follow-up Q1 + answer
    q1 = (assessment.llm_question_1 or "").strip()
    a1 = (assessment.llm_question_1_answer_final or "").strip()

    # Follow-up Q2 + answer
    q2 = (assessment.llm_question_2 or "").strip()
    a2 = (assessment.llm_question_2_answer_final or "").strip()

    # Listening: we don't store a full transcript; provide a descriptive stand-in
    listening_instruction = (
        "You are going to listen to a lecture related to your subject area. "
        "The lecture is approximately ten minutes long. Write a short summary of the lecture."
    )
    lc_prompt = (assessment.listening_q1_prompt or "").strip()
    lc_ans = (assessment.listening_answer_final or "").strip()

    lc_trans = (
        "A full transcript of the listening passage is not stored in the system. "
        "The student listened to a subject-related lecture and received this instruction:\n\n"
        f"{lc_prompt or listening_instruction}"
    )

    # Reading: build a pseudo-transcript from the DebateTopic
    debate = assessment.reading_debate
    if debate is not None:
        rc_trans = f"""
Debate question:
{debate.question}

Position A – {debate.position_a_title}:
{debate.position_a_body}

Position B – {debate.position_b_title}:
{debate.position_b_body}
""".strip()
    else:
        rc_trans = "No reading debate topic is attached to this assessment."

    rc_ans = (assessment.reading_answer_final or "").strip()

    return stat, q1, a1, q2, a2, lc_trans, lc_ans, rc_trans, rc_ans


def generate_evaluation_for_assessment(
    assessment: Assessment,
    model: str = DEFAULT_MODEL,
) -> tuple[str | None, str | None, str]:
    """
    High-level service wrapper to generate an LLM evaluation for a fully complete Assessment.

    Returns:
        (evaluation_text, error_message, model_name)
    """
    client = get_openai_client()
    stat, q1, a1, q2, a2, lc_trans, lc_ans, rc_trans, rc_ans = (
        _build_evaluation_inputs_from_assessment(assessment)
    )

    try:
        text = _gen_eval(
            client,
            model,
            stat,
            q1,
            a1,
            q2,
            a2,
            lc_trans,
            lc_ans,
            rc_trans,
            rc_ans,
        )
        text = (text or "").strip()
        if not text:
            return None, "Empty response from LLM", model
        return text, None, model
    except Exception as exc:  # noqa: BLE001
        return None, str(exc), model
