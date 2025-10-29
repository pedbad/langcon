import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
print("ENV:", os.getenv("ENV"))
print("EMAIL_FILE_PATH:", os.getenv("EMAIL_FILE_PATH"))
