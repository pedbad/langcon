# src/assessments/vendor/lcon.py
import json

def generate_questions(opai, model, statement):
    """ Passes a statement to the model and returns two follow up questions in JSON format
    Args:
        opai - link to the OpenAI api interface
        model - model to be used i.e. 'gpt-5-mini'
        statement - the statement used to produce to follow-up questions
    Returns: a JSON object containing the two questions
    """
    system_prompt = """You are a university admissions tuto...ible for assessing applicants’ proficiency in Academic English. 
As part of the assessment process, you receive an initial statement from each applicant explaining their reasons 
for wanting to study at the university and, for PhD applicants, an outline of their intended research. 

Your task is to produce exactly two brief follow-up questions addressed directly to the student:
• The first question should focus on the **content** of the statement (ideas, motivation, or research focus).  
• The second question should focus on the **language**, ask...n, or the rationale behind a particular wording or expression.  
"""

    user_prompt = f"""Here is the applicant’s initial statement:

{statement}
"""

    # Call the OpenAI API
    response = opai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    reply = response.choices[0].message.content
    data = json.loads(reply)  # safely parse the JSON output
    return data
