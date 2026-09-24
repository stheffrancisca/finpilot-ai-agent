import streamlit as st
import altair as alt
import pandas as pd

from app.agents.financial_agent import (
    run_financial_agent,
)

from app.services.audit import (
    read_audit_log,
)

from app.services.csv_adapter import (
    read_csv_flexible,
    normalize_bank_dataframe,
)

from app.services.pdf_adapter import (
    read_pdf_flexible,
)

from app.tools.financial_metrics import (
    expenses_by_category,
)

from app.tools.financial_tools import (
    detect_spending_anomalies,
    detect_recurring_expenses,
    forecast_month_end_balance,
)


# =========================================================
# CONFIG
# =========================================================

DEFAULT_FILEPATH = (
    "data/sample_transactions.csv"
)

RESERVE_PERCENTAGE = 0.10


st.set_page_config(
    page_title="FinPilot AI",
    page_icon="💰",
    layout="wide",
)


# =========================================================
# AUXILIARES
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


def validate_dataframe(df):

    required = {
        "date",
        "description",
        "category",
        "type",
        "amount",
    }

    missing = (
        required
        - set(
            df.columns
        )
    )

    if missing:

        return (
            False,
            "Colunas ausentes: "
            + ", ".join(
                sorted(
                    missing
                )
            ),
        )

    if df.empty:

        return (
            False,
            "O arquivo não possui transações válidas.",
        )

    return (
        True,
        None,
    )


# =========================================================
# AUDITORIA
# =========================================================

REASON_LABELS = {

    "financial_action":
        "Tentativa de executar transação financeira",

    "prompt_injection":
        "Tentativa de alterar as regras do agente",

    "sensitive_inference":
        "Tentativa de inferir informação sensível",

    "unsafe_output":
        "Resposta potencialmente insegura",

    "outro":
        "Outro comportamento bloqueado",
}


EVENT_LABELS = {

    "input_guardrail":
        "Verificação da pergunta",

    "output_guardrail":
        "Verificação da resposta",

    "tool_call":
        "Ferramenta executada",

    "fast_tool_call":
        "Ferramenta executada",

    "agent_error":
        "Falha do agente",
}


STATUS_LABELS = {

    "allowed":
        "Permitido",

    "blocked":
        "Bloqueado",

    "success":
        "Sucesso",

    "error":
        "Erro",
}


# =========================================================
# ADMIN
# =========================================================

