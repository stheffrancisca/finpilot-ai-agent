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

from app.tools.financial_metrics import (
    expenses_by_category,
)

from app.tools.financial_tools import (
    detect_spending_anomalies,
    detect_recurring_expenses,
    forecast_month_end_balance,
)


# =========================================================
# CONFIGURAÇÕES
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
# FUNÇÕES AUXILIARES
# =========================================================

def format_brl(value):

    value = float(
        value
    )

    formatted = (
        f"{value:,.2f}"
    )

    formatted = (
        formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return (
        f"R$ {formatted}"
    )


def validate_dataframe(df):

    required_columns = {
        "date",
        "description",
        "category",
        "type",
        "amount",
    }

    missing_columns = (
        required_columns
        - set(
            df.columns
        )
    )

    if missing_columns:

        return (
            False,
            (
                "Ainda faltam as colunas: "
                + ", ".join(
                    sorted(
                        missing_columns
                    )
                )
            ),
        )

    if df.empty:

        return (
            False,
            "O arquivo não possui transações válidas.",
        )

    unresolved = (
        df["type"]
        .isna()
        .sum()
    )

    if unresolved > 0:

        return (
            False,
            (
                f"{unresolved} transação(ões) "
                "não possuem tipo identificado."
            ),
        )

    valid_types = {
        "entrada",
        "saida",
    }

    invalid_types = (
        set(
            df["type"]
            .dropna()
            .astype(str)
            .str.lower()
        )
        - valid_types
    )

    if invalid_types:

        return (
            False,
            (
                "Existem tipos não reconhecidos: "
                + ", ".join(
                    sorted(
                        invalid_types
                    )
                )
            ),
        )

    return (
        True,
        None,
    )


# =========================================================
# LABELS DE AUDITORIA
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

    "agent_response":
        "Resposta do agente",

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

    audit_events = (
        read_audit_log()
    )

    if not audit_events:

        st.info(
            "Nenhum evento de auditoria "
            "foi registrado ainda."
        )

        return

    # =====================================================
    # MÉTRICAS
    # =====================================================

    total_events = len(
        audit_events
    )

    blocked_events = sum(
        1
        for event in audit_events
        if event.get(
            "status"
        ) == "blocked"
    )

    error_events = sum(
        1
        for event in audit_events
        if event.get(
            "status"
        ) == "error"
    )

    tool_calls = sum(
        1
        for event in audit_events
        if event.get(
            "event_type"
        )
        in (
            "tool_call",
            "fast_tool_call",
        )
    )


    col1, col2, col3, col4 = (
        st.columns(4)
    )


    with col1:

        st.metric(
            "Interações monitoradas",
            total_events
        )


    with col2:

        st.metric(
            "Ameaças bloqueadas",
            blocked_events
        )


    with col3:

        st.metric(
            "Ferramentas acionadas",
            tool_calls
        )


    with col4:

        st.metric(
            "Falhas",
            error_events
        )


    st.divider()

    # =====================================================
    # EVENTOS
    # =====================================================

    st.subheader(
        "Últimos eventos de segurança"
    )

    st.caption(
        "Veja o prompt enviado pelo usuário, "
        "a decisão do guardrail e o motivo."
    )


    last_events = list(
        reversed(
            audit_events[-20:]
        )
    )


    audit_rows = []


    for event in last_events:

        # -------------------------------------------------
        # PROMPT
        # -------------------------------------------------

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
                or extra.get(
                    "question"
                )
                or extra.get(
                    "message"
                )
                or ""
            )


        if not prompt_text:

            prompt_text = (
                event.get(
                    "prompt"
                )
                or event.get(
                    "question"
                )
                or event.get(
                    "message"
                )
                or ""
            )


        # -------------------------------------------------
        # MOTIVO
        # -------------------------------------------------

        reason_code = ""


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


        if isinstance(
            input_guardrail,
            dict
        ):

            reason_code = (
                input_guardrail.get(
                    "reason"
                )
                or ""
            )


        elif isinstance(
            output_guardrail,
            dict
        ):

            reason_code = (
                output_guardrail.get(
                    "reason"
                )
                or ""
            )


        friendly_reason = (
            REASON_LABELS.get(
                reason_code,
                reason_code
            )
            if reason_code
            else ""
        )


        # -------------------------------------------------
        # DATA/HORA
        # -------------------------------------------------

        timestamp = (
            event.get(
                "timestamp",
                ""
            )
        )


        if timestamp:

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


        # -------------------------------------------------
        # EVENTO
        # -------------------------------------------------

        event_code = (
            event.get(
                "event_type",
                ""
            )
        )


        friendly_event = (
            EVENT_LABELS.get(
                event_code,
                event_code
            )
        )


        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        status_code = (
            event.get(
                "status",
                ""
            )
        )


        friendly_status = (
            STATUS_LABELS.get(
                status_code,
                status_code
            )
        )


        # -------------------------------------------------
        # LINHA
        # -------------------------------------------------

        audit_rows.append(
            {
                "Horário":
                    timestamp,

                "Evento":
                    friendly_event,

                "Status":
                    friendly_status,

                "Prompt do usuário":
                    prompt_text,

                "Motivo do bloqueio":
                    friendly_reason,
            }
        )


    audit_df = pd.DataFrame(
        audit_rows
    )


    st.dataframe(
        audit_df,
        use_container_width=True,
        hide_index=True,
        height=430,

        column_config={

            "Horário":
                st.column_config.TextColumn(
                    "Horário",
                    width="small",
                ),

            "Evento":
                st.column_config.TextColumn(
                    "Evento",
                    width="medium",
                ),

            "Status":
                st.column_config.TextColumn(
                    "Status",
                    width="small",
                ),

            "Prompt do usuário":
                st.column_config.TextColumn(
                    "Prompt do usuário",
                    width="large",
                ),

            "Motivo do bloqueio":
                st.column_config.TextColumn(
                    "Motivo do bloqueio",
                    width="large",
                ),
        },
    )


    st.divider()

    # =====================================================
    # BLOQUEIOS
    # =====================================================

    blocked_reasons = {}


    for event in audit_events:

        if (
            event.get(
                "status"
            )
            != "blocked"
        ):

            continue


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


        reason_code = None


        if isinstance(
            input_guardrail,
            dict
        ):

            reason_code = (
                input_guardrail.get(
                    "reason"
                )
            )


        elif isinstance(
            output_guardrail,
            dict
        ):

            reason_code = (
                output_guardrail.get(
                    "reason"
                )
            )


        if not reason_code:

            reason_code = (
                "outro"
            )


        friendly_reason = (
            REASON_LABELS.get(
                reason_code,
                reason_code
            )
        )


        blocked_reasons[
            friendly_reason
        ] = (
            blocked_reasons.get(
                friendly_reason,
                0
            )
            + 1
        )


    # =====================================================
    # GRÁFICO DE AMEAÇAS
    # =====================================================

    if blocked_reasons:

        st.subheader(
            "Ameaças bloqueadas"
        )

        st.caption(
            "Tipos de solicitações interrompidas "
            "pelas proteções do FinPilot."
        )


        blocked_df = pd.DataFrame(
            [
                {
                    "Motivo":
                        reason,

                    "Quantidade":
                        quantity,
                }

                for reason, quantity
                in blocked_reasons.items()
            ]
        )


        blocked_df = (
            blocked_df
            .sort_values(
                by="Quantidade",
                ascending=False
            )
        )


        blocked_df[
            "QuantidadeTexto"
        ] = (
            blocked_df[
                "Quantidade"
            ]
            .astype(str)
        )


        max_value = float(
            blocked_df[
                "Quantidade"
            ].max()
        )


        scale_max = max(
            max_value * 1.20,
            1
        )


        bars = (
            alt.Chart(
                blocked_df
            )
            .mark_bar(
                cornerRadiusEnd=7,
                size=30,
            )
            .encode(

                x=alt.X(
                    "Quantidade:Q",

                    scale=alt.Scale(
                        domain=[
                            0,
                            scale_max,
                        ]
                    ),

                    axis=None,
                ),

                y=alt.Y(
                    "Motivo:N",
                    title=None,
                    sort="-x",

                    axis=alt.Axis(
                        labelLimit=380,
                        labelFontSize=12,
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "Motivo:N",
                        title="Motivo",
                    ),

                    alt.Tooltip(
                        "Quantidade:Q",
                        title="Bloqueios",
                    ),
                ],
            )
        )


        labels = (
            alt.Chart(
                blocked_df
            )
            .mark_text(
                align="left",
                baseline="middle",
                dx=7,
                fontSize=13,
                fontWeight="bold",
            )
            .encode(

                x=alt.X(
                    "Quantidade:Q",

                    scale=alt.Scale(
                        domain=[
                            0,
                            scale_max,
                        ]
                    ),
                ),

                y=alt.Y(
                    "Motivo:N",
                    sort="-x",
                ),

                text=alt.Text(
                    "QuantidadeTexto:N"
                ),
            )
        )


        threats_chart = (
            bars
            + labels
        ).properties(

            height=max(
                150,
                len(
                    blocked_df
                ) * 55
            )
        )


        st.altair_chart(
            threats_chart,
            use_container_width=True,
        )


        st.divider()

        # =================================================
        # EXPLICAÇÃO
        # =================================================

        st.subheader(
            "Entenda os bloqueios"
        )


        if (
            "Tentativa de executar transação financeira"
            in blocked_reasons
        ):

            st.warning(
                "**Transação financeira bloqueada**\n\n"
                "O usuário tentou solicitar PIX, "
                "transferência ou pagamento. "
                "O FinPilot pode analisar o impacto "
                "financeiro, mas não executa a operação."
            )


        if (
            "Tentativa de alterar as regras do agente"
            in blocked_reasons
        ):

            st.warning(
                "**Tentativa de manipular o agente**\n\n"
                "Foi identificado um pedido para ignorar "
                "instruções, revelar informações internas "
                "ou contornar as regras de segurança."
            )


        if (
            "Tentativa de inferir informação sensível"
            in blocked_reasons
        ):

            st.warning(
                "**Inferência sensível bloqueada**\n\n"
                "O FinPilot impediu uma tentativa de inferir "
                "informações sensíveis a partir "
                "dos dados financeiros."
            )


        if (
            "Resposta potencialmente insegura"
            in blocked_reasons
        ):

            st.warning(
                "**Resposta insegura bloqueada**\n\n"
                "O guardrail de saída detectou uma resposta "
                "incompatível com as regras de segurança."
            )


    st.divider()

    # =====================================================
    # STATUS
    # =====================================================

    st.subheader(
        "Status das proteções"
    )


    status1, status2, status3 = (
        st.columns(3)
    )


    with status1:

        st.success(
            "Input Guardrail\n\nAtivo"
        )


    with status2:

        st.success(
            "Output Guardrail\n\nAtivo"
        )


    with status3:

        st.success(
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

    # -----------------------------------------------------
    # RENDA
    # -----------------------------------------------------

    st.subheader(
        "Minha renda"
    )


    monthly_income = (
        st.number_input(
            "Renda mensal",
            min_value=0.0,
            step=100.0,
            format="%.2f",
            help=(
                "Informe sua renda líquida mensal."
            ),
        )
    )


    st.caption(
        "Usada para calcular saldo, "
        "reserva e limite seguro."
    )


    st.divider()

    # -----------------------------------------------------
    # FONTE DE DADOS
    # -----------------------------------------------------

    st.subheader(
        "Fonte de dados"
    )


    data_source = (
        st.radio(
            "Escolha os dados:",
            [
                "Usar extrato fictício",
                "Enviar meu CSV",
            ],
        )
    )


    uploaded_file = None


    if (
        data_source
        == "Enviar meu CSV"
    ):

        uploaded_file = (
            st.file_uploader(
                "Envie seu extrato em CSV",
                type=[
                    "csv"
                ],
            )
        )


        st.caption(
            "As movimentações serão analisadas "
            "automaticamente pelo FinPilot."
        )


    # -----------------------------------------------------
    # NAVEGAÇÃO
    # -----------------------------------------------------

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
# ADMIN
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

if (
    data_source
    == "Enviar meu CSV"
    and uploaded_file
    is not None
):

    try:

        raw_df, csv_info = (
            read_csv_flexible(
                uploaded_file
            )
        )


        df, normalization_report = (
            normalize_bank_dataframe(
                raw_df
            )
        )


        unresolved_types = (
            normalization_report[
                "unresolved_types"
            ]
        )


        if unresolved_types > 0:

            st.warning(
                "Não foi possível identificar "
                "automaticamente quais movimentações "
                "são entradas ou saídas."
            )


            type_options = (
                [
                    "Selecione..."
                ]
                + list(
                    raw_df.columns
                )
            )


            selected_type_column = (
                st.selectbox(
                    "Qual coluna indica "
                    "entrada ou saída?",
                    type_options,
                )
            )


            if (
                selected_type_column
                != "Selecione..."
            ):

                df, normalization_report = (
                    normalize_bank_dataframe(
                        raw_df,
                        manual_mapping={
                            "type":
                                selected_type_column
                        },
                    )
                )

            else:

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

    try:

        df = pd.read_csv(
            DEFAULT_FILEPATH
        )


    except Exception as error:

        st.error(
            "Não foi possível carregar "
            "o extrato padrão."
        )

        st.code(
            str(
                error
            )
        )

        st.stop()


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
        "O arquivo ainda não está pronto "
        "para análise."
    )

    st.warning(
        validation_error
    )

    st.stop()


