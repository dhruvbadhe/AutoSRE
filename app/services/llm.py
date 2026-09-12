import time
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.LLM_MODEL)

def generate_text(prompt: str, max_retries: int = 5) -> str:
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text if response and response.text else ""
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower():
                if attempt < max_retries - 1:
                    sleep_time = 15.0
                    if "retry in " in err_str:
                        try:
                            seconds_str = err_str.split("retry in ")[1].split("s")[0].strip()
                            sleep_time = float(seconds_str) + 1.0
                        except Exception:
                            sleep_time = 20.0
                    time.sleep(sleep_time)
                    continue
            raise e
    return ""