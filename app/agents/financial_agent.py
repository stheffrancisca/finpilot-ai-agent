import re
import unicodedata

import pandas as pd

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
# CONFIGURAÇÕES
# =========================================================

RESERVE_PERCENTAGE = 0.10


# =========================================================
# FORMATAÇÃO
# =========================================================

def format_brl(value):

    try:
        value = float(value)

    except Exception:
        value = 0.0

    formatted = (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {formatted}"


# =========================================================
# NORMALIZA TEXTO
# =========================================================

def normalize_text(value):

    value = str(
        value
        or ""
    ).strip().lower()

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(
            char
        )
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# =========================================================
# EXTRAI VALOR DA PERGUNTA
# =========================================================

def extract_money_amount(
    question
):

    text = (
        str(question)
        .replace("R$", "")
        .replace("r$", "")
    )

    patterns = [
        r"(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"(\d+(?:\.\d{1,2})?)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if not match:
            continue

        value = (
            match.group(1)
            .strip()
        )

        try:

            if "," in value:

                value = (
                    value
                    .replace(".", "")
                    .replace(",", ".")
                )

            return float(
                value
            )

        except Exception:
            continue

    return None


# =========================================================
# DATAFRAME SEGURO
# =========================================================

def prepare_dataframe(
    df
):

    if df is None:

        return pd.DataFrame(
            columns=[
                "date",
                "description",
                "category",
                "type",
                "amount",
            ]
        )

    result = df.copy()

    if (
        "description"
        not in result.columns
    ):

        result[
            "description"
        ] = ""

    if (
        "category"
        not in result.columns
    ):

        result[
            "category"
        ] = "Outros"

    if (
        "type"
        not in result.columns
    ):

        result[
            "type"
        ] = ""

    if (
        "amount"
        not in result.columns
    ):

        result[
            "amount"
        ] = 0.0

    result[
        "description"
    ] = (
        result[
            "description"
        ]
        .astype(str)
        .str.strip()
    )

    result[
        "category"
    ] = (
        result[
            "category"
        ]
        .astype(str)
        .str.strip()
    )

    result[
        "type"
    ] = (
        result[
            "type"
        ]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    result[
        "amount"
    ] = pd.to_numeric(
        result[
            "amount"
        ],
        errors="coerce",
    ).fillna(
        0.0
    )

    return result


# =========================================================
# MÉTRICAS DETERMINÍSTICAS
# =========================================================

def get_local_metrics(
    df
):

    df = prepare_dataframe(
        df
    )

    # -----------------------------------------------------
    # RENDA MENSAL INFORMADA
    # -----------------------------------------------------

    descriptions_normalized = (
        df[
            "description"
        ]
        .apply(
            normalize_text
        )
    )

    income_mask = (
        descriptions_normalized
        .str.contains(
            "renda mensal informada",
            na=False,
        )
    )

    monthly_income = float(
        df.loc[
            income_mask,
            "amount",
        ].sum()
    )

    # Fallback para bases antigas
    if monthly_income <= 0:

        income_candidates = (
            df[
                (
                    df[
                        "type"
                    ]
                    == "entrada"
                )
                &
                (
                    df[
                        "category"
                    ]
                    .apply(
                        normalize_text
                    )
                    == "receita"
                )
            ]
        )

        monthly_income = float(
            income_candidates[
                "amount"
            ].sum()
        )

    # -----------------------------------------------------
    # COMPRAS / DESPESAS
    # -----------------------------------------------------

    expenses_df = (
        df[
            df[
                "type"
            ]
            == "saida"
        ]
        .copy()
    )

    purchases = float(
        expenses_df[
            "amount"
        ].sum()
    )

    # -----------------------------------------------------
    # DEVOLUÇÕES
    # -----------------------------------------------------

    category_normalized = (
        df[
            "category"
        ]
        .apply(
            normalize_text
        )
    )

    refund_mask = (
        category_normalized
        .isin(
            [
                "devolucoes",
                "devolucao",
                "estornos",
                "estorno",
            ]
        )
    )

    refunds = float(
        df.loc[
            refund_mask,
            "amount",
        ].sum()
    )

    net_expenses = max(
        purchases
        - refunds,
        0.0,
    )

    # -----------------------------------------------------
    # SALDO
    # -----------------------------------------------------

    balance = (
        monthly_income
        - net_expenses
    )

    reserve = (
        monthly_income
        * RESERVE_PERCENTAGE
    )

    safe_spend = max(
        balance
        - reserve,
        0.0,
    )

    # -----------------------------------------------------
    # MAIOR CATEGORIA
    # -----------------------------------------------------

    top_category = None
    top_category_value = 0.0

    if not expenses_df.empty:

        grouped = (
            expenses_df
            .groupby(
                "category"
            )[
                "amount"
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        if not grouped.empty:

            top_category = str(
                grouped.index[0]
            )

            top_category_value = float(
                grouped.iloc[0]
            )

    # -----------------------------------------------------
    # PERCENTUAL DA RENDA
    # -----------------------------------------------------

    expense_ratio = 0.0

    if monthly_income > 0:

        expense_ratio = (
            net_expenses
            / monthly_income
        ) * 100

    return {
        "monthly_income":
            monthly_income,

        "purchases":
            purchases,

        "refunds":
            refunds,

        "net_expenses":
            net_expenses,

        "balance":
            balance,

        "reserve":
            reserve,

        "safe_spend":
            safe_spend,

        "expense_ratio":
            expense_ratio,

        "top_category":
            top_category,

        "top_category_value":
            top_category_value,
    }


# =========================================================
# LOG DE FAST ROUTE
# =========================================================

def log_fast_tool(
    question,
    tool_name,
    extra=None,
):

    payload = {
        "prompt":
            question,

        "tool":
            tool_name,
    }

    if isinstance(
        extra,
        dict
    ):

        payload.update(
            extra
        )

    write_audit_event(
        event_type="fast_tool_call",
        status="success",
        extra=payload,
    )


# =========================================================
# FINALIZA E PASSA PELO OUTPUT GUARDRAIL
# =========================================================

def finalize_response(
    question,
    response,
):

    output_guardrail = (
        check_output_guardrail(
            response
        )
    )

    if not output_guardrail.get(
        "allowed",
        False
    ):

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
            output_guardrail.get(
                "message"
            )
            or
            "A resposta foi bloqueada "
            "pelas regras de segurança."
        )

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
        output_guardrail.get(
            "message"
        )
        or response
    )


# =========================================================
# MELHORAR SITUAÇÃO FINANCEIRA
# =========================================================

def build_financial_guidance(
    question,
    df,
):

    metrics = (
        get_local_metrics(
            df
        )
    )

    income = (
        metrics[
            "monthly_income"
        ]
    )

    purchases = (
        metrics[
            "purchases"
        ]
    )

    refunds = (
        metrics[
            "refunds"
        ]
    )

    net_expenses = (
        metrics[
            "net_expenses"
        ]
    )

    balance = (
        metrics[
            "balance"
        ]
    )

    safe_spend = (
        metrics[
            "safe_spend"
        ]
    )

    ratio = (
        metrics[
            "expense_ratio"
        ]
    )

    top_category = (
        metrics[
            "top_category"
        ]
    )

    top_value = (
        metrics[
            "top_category_value"
        ]
    )

    log_fast_tool(
        question,
        "financial_guidance",
    )

    lines = [
        "Com base nos dados atuais, eu focaria nestes pontos:",
        "",
    ]

    if income > 0:

        lines.append(
            f"**Renda mensal:** {format_brl(income)}"
        )

        lines.append(
            f"**Gasto líquido atual:** {format_brl(net_expenses)} "
            f"({ratio:.1f}% da sua renda)"
        )

    else:

        lines.append(
            f"**Gastos identificados:** {format_brl(net_expenses)}"
        )

    if refunds > 0:

        lines.append(
            f"**Devoluções/estornos:** {format_brl(refunds)}"
        )

    if (
        top_category
        and top_value > 0
    ):

        lines.append(
            f"**Maior categoria de gasto:** "
            f"{top_category} — {format_brl(top_value)}"
        )

    if income > 0:

        lines.append(
            f"**Saldo após os gastos:** {format_brl(balance)}"
        )

        lines.append(
            f"**Valor disponível após a reserva de 10%:** "
            f"{format_brl(safe_spend)}"
        )

    lines.extend(
        [
            "",
            "**Ações práticas:**",
        ]
    )

    # -----------------------------------------------------
    # RECOMENDAÇÕES DETERMINÍSTICAS
    # -----------------------------------------------------

    if (
        top_category
        and top_value > 0
        and income > 0
    ):

        category_ratio = (
            top_value
            / income
        ) * 100

        lines.append(
            f"1. Revise **{top_category}**, que sozinho representa "
            f"aproximadamente {category_ratio:.1f}% da sua renda mensal."
        )

    elif top_category:

        lines.append(
            f"1. Revise os gastos de **{top_category}**, "
            "que é atualmente sua maior categoria."
        )

    else:

        lines.append(
            "1. Continue registrando suas despesas para identificar "
            "quais categorias concentram mais gastos."
        )

    if income > 0:

        if ratio >= 90:

            lines.append(
                "2. Seus gastos estão consumindo quase toda a renda. "
                "Priorize despesas essenciais e reduza gastos adiáveis "
                "antes de assumir novas compras."
            )

        elif ratio >= 70:

            lines.append(
                "2. Uma parcela relevante da renda já está comprometida. "
                "Tente reduzir principalmente gastos variáveis e recorrentes."
            )

        elif ratio >= 50:

            lines.append(
                "2. Você ainda possui margem, mas vale definir limites "
                "por categoria para evitar aumento do comprometimento da renda."
            )

        else:

            lines.append(
                "2. Seu comprometimento atual está relativamente controlado. "
                "Use parte da margem para fortalecer sua reserva financeira."
            )

        lines.append(
            f"3. Preserve pelo menos a reserva configurada de "
            f"{format_brl(metrics['reserve'])} antes de aumentar gastos."
        )

    else:

        lines.append(
            "2. Informe sua renda mensal para eu calcular "
            "quanto seus gastos representam da sua renda."
        )

    if refunds > 0:

        lines.append(
            "4. Mantenha devoluções e estornos separados das compras, "
            "para não distorcer sua análise de consumo."
        )

    return "\n".join(
        lines
    )


# =========================================================
# FAST ROUTE
# =========================================================

def try_fast_route(
    question,
    df,
):

    normalized = normalize_text(
        question
    )

    metrics = (
        get_local_metrics(
            df
        )
    )

    # =====================================================
    # MELHORAR SITUAÇÃO FINANCEIRA
    # =====================================================

    guidance_terms = [
        "como melhorar minha situacao financeira",
        "como melhorar minhas financas",
        "como melhorar minha vida financeira",
        "como organizar minhas financas",
        "o que posso melhorar",
        "onde posso economizar",
        "como posso economizar",
        "me de dicas financeiras",
        "me dê dicas financeiras",
        "analise minha situacao financeira",
        "analisa minha situacao financeira",
    ]

    if any(
        term in normalized
        for term in guidance_terms
    ):

        return (
            build_financial_guidance(
                question,
                df,
            )
        )

    # =====================================================
    # MAIOR GASTO / MAIOR CATEGORIA
    # =====================================================

    top_terms = [
        "maior gasto",
        "mais gasto",
        "mais gastei",
        "gasto mais",
        "setor que eu mais gasto",
        "categoria que eu mais gasto",
        "onde gasto mais",
        "onde eu gasto mais",
    ]

    if any(
        term in normalized
        for term in top_terms
    ):

        category = (
            metrics[
                "top_category"
            ]
        )

        value = (
            metrics[
                "top_category_value"
            ]
        )

        log_fast_tool(
            question,
            "get_top_expense_category",
        )

        if not category:

            return (
                "Não encontrei despesas suficientes "
                "para identificar sua maior categoria."
            )

        return (
            f"O setor em que você mais gasta dinheiro é "
            f"**{category}**, com um total de "
            f"**{format_brl(value)}** em despesas."
        )

    # =====================================================
    # QUANTO POSSO GASTAR
    # =====================================================

    safe_terms = [
        "quanto posso gastar",
        "quanto eu posso gastar",
        "quanto posso gastar hoje",
        "limite seguro",
        "quanto sobra",
        "quanto tenho disponivel",
        "quanto tenho disponível",
        "sem comprometer minha reserva",
    ]

    if any(
        term in normalized
        for term in safe_terms
    ):

        log_fast_tool(
            question,
            "safe_spend",
        )

        if (
            metrics[
                "monthly_income"
            ]
            <= 0
        ):

            return (
                "Informe sua renda mensal para eu calcular "
                "quanto você pode gastar com segurança."
            )

        return (
            f"Considerando sua renda de "
            f"**{format_brl(metrics['monthly_income'])}**, "
            f"seus gastos líquidos de "
            f"**{format_brl(metrics['net_expenses'])}** "
            f"e uma reserva de 10%, você possui aproximadamente "
            f"**{format_brl(metrics['safe_spend'])}** "
            f"disponíveis para gastar sem comprometer essa reserva."
        )

    # =====================================================
    # SIMULAÇÃO DE COMPRA
    # =====================================================

    purchase_terms = [
        "posso gastar",
        "posso comprar",
        "se eu gastar",
        "se eu comprar",
        "comprar por",
        "gastar hoje",
    ]

    if any(
        term in normalized
        for term in purchase_terms
    ):

        amount = (
            extract_money_amount(
                question
            )
        )

        if amount is not None:

            log_fast_tool(
                question,
                "calculate_purchase_impact",
                {
                    "purchase_amount":
                        amount,
                },
            )

            current_balance = (
                metrics[
                    "balance"
                ]
            )

            safe_spend = (
                metrics[
                    "safe_spend"
                ]
            )

            after_purchase = (
                current_balance
                - amount
            )

            if (
                metrics[
                    "monthly_income"
                ]
                <= 0
            ):

                return (
                    "Informe sua renda mensal para eu analisar "
                    "o impacto dessa compra com segurança."
                )

            if safe_spend <= 0:

                risk = "ALTO"

            else:

                usage = (
                    amount
                    / safe_spend
                ) * 100

                if usage <= 50:

                    risk = "BAIXO"

                elif usage <= 80:

                    risk = "MODERADO"

                else:

                    risk = "ALTO"

            return (
                f"**Análise da compra de {format_brl(amount)}**\n\n"
                f"- Saldo atual: **{format_brl(current_balance)}**\n"
                f"- Limite seguro atual: **{format_brl(safe_spend)}**\n"
                f"- Saldo após a compra: **{format_brl(after_purchase)}**\n"
                f"- Nível de impacto: **{risk}**\n\n"
                f"Essa análise é uma simulação. "
                f"O FinPilot não executa a compra ou pagamento."
            )

    # =====================================================
    # RESUMO FINANCEIRO
    # =====================================================

    summary_terms = [
        "resumo financeiro",
        "resuma minhas financas",
        "resuma minha situacao",
        "como estou financeiramente",
        "minha situacao financeira",
        "visao geral",
        "visão geral",
    ]

    if any(
        term in normalized
        for term in summary_terms
    ):

        log_fast_tool(
            question,
            "get_financial_summary",
        )

        return (
            f"**Resumo financeiro atual**\n\n"
            f"- Renda mensal: **{format_brl(metrics['monthly_income'])}**\n"
            f"- Compras/despesas: **{format_brl(metrics['purchases'])}**\n"
            f"- Devoluções: **{format_brl(metrics['refunds'])}**\n"
            f"- Gasto líquido: **{format_brl(metrics['net_expenses'])}**\n"
            f"- Saldo: **{format_brl(metrics['balance'])}**\n"
            f"- Reserva de 10%: **{format_brl(metrics['reserve'])}**\n"
            f"- Disponível após reserva: **{format_brl(metrics['safe_spend'])}**"
        )

    # =====================================================
    # RECORRÊNCIAS
    # =====================================================

    recurring_terms = [
        "gastos recorrentes",
        "despesas recorrentes",
        "assinaturas",
        "o que pago todo mes",
        "o que pago todo mês",
    ]

    if any(
        term in normalized
        for term in recurring_terms
    ):

        try:

            recurring = (
                detect_recurring_expenses(
                    df
                )
            )

            log_fast_tool(
                question,
                "detect_recurring_expenses",
            )

            if not recurring:

                return (
                    "Não identifiquei gastos recorrentes "
                    "suficientes nos dados atuais."
                )

            lines = [
                "**Gastos recorrentes identificados:**",
                "",
            ]

            for item in recurring[:10]:

                description = (
                    item.get(
                        "description",
                        "Transação"
                    )
                )

                total = float(
                    item.get(
                        "total_amount",
                        0
                    )
                )

                occurrences = (
                    item.get(
                        "occurrences",
                        0
                    )
                )

                lines.append(
                    f"- **{description}** — "
                    f"{format_brl(total)} "
                    f"em {occurrences} ocorrência(s)"
                )

            return "\n".join(
                lines
            )

        except Exception:

            return None

    # =====================================================
    # ANOMALIAS
    # =====================================================

    anomaly_terms = [
        "gasto fora do padrao",
        "gasto fora do padrão",
        "gastos fora do padrao",
        "gastos fora do padrão",
        "anomalias",
        "gasto estranho",
        "gastos estranhos",
    ]

    if any(
        term in normalized
        for term in anomaly_terms
    ):

        try:

            anomalies = (
                detect_spending_anomalies(
                    df
                )
            )

            log_fast_tool(
                question,
                "detect_spending_anomalies",
            )

            if not anomalies:

                return (
                    "Não identifiquei gastos fora do padrão "
                    "nos dados atuais."
                )

            lines = [
                "**Gastos fora do padrão identificados:**",
                "",
            ]

            for item in anomalies[:10]:

                lines.append(
                    f"- **{item.get('description', 'Transação')}** — "
                    f"{format_brl(item.get('amount', 0))}"
                )

            return "\n".join(
                lines
            )

        except Exception:

            return None

    # =====================================================
    # FORECAST
    # =====================================================

    forecast_terms = [
        "forecast",
        "projecao",
        "projeção",
        "fim do mes",
        "fim do mês",
        "saldo projetado",
    ]

    if any(
        term in normalized
        for term in forecast_terms
    ):

        try:

            forecast = (
                forecast_month_end_balance(
                    df
                )
            )

            log_fast_tool(
                question,
                "forecast_month_end_balance",
            )

            if not forecast:

                return (
                    "Não há dados suficientes para calcular "
                    "uma projeção de fim de mês."
                )

            return (
                f"**Projeção financeira**\n\n"
                f"- Saldo atual: "
                f"**{format_brl(forecast.get('current_balance', 0))}**\n"
                f"- Média diária de despesas: "
                f"**{format_brl(forecast.get('average_daily_expense', 0))}**\n"
                f"- Saldo projetado no fim do mês: "
                f"**{format_brl(forecast.get('projected_month_end_balance', 0))}**"
            )

        except Exception:

            return None

    return None


# =========================================================
# AGENTE PRINCIPAL
# =========================================================

def run_financial_agent(
    question: str,
    df
) -> str:

    # =====================================================
    # VALIDAÇÃO
    # =====================================================

    if not question:

        return (
            "Digite uma pergunta para que eu possa "
            "analisar sua situação financeira."
        )

    question = (
        str(question)
        .strip()
    )

    # =====================================================
    # INPUT GUARDRAIL
    # =====================================================

    input_guardrail = (
        check_input_guardrail(
            question
        )
    )

    # -----------------------------------------------------
    # BLOQUEADO
    # -----------------------------------------------------

    if not input_guardrail.get(
        "allowed",
        False
    ):

        write_audit_event(
            event_type="input_guardrail",
            status="blocked",
            input_guardrail=input_guardrail,
            extra={
                "prompt":
                    question,
            },
        )

        return (
            input_guardrail.get(
                "message"
            )
            or
            "Essa solicitação foi bloqueada "
            "pelas regras de segurança do FinPilot."
        )

    # -----------------------------------------------------
    # PERMITIDO
    # -----------------------------------------------------

    write_audit_event(
        event_type="input_guardrail",
        status="allowed",
        input_guardrail=input_guardrail,
        extra={
            "prompt":
                question,
        },
    )

    # =====================================================
    # FAST ROUTE
    # =====================================================

    try:

        fast_response = (
            try_fast_route(
                question,
                df,
            )
        )

        if fast_response:

            return (
                finalize_response(
                    question,
                    fast_response,
                )
            )

    except Exception as fast_error:

        write_audit_event(
            event_type="agent_error",
            status="error",
            extra={
                "prompt":
                    question,

                "stage":
                    "fast_route",

                "error":
                    str(
                        fast_error
                    ),
            },
        )

    # =====================================================
    # FERRAMENTAS PARA O GEMINI
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
    # GEMINI FALLBACK
    # =====================================================

    try:

        response = (
            run_gemini_agent(
                message=question,
                tools=tools,
            )
        )

        return (
            finalize_response(
                question,
                response,
            )
        )

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

                "stage":
                    "gemini",

                "error":
                    error_text,
            },
        )

        # =================================================
        # QUOTA / LIMITE
        # =================================================

        if (
            "429"
            in error_text

            or "resource_exhausted"
            in error_text.lower()

            or "quota"
            in error_text.lower()
        ):

            return (
                "A IA generativa atingiu temporariamente "
                "o limite de uso da API. "
                "As análises financeiras principais do "
                "FinPilot continuam funcionando normalmente."
            )

        # =================================================
        # AUTENTICAÇÃO
        # =================================================

        if (
            "api key"
            in error_text.lower()

            or "api_key"
            in error_text.lower()

            or "401"
            in error_text

            or "403"
            in error_text
        ):

            return (
                "A camada de IA generativa está temporariamente "
                "indisponível por uma configuração da API. "
                "As ferramentas financeiras locais continuam ativas."
            )

        # =================================================
        # MODELO
        # =================================================

        if (
            "404"
            in error_text

            or "model"
            in error_text.lower()
        ):

            return (
                "A camada generativa não conseguiu acessar "
                "o modelo configurado. "
                "As análises financeiras determinísticas "
                "continuam disponíveis."
            )

        return (
            "Não consegui usar a camada generativa nesta consulta, "
            "mas você pode perguntar sobre seus gastos, maior categoria, "
            "quanto pode gastar, recorrências, forecast, anomalias "
            "ou como melhorar sua situação financeira."
        )