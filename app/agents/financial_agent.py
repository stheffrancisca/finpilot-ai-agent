from app.services.gemini_service import (
    run_gemini_agent,
)

from app.tools.financial_tools import (
    get_financial_summary,
    get_expense_by_category,
    get_top_expense_category,
    calculate_purchase_impact,
    detect_recurring_expenses,
    forecast_month_end_balance,
)


TOOLS = [
    get_financial_summary,
    get_expense_by_category,
    get_top_expense_category,
    calculate_purchase_impact,
    detect_recurring_expenses,
    forecast_month_end_balance,
]


def run_financial_agent(
    question: str
) -> str:

    if not question:
        return (
            "Digite uma pergunta para que eu possa "
            "analisar sua situação financeira."
        )

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
                "A IA atingiu temporariamente o limite de uso da API Gemini.\n\n"
                "O motor financeiro continua funcionando normalmente."
            )

        raise error