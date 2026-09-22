from app.services.gemini_service import run_gemini_agent

from app.tools.financial_tools import (
    get_financial_summary,
    get_expense_by_category,
    get_top_expense_category,
    calculate_purchase_impact,
)


TOOLS = [
    get_financial_summary,
    get_expense_by_category,
    get_top_expense_category,
    calculate_purchase_impact,
]


def run_financial_agent(question: str) -> str:

    if not question:
        return "Digite uma pergunta financeira."

    try:
        return run_gemini_agent(
            message=question,
            tools=TOOLS,
        )

    except Exception as error:

        error_text = str(error)

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota" in error_text.lower()
        ):
            return (
                "⚠️ O modelo de IA atingiu temporariamente "
                "o limite de uso da API Gemini.\n\n"
                "O motor financeiro do FinPilot continua funcionando "
                "normalmente. Tente novamente quando a quota da API "
                "estiver disponível."
            )

        raise error