def render_admin_panel():

    st.title(
        "Admin"
    )

    st.caption(
        "Segurança, auditoria e monitoramento "
        "do FinPilot AI."
    )

    st.divider()

    events = (
        read_audit_log()
    )

    if not events:

        st.info(
            "Nenhum evento registrado."
        )

        return

    blocked = sum(
        1
        for event in events
        if event.get(
            "status"
        ) == "blocked"
    )

    errors = sum(
        1
        for event in events
        if event.get(
            "status"
        ) == "error"
    )

    tools = sum(
        1
        for event in events
        if event.get(
            "event_type"
        )
        in [
            "tool_call",
            "fast_tool_call",
        ]
    )

    a1, a2, a3, a4 = (
        st.columns(4)
    )

    a1.metric(
        "Interações monitoradas",
        len(
            events
        )
    )

    a2.metric(
        "Ameaças bloqueadas",
        blocked
    )

    a3.metric(
        "Ferramentas acionadas",
        tools
    )

    a4.metric(
        "Falhas",
        errors
    )

    st.divider()

    st.subheader(
        "Últimos eventos de segurança"
    )

    rows = []

    for event in reversed(
        events[-20:]
    ):

        extra = (
            event.get(
                "extra",
                {}
            )
        )

        prompt_text = ""

        if isinstance(
            extra,
            dict
        ):

            prompt_text = (
                extra.get(
                    "prompt"
                )
                or ""
            )

        input_guardrail = (
            event.get(
                "input_guardrail"
            )
        )

        output_guardrail = (
            event.get(
                "output_guardrail"
            )
        )

        reason = ""

        if isinstance(
            input_guardrail,
            dict
        ):

            reason = (
                input_guardrail.get(
                    "reason"
                )
                or ""
            )

        elif isinstance(
            output_guardrail,
            dict
        ):

            reason = (
                output_guardrail.get(
                    "reason"
                )
                or ""
            )

        timestamp = (
            event.get(
                "timestamp",
                ""
            )
        )

        try:

            timestamp = (
                pd.to_datetime(
                    timestamp
                )
                .strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )

        except Exception:

            pass

        event_code = (
            event.get(
                "event_type",
                ""
            )
        )

        status_code = (
            event.get(
                "status",
                ""
            )
        )

        rows.append(
            {
                "Horário":
                    timestamp,

                "Evento":
                    EVENT_LABELS.get(
                        event_code,
                        event_code
                    ),

                "Status":
                    STATUS_LABELS.get(
                        status_code,
                        status_code
                    ),

                "Prompt do usuário":
                    prompt_text,

                "Motivo do bloqueio":
                    REASON_LABELS.get(
                        reason,
                        reason
                    )
                    if reason
                    else "",
            }
        )

    st.dataframe(
        pd.DataFrame(
            rows
        ),
        use_container_width=True,
        hide_index=True,
        height=430,
    )

    st.divider()

    st.subheader(
        "Status das proteções"
    )

    s1, s2, s3 = (
        st.columns(3)
    )

    s1.success(
        "Input Guardrail\n\nAtivo"
    )

    s2.success(
        "Output Guardrail\n\nAtivo"
    )

    s3.success(
        "Audit Log\n\nAtivo"
    )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title(
        "FinPilot AI"
    )

    st.caption(
        "Análise financeira com IA "
        "e ferramentas determinísticas."
    )

    st.divider()

    st.subheader(
        "Minha renda"
    )

    monthly_income = (
        st.number_input(
            "Renda mensal",
            min_value=0.0,
            step=100.0,
            format="%.2f",
        )
    )

    st.caption(
        "Usada para calcular saldo, "
        "reserva e limite seguro."
    )

    st.divider()

    st.subheader(
        "Fonte de dados"
    )

    data_source = (
        st.radio(
            "Escolha os dados:",
            [
                "Usar extrato fictício",
                "Enviar arquivo",
            ],
        )
    )

    uploaded_file = None

    if (
        data_source
        == "Enviar arquivo"
    ):

        uploaded_file = (
            st.file_uploader(
                "Envie seu extrato",
                type=[
                    "csv",
                    "pdf",
                    "xlsx",
                ],
            )
        )

        st.caption(
            "Formatos aceitos: CSV, PDF e XLSX."
        )

    st.divider()

    st.subheader(
        "Navegação"
    )

    if (
        "current_page"
        not in st.session_state
    ):

        st.session_state.current_page = (
            "dashboard"
        )

    if st.button(
        "Dashboard",
        use_container_width=True,
    ):

        st.session_state.current_page = (
            "dashboard"
        )

        st.rerun()

    if st.button(
        "Admin",
        use_container_width=True,
    ):

        st.session_state.current_page = (
            "admin"
        )

        st.rerun()

    st.divider()

    if st.button(
        "Limpar conversa",
        use_container_width=True,
    ):

        st.session_state.messages = []

        st.rerun()


# =========================================================
# ADMIN ROUTE
# =========================================================

if (
    st.session_state.get(
        "current_page",
        "dashboard"
    )
    == "admin"
):

    render_admin_panel()

    st.stop()


# =========================================================
# CARREGAMENTO
# =========================================================

file_report = {}

is_credit_card_pdf = False


