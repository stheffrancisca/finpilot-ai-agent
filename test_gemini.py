from app.services.gemini_service import ask_gemini


response = ask_gemini(
    "Responda apenas: FinPilot conectado com sucesso."
)

print(response)