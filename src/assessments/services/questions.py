# src/assessments/services/questions.py
"""
Service wrapper to generate two follow-up questions from the student's initial statement.

- Calls the colleague's vendor function (unchanged prompt logic).
- Adds a minimal retry if the model returns non-JSON.
- Validates the expected keys are present.
"""

import json
from typing import Dict, Any

# Parent-relative imports:
# - llm_client is in the assessments package root (..)
# - vendor.lcon is our copied colleague function (..)
from ..llm_client import get_openai_client
from ..vendor.lcon import generate_questions as _gen_qs

DEFAULT_MODEL = "gpt-4o-mini"


def generate_followups_from_statement(statement: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Calls the colleague’s prompt to get two follow-up questions.
    Returns a dict like: {"question1": "...", "question2": "..."}

    Raises:
        json.JSONDecodeError / ValueError on malformed responses.
        Any OpenAI-related exception is allowed to bubble up to the caller.
    """
    client = get_openai_client()

    # First attempt: as-is
    try:
        data = _gen_qs(client, model, statement)
    except json.JSONDecodeError:
        # Retry once, with an even stricter JSON instruction appended to the statement.
        retry_statement = (
            statement
            + '\n\nIMPORTANT: Return ONLY valid JSON like {"question1":"...","question2":"..."} '
              'using double quotes and no extra text.'
        )
        data = _gen_qs(client, model, retry_statement)

    # Validate shape
    if not isinstance(data, dict) or not {"question1", "question2"} <= set(data.keys()):
        raise ValueError("LLM did not return the expected JSON keys: question1, question2")

    return data