if (
    data_source
    == "Enviar arquivo"
    and uploaded_file
    is not None
):

    filename = (
        uploaded_file.name
        .lower()
    )

    try:

        # -------------------------------------------------
        # CSV
        # -------------------------------------------------

        if filename.endswith(
            ".csv"
        ):

            raw_df, _ = (
                read_csv_flexible(
                    uploaded_file
                )
            )

            df, file_report = (
                normalize_bank_dataframe(
                    raw_df
                )
            )

        # -------------------------------------------------
        # EXCEL
        # -------------------------------------------------

        elif filename.endswith(
            ".xlsx"
        ):

            raw_df = pd.read_excel(
                uploaded_file,
                engine="openpyxl",
            )

            df, file_report = (
                normalize_bank_dataframe(
                    raw_df
                )
            )

        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        elif filename.endswith(
            ".pdf"
        ):

            df, file_report = (
                read_pdf_flexible(
                    uploaded_file
                )
            )

            is_credit_card_pdf = (
                file_report.get(
                    "source_type"
                )
                == "credit_card_pdf"
            )

        else:

            st.error(
                "Formato não suportado."
            )

            st.stop()

    except Exception as error:

        st.error(
            "Não foi possível interpretar "
            "esse arquivo."
        )

        st.warning(
            str(
                error
            )
        )

        st.stop()


else:

    df = pd.read_csv(
        DEFAULT_FILEPATH
    )


# =========================================================
# VALIDAÇÃO
# =========================================================

is_valid, validation_error = (
    validate_dataframe(
        df
    )
)

if not is_valid:

    st.error(
        validation_error
    )

    st.stop()


# =========================================================
# NORMALIZAÇÃO
# =========================================================

df = df.copy()

df["date"] = pd.to_datetime(
    df["date"],
    errors="coerce",
)

df["amount"] = pd.to_numeric(
    df["amount"],
    errors="coerce",
)

df["type"] = (
    df["type"]
    .astype(str)
    .str.lower()
    .str.strip()
)

df["category"] = (
    df["category"]
    .astype(str)
    .str.strip()
)

df["description"] = (
    df["description"]
    .astype(str)
    .str.strip()
)

df = (
    df.dropna(
        subset=[
            "date",
            "amount",
        ]
    )
)


# =========================================================
# TIPOS ESPECIAIS DO PDF
# =========================================================

if (
    "movement_kind"
    not in df.columns
):

    df[
        "movement_kind"
    ] = ""

    df.loc[
        df["type"] == "saida",
        "movement_kind",
    ] = "compra"

    df.loc[
        df["type"] == "entrada",
        "movement_kind",
    ] = "credito"


# =========================================================
# SEPARA MOVIMENTAÇÕES
# =========================================================

purchase_df = (
    df[
        df[
            "movement_kind"
        ]
        == "compra"
    ]
    .copy()
)


refund_df = (
    df[
        df[
            "movement_kind"
        ]
        == "devolucao"
    ]
    .copy()
)


payment_df = (
    df[
        df[
            "movement_kind"
        ]
        == "pagamento_fatura"
    ]
    .copy()
)


other_credit_df = (
    df[
        df[
            "movement_kind"
        ]
        == "credito"
    ]
    .copy()
)


# =========================================================
# VALORES
# =========================================================

purchases = float(
    purchase_df[
        "amount"
    ].sum()
)


refunds = float(
    refund_df[
        "amount"
    ].sum()
)


payments = float(
    payment_df[
        "amount"
    ].sum()
)


other_credits = float(
    other_credit_df[
        "amount"
    ].sum()
)


# =========================================================
# TOTAL LÍQUIDO
# =========================================================

net_expenses = max(
    purchases
    - refunds,
    0.0,
)


# =========================================================
# PARA CSV / XLSX ANTIGOS
# =========================================================

if not is_credit_card_pdf:

    regular_expenses = (
        df[
            df["type"]
            == "saida"
        ]
    )

    purchases = float(
        regular_expenses[
            "amount"
        ].sum()
    )

    net_expenses = (
        purchases
    )


# =========================================================
# RENDA E SALDO
# =========================================================

income = float(
    monthly_income
)


balance = (
    income
    - net_expenses
)


