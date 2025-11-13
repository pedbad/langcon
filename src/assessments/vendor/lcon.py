# src/assessments/vendor/lcon.py
import json


def generate_questions(opai, model, statement):
    """
    Pass a statement to the model and return two follow-up questions as JSON.

    Args:
        opai: OpenAI client instance.
        model: Model name, e.g. "gpt-4o-mini".
        statement: The applicant's initial statement.

    Returns:
        dict: {"question1": "...", "question2": "..."}
    """

    system_prompt = (
        "You are a university admissions tutor responsible for assessing applicants’ "
        "proficiency in Academic English.\n"
        "As part of the assessment process, you receive an initial statement from each "
        "applicant explaining their reasons for wanting to study at the university and, "
        "for PhD applicants, an outline of their intended research.\n\n"
        "Your task is to produce exactly two brief follow-up questions addressed directly "
        "to the student:\n"
        "• The first question should focus on the content of the statement (ideas, "
        "motivation, or research focus).\n"
        "• The second question should focus on the language, asking the student to reflect "
        "on a choice of wording, cohesion, or the rationale behind a particular "
        "expression.\n\n"
        'Return ONLY a valid JSON object with keys "question1" and "question2".'
    )

    user_prompt = "Here is the applicant’s initial statement:\n\n" f"{statement}\n"

    # Call the OpenAI API
    response = opai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    reply = response.choices[0].message.content
    data = json.loads(reply)  # parse the JSON output
    return data
