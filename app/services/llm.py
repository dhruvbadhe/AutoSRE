import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.LLM_MODEL)

def generate_text(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text if response and response.text else ""