# =========================================================
# NORMALIZAÇÃO
# =========================================================

df = df.copy()


df["date"] = (
    pd.to_datetime(
        df["date"],
        errors="coerce",
    )
)


df["amount"] = (
    pd.to_numeric(
        df["amount"],
        errors="coerce",
    )
)


df["type"] = (
    df["type"]
    .astype(str)
    .str.strip()
    .str.lower()
)


df["description"] = (
    df["description"]
    .astype(str)
    .str.strip()
)


df["category"] = (
    df["category"]
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
# DESPESAS E CRÉDITOS
# =========================================================

expense_df = (
    df[
        df["type"]
        == "saida"
    ]
    .copy()
)


credit_df = (
    df[
        df["type"]
        == "entrada"
    ]
    .copy()
)


source_credits = float(
    credit_df[
        "amount"
    ].sum()
)


# =========================================================
# DATAFRAME DO AGENTE
# =========================================================

analysis_df = (
    expense_df.copy()
)


if monthly_income > 0:

    reference_date = (
        df["date"].min()
        if not df.empty
        else pd.Timestamp.today()
    )


    income_row = (
        pd.DataFrame(
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
                        float(
                            monthly_income
                        ),
                }
            ]
        )
    )


    analysis_df = (
        pd.concat(
            [
                analysis_df,
                income_row,
            ],
            ignore_index=True,
        )
    )


