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
    detect_spending_anomalies,
)


def run_financial_agent(
    question: str,
    df
) -> str:

    if not question:
        return (
            "Digite uma pergunta para que eu possa "
            "analisar sua situação financeira."
        )

    # Wrappers fechando sobre o DataFrame atual
    def tool_get_financial_summary():
        return get_financial_summary(df)

    def tool_get_expense_by_category(
        category: str
    ):
        return get_expense_by_category(
            df,
            category
        )

    def tool_get_top_expense_category():
        return get_top_expense_category(
            df
        )

    def tool_calculate_purchase_impact(
        purchase_amount: float
    ):
        return calculate_purchase_impact(
            df,
            purchase_amount
        )

    def tool_detect_recurring_expenses():
        return detect_recurring_expenses(
            df
        )

    def tool_forecast_month_end_balance():
        return forecast_month_end_balance(
            df
        )

    def tool_detect_spending_anomalies():
        return detect_spending_anomalies(
            df
        )

    tools = [
        tool_get_financial_summary,
        tool_get_expense_by_category,
        tool_get_top_expense_category,
        tool_calculate_purchase_impact,
        tool_detect_recurring_expenses,
        tool_forecast_month_end_balance,
        tool_detect_spending_anomalies,
    ]

    try:

        return run_gemini_agent(
            message=question,
            tools=tools,
        )

    except Exception as error:

        error_text = str(error)

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota" in error_text.lower()
        ):

            return (
                "A IA atingiu temporariamente "
                "o limite de uso da API Gemini.\n\n"
                "Os cálculos financeiros e insights "
                "continuam disponíveis normalmente."
            )

        raise error