reserve = (
    income
    * RESERVE_PERCENTAGE
)


safe_spend = max(
    balance
    - reserve,
    0.0,
)


# =========================================================
# DATAFRAME FINANCEIRO PARA O AGENTE
# =========================================================

analysis_expenses = (
    purchase_df.copy()
)


# DEVOLUÇÕES REDUZEM O GASTO
# mas não são renda mensal.
for _, refund in (
    refund_df.iterrows()
):

    refund_row = (
        refund.to_dict()
    )

    refund_row[
        "type"
    ] = "entrada"

    analysis_expenses = pd.concat(
        [
            analysis_expenses,
            pd.DataFrame(
                [
                    refund_row
                ]
            ),
        ],
        ignore_index=True,
    )


analysis_df = (
    analysis_expenses.copy()
)


if monthly_income > 0:

    reference_date = (
        df["date"].min()
        if not df.empty
        else pd.Timestamp.today()
    )

    income_row = pd.DataFrame(
        [
            {
                "date":
                    reference_date,

                "description":
                    "Renda mensal informada",

                "category":
                    "Receita",

                "type":
                    "entrada",

                "amount":
                    monthly_income,

                "movement_kind":
                    "renda",
            }
        ]
    )

    analysis_df = pd.concat(
        [
            analysis_df,
            income_row,
        ],
        ignore_index=True,
    )


# =========================================================
# DATA PARA VISUALIZAÇÕES
# =========================================================

visualization_df = (
    purchase_df[
        [
            "date",
            "description",
            "category",
            "amount",
        ]
    ]
    .copy()
)


# =========================================================
# INCLUI DEVOLUÇÕES NA VISUALIZAÇÃO
# =========================================================

if not refund_df.empty:

    refund_visual = (
        refund_df[
            [
                "date",
                "description",
                "amount",
            ]
        ]
        .copy()
    )

    refund_visual[
        "category"
    ] = "Devoluções"

    visualization_df = pd.concat(
        [
            visualization_df,
            refund_visual,
        ],
        ignore_index=True,
    )


# =========================================================
# CATEGORY DATA
# =========================================================