# =========================================================
# CÁLCULOS
# =========================================================

income = float(
    monthly_income
)


expenses = float(
    expense_df[
        "amount"
    ].sum()
)


balance = (
    income
    - expenses
)


reserve = (
    income
    * RESERVE_PERCENTAGE
)


safe_spend = max(
    balance
    - reserve,
    0.0
)


# =========================================================
# INSIGHTS
# =========================================================

category_data = (
    expenses_by_category(
        expense_df
    )
)


recurring_expenses = (
    detect_recurring_expenses(
        expense_df
    )
)


anomalies = (
    detect_spending_anomalies(
        expense_df
    )
)


if monthly_income > 0:

    forecast = (
        forecast_month_end_balance(
            analysis_df
        )
    )

else:

    forecast = None


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
        "para obter uma análise financeira completa."
    )


st.divider()


# =========================================================
# KPIs
# =========================================================

col1, col2, col3, col4 = (
    st.columns(4)
)


with col1:

    st.metric(
        "Renda mensal",
        format_brl(
            income
        )
    )


with col2:

    st.metric(
        "Despesas identificadas",
        format_brl(
            expenses
        )
    )


with col3:

    st.metric(
        "Saldo disponível",
        format_brl(
            balance
        )
    )


with col4:

    st.metric(
        "Limite seguro",
        format_brl(
            safe_spend
        )
    )


