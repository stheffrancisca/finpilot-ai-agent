import re

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
# FORMATAÇÃO
# =========================================================

def format_brl(value):
    value = float(value)

    formatted = f"{value:,.2f}"

    formatted = (
        formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {formatted}"


# =========================================================
# ROTEAMENTO RÁPIDO
# =========================================================

def try_fast_route(question: str, df):

    text = question.lower().strip()

    # -----------------------------------------------------
    # SIMULAÇÃO DE COMPRA
    # -----------------------------------------------------

    purchase_keywords = [
        "gastar",
        "gasta",
        "gasto",
        "comprar",
        "compra",
        "posso",
        "pagar",
    ]

    has_purchase_intent = any(
        keyword in text
        for keyword in purchase_keywords
    )

    if has_purchase_intent:

        money_match = re.search(
            r"(?:R\$\s*)?(\d[\d.,]*)",
            text
        )

        if money_match:

            raw_value = money_match.group(1)

            if "." in raw_value and "," in raw_value:
                raw_value = (
                    raw_value
                    .replace(".", "")
                    .replace(",", ".")
                )

            elif "," in raw_value:
                raw_value = raw_value.replace(
                    ",",
                    "."
                )

            elif (
                "." in raw_value
                and len(
                    raw_value.split(".")[-1]
                ) == 3
            ):
                raw_value = raw_value.replace(
                    ".",
                    ""
                )

            try:
                purchase_amount = float(
                    raw_value
                )

                result = calculate_purchase_impact(
                    df,
                    purchase_amount
                )

                write_audit_event(
                    event_type="fast_tool_call",
                    user_question=question,
                    status="success",
                    extra={
                        "tool": "calculate_purchase_impact",
                        "arguments": {
                            "purchase_amount": purchase_amount
                        },
                        "result": result,
                    },
                )

                risk_label = (
                    result["risk"]
                    .upper()
                )

                return (
                    f"### Análise da compra\n\n"
                    f"**Valor:** "
                    f"{format_brl(result['purchase_amount'])}\n\n"
                    f"**Saldo atual:** "
                    f"{format_brl(result['current_balance'])}\n\n"
                    f"**Saldo após a compra:** "
                    f"{format_brl(result['remaining_balance'])}\n\n"
                    f"**Limite seguro:** "
                    f"{format_brl(result['safe_spend'])}\n\n"
                    f"**Uso do limite seguro:** "
                    f"{result['usage_percentage']:.2f}%\n\n"
                    f"**Risco:** {risk_label}"
                )

            except ValueError:
                pass

    # -----------------------------------------------------
    # RESUMO FINANCEIRO
    # -----------------------------------------------------

    summary_keywords = [
        "situação financeira",
        "situacao financeira",
        "meu saldo",
        "resumo financeiro",
        "como estão minhas finanças",
        "como estao minhas financas",
    ]

    if any(
        keyword in text
        for keyword in summary_keywords
    ):

        result = get_financial_summary(df)

        write_audit_event(
            event_type="fast_tool_call",
            user_question=question,
            status="success",
            extra={
                "tool": "get_financial_summary",
                "result": result,
            },
        )

        return (
            "### Resumo financeiro\n\n"
            f"**Receitas:** {format_brl(result['income'])}\n\n"
            f"**Despesas:** {format_brl(result['expenses'])}\n\n"
            f"**Saldo atual:** {format_brl(result['balance'])}\n\n"
            f"**Reserva recomendada:** "
            f"{format_brl(result['reserve'])}\n\n"
            f"**Limite seguro para gastos:** "
            f"{format_brl(result['safe_spend'])}"
        )

    # -----------------------------------------------------
    # MAIOR GASTO
    # -----------------------------------------------------

    top_keywords = [
        "maior gasto",
        "maior categoria",
        "categoria que mais",
        "onde gasto mais",
    ]

    if any(
        keyword in text
        for keyword in top_keywords
    ):

        result = get_top_expense_category(df)

        write_audit_event(
            event_type="fast_tool_call",
            user_question=question,
            status="success",
            extra={
                "tool": "get_top_expense_category",
                "result": result,
            },
        )

        if not result["category"]:
            return (
                "Não há despesas suficientes "
                "para identificar a maior categoria."
            )

        return (
            f"Sua maior categoria de gastos é "
            f"**{result['category']}**, com "
            f"**{format_brl(result['amount'])}**."
        )

    # -----------------------------------------------------
    # RECORRÊNCIAS
    # -----------------------------------------------------

    recurring_keywords = [
        "gastos recorrentes",
        "despesas recorrentes",
        "recorrencias",
        "recorrências",
    ]

    if any(
        keyword in text
        for keyword in recurring_keywords
    ):

        results = detect_recurring_expenses(df)

        if not results:
            return (
                "Nenhum gasto recorrente "
                "foi identificado."
            )

        lines = [
            "### Gastos recorrentes\n"
        ]

        for item in results[:5]:

            lines.append(
                f"- **{item['description']}**: "
                f"{item['occurrences']} ocorrências, "
                f"total de "
                f"{format_brl(item['total_amount'])}"
            )

        return "\n".join(lines)

    # -----------------------------------------------------
    # FORECAST
    # -----------------------------------------------------

    forecast_keywords = [
        "fim do mês",
        "fim do mes",
        "forecast",
        "projeção",
        "projecao",
        "quanto terei",
        "quanto vou ter",
    ]

    if any(
        keyword in text
        for keyword in forecast_keywords
    ):

        result = forecast_month_end_balance(df)

        return (
            "### Projeção do mês\n\n"
            f"**Saldo atual:** "
            f"{format_brl(result['current_balance'])}\n\n"
            f"**Média diária de despesas:** "
            f"{format_brl(result['average_daily_expense'])}\n\n"
            f"**Dias restantes:** "
            f"{result['days_remaining']}\n\n"
            f"**Saldo projetado no fim do mês:** "
            f"{format_brl(result['projected_month_end_balance'])}"
        )

    # -----------------------------------------------------
    # ANOMALIAS
    # -----------------------------------------------------

    anomaly_keywords = [
        "gasto fora do padrão",
        "gasto fora do padrao",
        "anomalia",
        "anomalias",
        "gasto estranho",
    ]

    if any(
        keyword in text
        for keyword in anomaly_keywords
    ):

        results = detect_spending_anomalies(df)

        if not results:
            return (
                "Nenhum gasto fora do padrão "
                "foi identificado."
            )

        lines = [
            "### Gastos fora do padrão\n"
        ]

        for item in results[:5]:

            lines.append(
                f"- **{item['description']}**: "
                f"{format_brl(item['amount'])} "
                f"(média histórica: "
                f"{format_brl(item['average_amount'])})"
            )

        return "\n".join(lines)

    return None


# =========================================================
# AGENTE FINANCEIRO
# =========================================================

def run_financial_agent(
    question: str,
    df
) -> str:

    if not question:

        return (
            "Digite uma pergunta para que eu possa "
            "analisar sua situação financeira."
        )

    # -----------------------------------------------------
    # GUARDRAIL DE ENTRADA
    # -----------------------------------------------------

    input_guardrail = check_input_guardrail(
        question
    )

    write_audit_event(
        event_type="input_guardrail",
        user_question=question,
        input_guardrail=input_guardrail,
        status=(
            "allowed"
            if input_guardrail["allowed"]
            else "blocked"
        ),
    )

    if not input_guardrail["allowed"]:
        return input_guardrail["message"]

    # -----------------------------------------------------
    # FAST ROUTE
    # -----------------------------------------------------

    fast_response = try_fast_route(
        question,
        df
    )

    if fast_response is not None:

        output_guardrail = (
            check_output_guardrail(
                fast_response
            )
        )

        write_audit_event(
            event_type="output_guardrail",
            user_question=question,
            output_guardrail=output_guardrail,
            status=(
                "allowed"
                if output_guardrail["allowed"]
                else "blocked"
            ),
        )

        return output_guardrail[
            "message"
        ]

    # -----------------------------------------------------
    # FERRAMENTAS PARA GEMINI
    # -----------------------------------------------------

    def tool_get_financial_summary():
        """Retorna o resumo financeiro atual."""
        return get_financial_summary(df)

    def tool_get_expense_by_category(
        category: str
    ):
        """Retorna o total gasto em uma categoria."""
        return get_expense_by_category(
            df,
            category
        )

    def tool_get_top_expense_category():
        """Retorna a categoria com maior gasto."""
        return get_top_expense_category(df)

    def tool_calculate_purchase_impact(
        purchase_amount: float
    ):
        """Calcula o impacto financeiro de uma compra."""
        return calculate_purchase_impact(
            df,
            purchase_amount
        )

    def tool_detect_recurring_expenses():
        """Detecta gastos recorrentes."""
        return detect_recurring_expenses(df)

    def tool_forecast_month_end_balance():
        """Projeta o saldo até o fim do mês."""
        return forecast_month_end_balance(df)

    def tool_detect_spending_anomalies():
        """Detecta gastos fora do padrão."""
        return detect_spending_anomalies(df)

    tools = [
        tool_get_financial_summary,
        tool_get_expense_by_category,
        tool_get_top_expense_category,
        tool_calculate_purchase_impact,
        tool_detect_recurring_expenses,
        tool_forecast_month_end_balance,
        tool_detect_spending_anomalies,
    ]

    # -----------------------------------------------------
    # GEMINI
    # -----------------------------------------------------

    try:

        response = run_gemini_agent(
            message=question,
            tools=tools,
        )

        output_guardrail = (
            check_output_guardrail(
                response
            )
        )

        write_audit_event(
            event_type="output_guardrail",
            user_question=question,
            output_guardrail=output_guardrail,
            status=(
                "allowed"
                if output_guardrail["allowed"]
                else "blocked"
            ),
        )

        if not output_guardrail["allowed"]:
            return output_guardrail["message"]

        return output_guardrail[
            "message"
        ]

    except Exception as error:

        error_text = str(error)

        write_audit_event(
            event_type="agent_error",
            user_question=question,
            status="error",
            error=error_text,
        )

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota" in error_text.lower()
        ):

            return (
                "A IA atingiu temporariamente "
                "o limite de uso da API Gemini.\n\n"
                "Os recursos financeiros locais "
                "continuam funcionando normalmente."
            )

        raise error