if not visualization_df.empty:

    category_data = (
        visualization_df
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

else:

    category_data = (
        pd.Series(
            dtype=float
        )
    )


# =========================================================
# INSIGHTS
# =========================================================

recurring_expenses = (
    detect_recurring_expenses(
        purchase_df
    )
)


anomalies = (
    detect_spending_anomalies(
        purchase_df
    )
)


forecast = None

if monthly_income > 0:

    forecast = (
        forecast_month_end_balance(
            analysis_df
        )
    )


# =========================================================
# DASHBOARD
# =========================================================

st.title(
    "FinPilot AI"
)

st.caption(
    "Seu copiloto inteligente "
    "para decisões financeiras"
)


if monthly_income <= 0:

    st.info(
        "Informe sua renda mensal na barra lateral "
        "para obter uma análise completa."
    )


st.divider()


# =========================================================
# KPIs
# =========================================================

if is_credit_card_pdf:

    k1, k2, k3, k4, k5 = (
        st.columns(5)
    )

    with k1:

        st.metric(
            "Renda mensal",
            format_brl(
                income
            )
        )

    with k2:

        st.metric(
            "Compras identificadas",
            format_brl(
                purchases
            )
        )

    with k3:

        st.metric(
            "Devoluções",
            format_brl(
                refunds
            )
        )

    with k4:

        st.metric(
            "Total líquido",
            format_brl(
                net_expenses
            )
        )

    with k5:

        st.metric(
            "Limite seguro",
            format_brl(
                safe_spend
            )
        )


    if payments > 0:

        st.caption(
            f"Pagamento da fatura anterior identificado: "
            f"{format_brl(payments)}. "
            "Esse valor não foi considerado como renda "
            "nem como devolução."
        )


else:

    k1, k2, k3, k4 = (
        st.columns(4)
    )

    k1.metric(
        "Renda mensal",
        format_brl(
            income
        )
    )

    k2.metric(
        "Despesas identificadas",
        format_brl(
            net_expenses
        )
    )

    k3.metric(
        "Saldo disponível",
        format_brl(
            balance
        )
    )

    k4.metric(
        "Limite seguro",
        format_brl(
            safe_spend
        )
    )


st.divider()


# =========================================================
# VISÃO DAS DESPESAS
# =========================================================

st.subheader(
    "Visão das despesas"
)

st.caption(
    "Clique em uma categoria para visualizar "
    "as movimentações classificadas nela."
)


if not category_data.empty:

    if (
        "category_chart_version"
        not in st.session_state
    ):

        st.session_state.category_chart_version = 0


    category_df = (
        category_data
        .reset_index()
    )

    category_df.columns = [
        "Categoria",
        "Valor",
    ]


    category_df[
        "ValorFormatado"
    ] = (
        category_df[
            "Valor"
        ]
        .apply(
            format_brl
        )
    )


    category_df = (
        category_df
        .sort_values(
            "Valor",
            ascending=False,
        )
    )


    max_value = float(
        category_df[
            "Valor"
        ].max()
    )


    chart_max = max(
        max_value
        * 1.35,
        1,
    )


    category_selection = (
        alt.selection_point(
            name="categoria_select",
            fields=[
                "Categoria"
            ],
            on="click",
            clear="dblclick",
        )
    )


    bars = (
        alt.Chart(
            category_df
        )
        .mark_bar(
            cornerRadiusEnd=6,
            size=30,
        )
        .encode(

            x=alt.X(
                "Valor:Q",
                axis=None,

                scale=alt.Scale(
                    domain=[
                        0,
                        chart_max,
                    ]
                ),
            ),

            y=alt.Y(
                "Categoria:N",
                sort="-x",
                title=None,
            ),

            opacity=alt.condition(
                category_selection,
                alt.value(1),
                alt.value(0.50),
            ),

            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                ),

                alt.Tooltip(
                    "Valor:Q",
                    format=",.2f",
                ),
            ],
        )
        .add_params(
            category_selection
        )
    )


    labels = (
        alt.Chart(
            category_df
        )
        .mark_text(
            align="left",
            baseline="middle",
            dx=8,
            fontWeight="bold",
        )
        .encode(

            x=alt.X(
                "Valor:Q",

                scale=alt.Scale(
                    domain=[
                        0,
                        chart_max,
                    ]
                ),
            ),

            y=alt.Y(
                "Categoria:N",
                sort="-x",
            ),

            text="ValorFormatado:N",
        )
    )


    left, right = (
        st.columns(
            [
                1.2,
                1,
            ]
        )
    )


    with left:

        st.markdown(
            "#### Movimentações por categoria"
        )

        chart_event = (
            st.altair_chart(
                (
                    bars
                    + labels
                ).properties(
                    height=max(
                        260,
                        len(
                            category_df
                        ) * 50
                    )
                ),
                use_container_width=True,
                key=(
                    "category_chart_"
                    + str(
                        st.session_state.category_chart_version
                    )
                ),
                on_select="rerun",
                selection_mode=[
                    "categoria_select"
                ],
            )
        )


    # =====================================================
    # SELEÇÃO
    # =====================================================

    selected_category = None


    try:

        state = getattr(
            chart_event,
            "selection",
            {},
        )

        result = state.get(
            "categoria_select",
            [],
        )

        if (
            isinstance(
                result,
                list
            )
            and result
        ):

            selected_category = (
                result[0].get(
                    "Categoria"
                )
            )

        elif isinstance(
            result,
            dict
        ):

            value = result.get(
                "Categoria"
            )

            if isinstance(
                value,
                list
            ):

                if value:

                    selected_category = (
                        value[0]
                    )

            else:

                selected_category = (
                    value
                )

    except Exception:

        selected_category = None


    with right:

        if selected_category:

            t1, t2 = (
                st.columns(
                    [
                        2.5,
                        1.3,
                    ]
                )
            )

            t1.markdown(
                f"#### {selected_category}"
            )

            with t2:

                if st.button(
                    "Limpar seleção",
                    use_container_width=True,
                ):

                    st.session_state.category_chart_version += 1

                    st.rerun()


            selected_df = (
                visualization_df[
                    visualization_df[
                        "category"
                    ]
                    == selected_category
                ]
                .copy()
            )


            detail = (
                selected_df
                .groupby(
                    "description",
                    as_index=False,
                )
                .agg(
                    Valor=(
                        "amount",
                        "sum",
                    ),
                    Quantidade=(
                        "amount",
                        "count",
                    ),
                )
                .sort_values(
                    "Valor",
                    ascending=False,
                )
            )


            detail[
                "ValorFormatado"
            ] = (
                detail[
                    "Valor"
                ]
                .apply(
                    format_brl
                )
            )


            max_detail = max(
                float(
                    detail[
                        "Valor"
                    ].max()
                )
                * 1.4,
                1,
            )


            detail_bars = (
                alt.Chart(
                    detail
                )
                .mark_bar(
                    cornerRadiusEnd=6,
                    size=26,
                )
                .encode(

                    x=alt.X(
                        "Valor:Q",
                        axis=None,

                        scale=alt.Scale(
                            domain=[
                                0,
                                max_detail,
                            ]
                        ),
                    ),

                    y=alt.Y(
                        "description:N",
                        title=None,
                        sort="-x",
                    ),

                    tooltip=[
                        "description:N",
                        "Valor:Q",
                        "Quantidade:Q",
                    ],
                )
            )


            detail_labels = (
                alt.Chart(
                    detail
                )
                .mark_text(
                    align="left",
                    baseline="middle",
                    dx=8,
                    fontWeight="bold",
                )
                .encode(

                    x=alt.X(
                        "Valor:Q",

                        scale=alt.Scale(
                            domain=[
                                0,
                                max_detail,
                            ]
                        ),
                    ),

                    y=alt.Y(
                        "description:N",
                        sort="-x",
                    ),

                    text="ValorFormatado:N",
                )
            )


            st.altair_chart(
                (
                    detail_bars
                    + detail_labels
                ).properties(
                    height=max(
                        220,
                        len(
                            detail
                        ) * 48,
                    )
                ),
                use_container_width=True,
            )


        else:

            st.markdown(
                "#### Participação nas movimentações"
            )

            donut = (
                alt.Chart(
                    category_df
                )
                .mark_arc(
                    innerRadius=65
                )
                .encode(

                    theta="Valor:Q",

                    color=alt.Color(
                        "Categoria:N",
                        title=None,
                    ),

                    tooltip=[
                        "Categoria:N",
                        "Valor:Q",
                    ],
                )
                .properties(
                    height=280
                )
            )

            st.altair_chart(
                donut,
                use_container_width=True,
            )


    # =====================================================
    # DETALHAMENTO
    # =====================================================

    if selected_category:

        st.divider()

        st.subheader(
            f"Detalhes de {selected_category}"
        )

        selected_df = (
            visualization_df[
                visualization_df[
                    "category"
                ]
                == selected_category
            ]
            .copy()
        )


        total = float(
            selected_df[
                "amount"
            ].sum()
        )


        count = len(
            selected_df
        )


        average = (
            total / count
            if count
            else 0
        )


        d1, d2, d3 = (
            st.columns(3)
        )

        d1.metric(
            "Total",
            format_brl(
                total
            )
        )

        d2.metric(
            "Movimentações",
            count
        )

        d3.metric(
            "Ticket médio",
            format_brl(
                average
            )
        )


        details = (
            selected_df[
                [
                    "date",
                    "description",
                    "amount",
                ]
            ]
            .copy()
            .sort_values(
                "date",
                ascending=False,
            )
        )


        details[
            "date"
        ] = (
            details[
                "date"
            ]
            .dt.strftime(
                "%d/%m/%Y"
            )
        )


        details[
            "amount"
        ] = (
            details[
                "amount"
            ]
            .apply(
                format_brl
            )
        )


        details = (
            details.rename(
                columns={
                    "date":
                        "Data",

                    "description":
                        "Descrição",

                    "amount":
                        "Valor",
                }
            )
        )


        st.dataframe(
            details,
            use_container_width=True,
            hide_index=True,
        )


