from app.services.gemini_service import (
    run_gemini_agent,
)

from app.services.guardrails import (
    check_input_guardrail,
    check_output_guardrail,
)

from app.services.audit import (
    write_audit_event,
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


# =========================================================
# AGENTE FINANCEIRO
# =========================================================

def run_financial_agent(
    question: str,
    df
) -> str:

    # =====================================================
    # 1. VALIDAÇÃO
    # =====================================================

    if not question:

        return (
            "Digite uma pergunta para que eu possa "
            "analisar sua situação financeira."
        )

    question = question.strip()

    # =====================================================
    # 2. GUARDRAIL DE ENTRADA
    # =====================================================

    input_guardrail = (
        check_input_guardrail(
            question
        )
    )

    # -----------------------------------------------------
    # BLOQUEADO
    # -----------------------------------------------------

    if not input_guardrail["allowed"]:

        write_audit_event(
            event_type="input_guardrail",
            status="blocked",
            input_guardrail=input_guardrail,
            extra={
                "prompt": question,
            },
        )

        return (
            input_guardrail[
                "message"
            ]
        )

    # -----------------------------------------------------
    # PERMITIDO
    # -----------------------------------------------------

    write_audit_event(
        event_type="input_guardrail",
        status="allowed",
        input_guardrail=input_guardrail,
        extra={
            "prompt": question,
        },
    )

    # =====================================================
    # 3. FERRAMENTAS
    # =====================================================

    def tool_get_financial_summary():

        result = (
            get_financial_summary(
                df
            )
        )

        write_audit_event(
            event_type="tool_call",
            status="success",
            extra={
                "prompt":
                    question,

                "tool":
                    "get_financial_summary",
            },
        )

        return result


    def tool_get_expense_by_category(
        category: str
    ):

        result = (
            get_expense_by_category(
                df,
                category
            )
        )

        write_audit_event(
            event_type="tool_call",
            status="success",
            extra={
                "prompt":
                    question,

                "tool":
                    "get_expense_by_category",

                "category":
                    category,
            },
        )

        return result


    def tool_get_top_expense_category():

        result = (
            get_top_expense_category(
                df
            )
        )

        write_audit_event(
            event_type="tool_call",
            status="success",
            extra={
                "prompt":
                    question,

                "tool":
                    "get_top_expense_category",
            },
        )

        return result


    def tool_calculate_purchase_impact(
        purchase_amount: float
    ):

        result = (
            calculate_purchase_impact(
                df,
                purchase_amount
            )
        )

        write_audit_event(
            event_type="tool_call",
            status="success",
            extra={
                "prompt":
                    question,

                "tool":
                    "calculate_purchase_impact",

                "purchase_amount":
                    float(
                        purchase_amount
                    ),
            },
        )

        return result


    def tool_detect_recurring_expenses():

        result = (
            detect_recurring_expenses(
                df
            )
        )

        write_audit_event(
            event_type="tool_call",
            status="success",
            extra={
                "prompt":
                    question,

                "tool":
                    "detect_recurring_expenses",
            },
        )

        return result


    def tool_forecast_month_end_balance():

        result = (
            forecast_month_end_balance(
                df
            )
        )

        write_audit_event(
            event_type="tool_call",
            status="success",
            extra={
                "prompt":
                    question,

                "tool":
                    "forecast_month_end_balance",
            },
        )

        return result


    def tool_detect_spending_anomalies():

        result = (
            detect_spending_anomalies(
                df
            )
        )

        write_audit_event(
            event_type="tool_call",
            status="success",
            extra={
                "prompt":
                    question,

                "tool":
                    "detect_spending_anomalies",
            },
        )

        return result


    tools = [
        tool_get_financial_summary,
        tool_get_expense_by_category,
        tool_get_top_expense_category,
        tool_calculate_purchase_impact,
        tool_detect_recurring_expenses,
        tool_forecast_month_end_balance,
        tool_detect_spending_anomalies,
    ]

    # =====================================================
    # 4. EXECUÇÃO DO AGENTE
    # =====================================================

    try:

        response = (
            run_gemini_agent(
                message=question,
                tools=tools,
            )
        )

        # =================================================
        # 5. GUARDRAIL DE SAÍDA
        # =================================================

        output_guardrail = (
            check_output_guardrail(
                response
            )
        )

        # -------------------------------------------------
        # RESPOSTA BLOQUEADA
        # -------------------------------------------------

        if not output_guardrail[
            "allowed"
        ]:

            write_audit_event(
                event_type="output_guardrail",
                status="blocked",
                output_guardrail=output_guardrail,
                extra={
                    "prompt":
                        question,
                },
            )

            return (
                output_guardrail[
                    "message"
                ]
            )

        # -------------------------------------------------
        # RESPOSTA PERMITIDA
        # -------------------------------------------------

        write_audit_event(
            event_type="output_guardrail",
            status="allowed",
            output_guardrail=output_guardrail,
            extra={
                "prompt":
                    question,
            },
        )

        return (
            output_guardrail[
                "message"
            ]
        )

    # =====================================================
    # 6. TRATAMENTO DE ERRO
    # =====================================================

    except Exception as error:

        error_text = str(
            error
        )

        write_audit_event(
            event_type="agent_error",
            status="error",
            extra={
                "prompt":
                    question,

                "error":
                    error_text,
            },
        )

        # -------------------------------------------------
        # QUOTA GEMINI
        # -------------------------------------------------

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED"
            in error_text
            or "quota"
            in error_text.lower()
        ):

            return (
                "A IA atingiu temporariamente "
                "o limite de uso da API Gemini.\n\n"
                "Os cálculos financeiros e insights "
                "continuam disponíveis normalmente."
            )

        raise