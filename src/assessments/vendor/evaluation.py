# src/assessments/vendor/evaluation.py

def generate_eval_template(
    stat: str,
    q1: str,
    a1: str,
    q2: str,
    a2: str,
    lc_trans: str,
    lc_ans: str,
    rc_trans: str,
    rc_ans: str,
) -> str:
    """
    Utility function to incorporate the various user data into the user prompt.
    Mirrors your colleague's generate_eval_template, but kept here as a vendor helper.
    """
    user_prompt = f"""
Here is the data relevant for the evaluation:

INITIAL STATEMENT
{stat}

QUESTION 1
{q1}
ANSWER 1
{a1}

QUESTION 2
{q2}
ANSWER 2
{a2}

LISTENING_COMPREHENSION_INSTRUCTION
Listen to the lecture and provide a summary in no more than 250 words.

LISTENING_COMPREHENSION_TRANSCRIPT
{lc_trans}

LISTENING_COMPREHENSION_ANSWER
{lc_ans}

READING_COMPREHENSION_INSTRUCTION
Read the following two opening statements in a debate on a controversial topic. Summarise the two statements and state your own 
point of view of the issues. Your answer should be no more than 250 words.

READING_COMPREHENSION_TRANSCRIPT
{rc_trans}

READING_COMPREHENSION_ANSWER
{rc_ans}
""".strip()

    return user_prompt


EVAL_SYSTEM_PROMPT = """
You are an academic admissions tutor evaluating applicants’ written submissions for research degrees (e.g., PhDs).
For each applicant, you will receive:

An initial statement outlining the rationale for study or proposed research.

Two follow-up questions and the applicant’s answers: one addressing content, one addressing language.

A listening comprehension task, including the lecture transcript or description and the applicant’s summary.

A reading comprehension task, including two debate statements and the applicant’s summary and response.

Your task is to write a concise evaluation (≤150 words) of the applicant’s responses across all tasks, focusing on these five areas:

Lexical choices – connotation/denotation, register, specificity, and collocations.
Metalinguistic awareness – how wording, syntax, or figurative language shapes meaning.
Audience awareness – understanding of readers’ prior knowledge, stance, tone, and appropriateness.
Cohesion and coherence – clarity of linking within and across sentences/paragraphs; overall unity and flow.
Revision and reflection – identify one specific change that would most improve clarity, emphasis, or flow.

The evaluation should:

Cover all five focus areas.
Use professional, academic tone and precise terminology.
Be analytical yet concise — no longer than 150 words.
Avoid quoting large portions of the applicant’s text; paraphrase where necessary.
""".strip()


def generate_evaluation(
    opai,
    model: str,
    stat: str,
    q1: str,
    a1: str,
    q2: str,
    a2: str,
    lc_trans: str,
    lc_ans: str,
    rc_trans: str,
    rc_ans: str,
) -> str:
    """
    Passes the user data to the LLM and returns an evaluation string.

    Args:
        opai: OpenAI client instance.
        model: model name, e.g. "gpt-4o-mini".
        stat: initial statement by the user.
        q1, a1: first question and answer.
        q2, a2: second question and answer.
        lc_trans, lc_ans: listening 'transcript' / description and answer.
        rc_trans, rc_ans: reading 'transcript' and answer.

    Returns:
        evaluation text (str)
    """
    user_prompt = generate_eval_template(stat, q1, a1, q2, a2, lc_trans, lc_ans, rc_trans, rc_ans)

    messages = [
        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    response = opai.chat.completions.create(
        model=model,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()