else:

    st.info(
        "Nenhuma movimentação identificada."
    )


st.divider()


# =========================================================
# PLANEJAMENTO
# =========================================================

st.subheader(
    "Planejamento financeiro"
)


p1, p2, p3 = (
    st.columns(3)
)


p1.metric(
    "Reserva recomendada",
    format_brl(
        reserve
    )
)


p2.metric(
    "Saldo após gastos líquidos",
    format_brl(
        balance
    )
)


p3.metric(
    "Disponível após reserva",
    format_brl(
        safe_spend
    )
)


st.divider()


# =========================================================
# INSIGHTS
# =========================================================

st.subheader(
    "Insights Financeiros"
)


tab1, tab2, tab3 = (
    st.tabs(
        [
            "Gastos recorrentes",
            "Forecast",
            "Anomalias",
        ]
    )
)


with tab1:

    if recurring_expenses:

        for item in recurring_expenses:

            st.write(
                f"**{item['description']}** — "
                f"{format_brl(item['total_amount'])}"
            )

    else:

        st.info(
            "Nenhum gasto recorrente identificado."
        )


with tab2:

    if forecast is None:

        st.info(
            "Informe sua renda mensal "
            "para visualizar o forecast."
        )

    else:

        f1, f2, f3 = (
            st.columns(3)
        )

        f1.metric(
            "Saldo atual",
            format_brl(
                forecast[
                    "current_balance"
                ]
            )
        )

        f2.metric(
            "Média diária",
            format_brl(
                forecast[
                    "average_daily_expense"
                ]
            )
        )

        f3.metric(
            "Saldo projetado",
            format_brl(
                forecast[
                    "projected_month_end_balance"
                ]
            )
        )