if (
    source_credits > 0
    and data_source
    == "Enviar meu CSV"
):

    st.caption(
        "O arquivo contém "
        f"{format_brl(source_credits)} "
        "em créditos/pagamentos. "
        "Eles não foram considerados "
        "como renda mensal."
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
    "os gastos classificados nela."
)


if not category_data.empty:

    # =====================================================
    # ESTADO
    # =====================================================

    if (
        "category_chart_version"
        not in st.session_state
    ):

        st.session_state.category_chart_version = 0


    # =====================================================
    # CATEGORIAS
    # =====================================================

    category_df = (
        category_data
        .reset_index()
    )


    category_df.columns = [
        "Categoria",
        "Valor",
    ]


    category_df = (
        category_df
        .sort_values(
            by="Valor",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


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


    max_category_value = float(
        category_df[
            "Valor"
        ].max()
    )


    category_chart_max = (
        max_category_value
        * 1.30
    )


    if category_chart_max <= 0:

        category_chart_max = 1


    # =====================================================
    # SELEÇÃO
    # =====================================================

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


    # =====================================================
    # BARRAS
    # =====================================================

    category_bars = (
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

                scale=alt.Scale(
                    domain=[
                        0,
                        category_chart_max,
                    ]
                ),

                axis=None,
            ),

            y=alt.Y(
                "Categoria:N",
                title=None,
                sort="-x",

                axis=alt.Axis(
                    labelLimit=220,
                    labelFontSize=12,
                ),
            ),

            opacity=alt.condition(
                category_selection,
                alt.value(1),
                alt.value(0.55),
            ),

            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria",
                ),

                alt.Tooltip(
                    "Valor:Q",
                    title="Total",
                    format=",.2f",
                ),
            ],
        )
        .add_params(
            category_selection
        )
    )


    # =====================================================
    # VALORES
    # =====================================================

    category_labels = (
        alt.Chart(
            category_df
        )
        .mark_text(
            align="left",
            baseline="middle",
            dx=8,
            fontSize=12,
            fontWeight="bold",
        )
        .encode(

            x=alt.X(
                "Valor:Q",

                scale=alt.Scale(
                    domain=[
                        0,
                        category_chart_max,
                    ]
                ),
            ),

            y=alt.Y(
                "Categoria:N",
                sort="-x",
            ),

            text=alt.Text(
                "ValorFormatado:N"
            ),
        )
    )


    category_chart = (
        category_bars
        + category_labels
    ).properties(

        height=max(
            260,
            len(
                category_df
            ) * 50
        )
    )


    # =====================================================
    # COLUNAS
    # =====================================================

    chart_col1, chart_col2 = (
        st.columns(
            [
                1.25,
                1,
            ]
        )
    )


    # =====================================================
    # ESQUERDA
    # =====================================================

    with chart_col1:

        st.markdown(
            "#### Gastos por categoria"
        )


        chart_key = (
            "category_chart_"
            f"{st.session_state.category_chart_version}"
        )


        chart_event = (
            st.altair_chart(
                category_chart,
                use_container_width=True,
                key=chart_key,
                on_select="rerun",
                selection_mode=[
                    "categoria_select"
                ],
            )
        )


    # =====================================================
    # IDENTIFICA SELEÇÃO
    # =====================================================

    selected_category = None


    try:

        selection_state = (
            getattr(
                chart_event,
                "selection",
                {}
            )
        )


        category_result = (
            selection_state.get(
                "categoria_select",
                []
            )
        )


        if isinstance(
            category_result,
            list
        ):

            if category_result:

                first_result = (
                    category_result[0]
                )


                if isinstance(
                    first_result,
                    dict
                ):

                    selected_category = (
                        first_result.get(
                            "Categoria"
                        )
                    )


        elif isinstance(
            category_result,
            dict
        ):

            selected_value = (
                category_result.get(
                    "Categoria"
                )
            )


            if isinstance(
                selected_value,
                list
            ):

                if selected_value:

                    selected_category = (
                        selected_value[0]
                    )


            elif selected_value:

                selected_category = (
                    selected_value
                )


    except Exception:

        selected_category = None


    # =====================================================
    # DIREITA
    # =====================================================

    with chart_col2:

        if selected_category:

            title_col, clear_col = (
                st.columns(
                    [
                        2.8,
                        1.2,
                    ]
                )
            )


            with title_col:

                st.markdown(
                    f"#### {selected_category}"
                )


            with clear_col:

                if st.button(
                    "Limpar seleção",
                    key="clear_category",
                    use_container_width=True,
                ):

                    st.session_state.category_chart_version += 1

                    st.rerun()


            selected_transactions = (
                expense_df[
                    expense_df[
                        "category"
                    ]
                    == selected_category
                ]
                .copy()
            )


            detail_df = (
                selected_transactions
                .groupby(
                    "description",
                    as_index=False,
                )
                .agg(

                    Valor=(
                        "amount",
                        "sum"
                    ),

                    Quantidade=(
                        "amount",
                        "count"
                    ),
                )
            )


            detail_df = (
                detail_df
                .sort_values(
                    by="Valor",
                    ascending=False
                )
                .reset_index(
                    drop=True
                )
            )


            detail_df[
                "ValorFormatado"
            ] = (
                detail_df[
                    "Valor"
                ]
                .apply(
                    format_brl
                )
            )


            max_detail_value = (
                float(
                    detail_df[
                        "Valor"
                    ].max()
                )
                if not detail_df.empty
                else 0
            )


            detail_chart_max = (
                max_detail_value
                * 1.35
            )


            if detail_chart_max <= 0:

                detail_chart_max = 1


            detail_bars = (
                alt.Chart(
                    detail_df
                )
                .mark_bar(
                    cornerRadiusEnd=6,
                    size=26,
                )
                .encode(

                    x=alt.X(
                        "Valor:Q",

                        scale=alt.Scale(
                            domain=[
                                0,
                                detail_chart_max,
                            ]
                        ),

                        axis=None,
                    ),

                    y=alt.Y(
                        "description:N",
                        title=None,
                        sort="-x",

                        axis=alt.Axis(
                            labelLimit=210,
                            labelFontSize=11,
                        ),
                    ),

                    tooltip=[
                        alt.Tooltip(
                            "description:N",
                            title="Descrição",
                        ),

                        alt.Tooltip(
                            "Valor:Q",
                            title="Valor",
                            format=",.2f",
                        ),

                        alt.Tooltip(
                            "Quantidade:Q",
                            title="Quantidade",
                        ),
                    ],
                )
            )


            detail_labels = (
                alt.Chart(
                    detail_df
                )
                .mark_text(
                    align="left",
                    baseline="middle",
                    dx=8,
                    fontSize=12,
                    fontWeight="bold",
                )
                .encode(

                    x=alt.X(
                        "Valor:Q",

                        scale=alt.Scale(
                            domain=[
                                0,
                                detail_chart_max,
                            ]
                        ),
                    ),

                    y=alt.Y(
                        "description:N",
                        sort="-x",
                    ),

                    text=alt.Text(
                        "ValorFormatado:N"
                    ),
                )
            )


            detail_chart = (
                detail_bars
                + detail_labels
            ).properties(

                height=max(
                    230,
                    len(
                        detail_df
                    ) * 48
                )
            )


            st.altair_chart(
                detail_chart,
                use_container_width=True,
            )


        else:

            st.markdown(
                "#### Participação nos gastos"
            )


            donut_chart = (
                alt.Chart(
                    category_df
                )
                .mark_arc(
                    innerRadius=65
                )
                .encode(

                    theta=alt.Theta(
                        "Valor:Q"
                    ),

                    color=alt.Color(
                        "Categoria:N",
                        title=None,

                        legend=alt.Legend(
                            orient="bottom",
                            columns=2,
                        ),
                    ),

                    tooltip=[
                        alt.Tooltip(
                            "Categoria:N",
                            title="Categoria",
                        ),

                        alt.Tooltip(
                            "Valor:Q",
                            title="Valor",
                            format=",.2f",
                        ),
                    ],
                )
                .properties(
                    height=280
                )
            )


            st.altair_chart(
                donut_chart,
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


        selected_transactions = (
            expense_df[
                expense_df[
                    "category"
                ]
                == selected_category
            ]
            .copy()
        )


        category_total = float(
            selected_transactions[
                "amount"
            ].sum()
        )


        transaction_count = int(
            len(
                selected_transactions
            )
        )


        average_transaction = (
            category_total
            / transaction_count
            if transaction_count > 0
            else 0.0
        )


        d1, d2, d3 = (
            st.columns(3)
        )


        with d1:

            st.metric(
                "Total da categoria",
                format_brl(
                    category_total
                )
            )


        with d2:

            st.metric(
                "Quantidade de transações",
                transaction_count
            )


        with d3:

            st.metric(
                "Ticket médio",
                format_brl(
                    average_transaction
                )
            )


        st.markdown(
            "#### Gastos classificados"
        )


        transaction_summary = (
            selected_transactions
            .groupby(
                "description",
                as_index=False,
            )
            .agg(

                Quantidade=(
                    "amount",
                    "count"
                ),

                Valor=(
                    "amount",
                    "sum"
                ),
            )
        )


        transaction_summary = (
            transaction_summary
            .sort_values(
                by="Valor",
                ascending=False
            )
        )


        transaction_summary = (
            transaction_summary
            .rename(
                columns={
                    "description":
                        "Descrição"
                }
            )
        )


        transaction_summary[
            "Valor"
        ] = (
            transaction_summary[
                "Valor"
            ]
            .apply(
                format_brl
            )
        )


        st.dataframe(
            transaction_summary,
            use_container_width=True,
            hide_index=True,
        )


        with st.expander(
            "Ver transações individuais"
        ):

            transaction_detail = (
                selected_transactions[
                    [
                        "date",
                        "description",
                        "amount",
                    ]
                ]
                .copy()
            )


            transaction_detail = (
                transaction_detail
                .sort_values(
                    by="date",
                    ascending=False
                )
            )


            transaction_detail[
                "date"
            ] = (
                transaction_detail[
                    "date"
                ]
                .dt.strftime(
                    "%d/%m/%Y"
                )
            )


            transaction_detail[
                "amount"
            ] = (
                transaction_detail[
                    "amount"
                ]
                .apply(
                    format_brl
                )
            )


            transaction_detail = (
                transaction_detail
                .rename(
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
                transaction_detail,
                use_container_width=True,
                hide_index=True,
            )


else:

    st.info(
        "Nenhuma despesa foi identificada."
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


with p1:

    st.metric(
        "Reserva recomendada",
        format_brl(
            reserve
        ),
        help=(
            f"{RESERVE_PERCENTAGE * 100:.0f}% "
            "da renda mensal."
        ),
    )


with p2:

    st.metric(
        "Após despesas",
        format_brl(
            balance
        )
    )


with p3:

    st.metric(
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

        recurring_cols = (
            st.columns(3)
        )


        for index, item in enumerate(
            recurring_expenses
        ):

            with recurring_cols[
                index % 3
            ]:

                st.markdown(
                    f"### {item['description']}"
                )


                st.caption(
                    item[
                        "category"
                    ]
                )


                st.metric(
                    "Total",
                    format_brl(
                        item[
                            "total_amount"
                        ]
                    )
                )


                st.write(
                    f"Ocorrências: "
                    f"{item['occurrences']}"
                )


                st.write(
                    f"Média: "
                    f"{format_brl(item['average_amount'])}"
                )


    else:

        st.info(
            "Nenhum gasto recorrente "
            "foi identificado."
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


        with f1:

            st.metric(
                "Saldo atual",
                format_brl(
                    forecast[
                        "current_balance"
                    ]
                )
            )


        with f2:

            st.metric(
                "Média diária de despesas",
                format_brl(
                    forecast[
                        "average_daily_expense"
                    ]
                )
            )


        with f3:

            st.metric(
                "Saldo projetado",
                format_brl(
                    forecast[
                        "projected_month_end_balance"
                    ]
                )
            )


        st.write(
            f"Dias observados: "
            f"{forecast['days_observed']}"
        )


        st.write(
            f"Dias restantes: "
            f"{forecast['days_remaining']}"
        )


        st.write(
            "Despesas projetadas até o fim do mês: "
            f"{format_brl(forecast['projected_remaining_expenses'])}"
        )


with tab3:

    if anomalies:

        st.warning(
            f"{len(anomalies)} gasto(s) "
            "fora do padrão identificado(s)."
        )


        for anomaly in anomalies:

            a1, a2, a3 = (
                st.columns(3)
            )


            with a1:

                st.metric(
                    "Transação",
                    format_brl(
                        anomaly[
                            "amount"
                        ]
                    )
                )


            with a2:

                st.metric(
                    "Média histórica",
                    format_brl(
                        anomaly[
                            "average_amount"
                        ]
                    )
                )


            with a3:

                st.metric(
                    "Acima da média",
                    format_brl(
                        anomaly[
                            "difference_from_average"
                        ]
                    )
                )


            st.write(
                f"**{anomaly['description']}** "
                f"— {anomaly['category']}"
            )


            st.caption(
                f"Data: "
                f"{anomaly['date']}"
            )


            st.divider()


    else:

        st.success(
            "Nenhum gasto fora do padrão "
            "foi identificado."
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


st.caption(
    'Exemplos: "Posso gastar R$ 700 hoje?", '
    '"Qual é meu maior gasto?", '
    '"Quanto posso gastar sem comprometer minha reserva?"'
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
                            analysis_df
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
                        "Erro no agente financeiro:",
                        error
                    )