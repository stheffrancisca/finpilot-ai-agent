import os
import time

from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY não encontrada. Verifique o arquivo .env."
    )

client = genai.Client(api_key=api_key)


def ask_gemini(prompt, max_retries=3):

    last_error = None

    for attempt in range(max_retries):

        try:
            chat = client.chats.create(
                model="gemini-3.6-flash"
            )

            response = chat.send_message(prompt)

            return response.text

        except Exception as error:

            last_error = error

            if attempt < max_retries - 1:
                time.sleep(2)

    raise last_error