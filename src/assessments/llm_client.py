# src/assessments/llm_client.py
import os
from openai import OpenAI

def get_openai_client():
    """
    Returns an authenticated OpenAI client using the key
    from your .env or environment.
    """
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