with tab3:

    if anomalies:

        for item in anomalies:

            st.warning(
                f"{item['description']} — "
                f"{format_brl(item['amount'])}"
            )

    else:

        st.success(
            "Nenhum gasto fora do padrão identificado."
        )


st.divider()


# =========================================================
# CHAT
# =========================================================

st.subheader(
    "FinPilot AI Assistant"
)


st.write(
    "Pergunte sobre sua situação financeira, "
    "seus gastos ou simule uma decisão."
)


if (
    "messages"
    not in st.session_state
):

    st.session_state.messages = []


for message in (
    st.session_state.messages
):

    with st.chat_message(
        message[
            "role"
        ]
    ):

        st.markdown(
            message[
                "content"
            ]
        )


user_question = (
    st.chat_input(
        "Ex.: Posso gastar R$ 700 hoje?"
    )
)


if user_question:

    if monthly_income <= 0:

        st.warning(
            "Informe sua renda mensal "
            "antes de consultar o FinPilot."
        )

    else:

        st.session_state.messages.append(
            {
                "role":
                    "user",

                "content":
                    user_question,
            }
        )

        with st.chat_message(
            "user"
        ):

            st.markdown(
                user_question
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "Analisando sua situação financeira..."
            ):

                try:

                    response = (
                        run_financial_agent(
                            user_question,
                            analysis_df,
                        )
                    )

                    st.markdown(
                        response
                    )

                    st.session_state.messages.append(
                        {
                            "role":
                                "assistant",

                            "content":
                                response,
                        }
                    )

                except Exception as error:

                    st.error(
                        "Não foi possível concluir "
                        "a análise agora."
                    )

                    print(
                        "Erro:",
                        error
                    )