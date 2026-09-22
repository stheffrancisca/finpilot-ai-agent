import streamlit as st
import altair as alt
import pandas as pd

from app.agents.financial_agent import (
    run_financial_agent,
)

from app.tools.financial_metrics import (
    calculate_total_income,
    calculate_total_expenses,
    calculate_balance,
    expenses_by_category,
    calculate_safe_spend,
)

from app.tools.financial_tools import (
    detect_spending_anomalies,
    detect_recurring_expenses,
    forecast_month_end_balance,
)


# =========================
# CONFIGURAÇÕES
# =========================

DEFAULT_FILEPATH = (
    "data/sample_transactions.csv"
)

st.set_page_config(
    page_title="FinPilot AI",
    page_icon="💰",
    layout="wide"
)


# =========================
# FUNÇÕES AUXILIARES
# =========================

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
        - set(df.columns)
    )

    if missing_columns:

        return (
            False,
            (
                "O arquivo está sem as colunas: "
                + ", ".join(
                    sorted(
                        missing_columns
                    )
                )
            )
        )

    valid_types = {
        "entrada",
        "saida",
    }

    normalized_types = (
        df["type"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    invalid_types = (
        set(normalized_types)
        - valid_types
    )

    if invalid_types:

        return (
            False,
            (
                "Valores inválidos em 'type': "
                + ", ".join(
                    sorted(
                        invalid_types
                    )
                )
            )
        )

    try:

        pd.to_numeric(
            df["amount"]
        )

    except Exception:

        return (
            False,
            "A coluna 'amount' deve ser numérica."
        )

    try:

        pd.to_datetime(
            df["date"]
        )

    except Exception:

        return (
            False,
            "A coluna 'date' possui datas inválidas."
        )

    return True, None


# =========================
# SIDEBAR
# =========================

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
        "Fonte de dados"
    )

    data_source = st.radio(
        "Escolha os dados:",
        [
            "Usar extrato fictício",
            "Enviar meu CSV",
        ]
    )

    uploaded_file = None

    if (
        data_source
        == "Enviar meu CSV"
    ):

        uploaded_file = (
            st.file_uploader(
                "Envie seu extrato",
                type=["csv"]
            )
        )

        st.caption(
            "Colunas obrigatórias: "
            "date, description, category, "
            "type, amount"
        )

    st.divider()

    if st.button(
        "Limpar conversa"
    ):

        st.session_state.messages = []

        st.rerun()


# =========================
# CARREGAMENTO
# =========================

if (
    data_source
    == "Enviar meu CSV"
    and uploaded_file is not None
):

    try:

        df = pd.read_csv(
            uploaded_file
        )

    except Exception as error:

        st.error(
            "Não foi possível ler o CSV."
        )

        st.code(
            str(error)
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
            str(error)
        )

        st.stop()


# =========================
# VALIDAÇÃO
# =========================

is_valid, validation_error = (
    validate_dataframe(
        df
    )
)

if not is_valid:

    st.error(
        "O arquivo não possui "
        "o formato esperado."
    )

    st.warning(
        validation_error
    )

    st.stop()


# =========================
# NORMALIZAÇÃO
# =========================

df = df.copy()

df["date"] = pd.to_datetime(
    df["date"]
)

df["amount"] = pd.to_numeric(
    df["amount"]
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


# =========================
# CÁLCULOS
# =========================

income = (
    calculate_total_income(
        df
    )
)

expenses = (
    calculate_total_expenses(
        df
    )
)

balance = (
    calculate_balance(
        df
    )
)

safe_data = (
    calculate_safe_spend(
        df
    )
)

category_data = (
    expenses_by_category(
        df
    )
)

recurring_expenses = (
    detect_recurring_expenses(
        df
    )
)

forecast = (
    forecast_month_end_balance(
        df
    )
)

anomalies = (
    detect_spending_anomalies(
        df
    )
)


# =========================
# CABEÇALHO
# =========================

st.title(
    "FinPilot AI"
)

st.caption(
    "Seu copiloto inteligente "
    "para decisões financeiras"
)

st.divider()


# =========================
# INDICADORES
# =========================

col1, col2, col3, col4 = (
    st.columns(4)
)

with col1:

    st.metric(
        "Receitas",
        format_brl(
            income
        )
    )

with col2:

    st.metric(
        "Despesas",
        format_brl(
            expenses
        )
    )

with col3:

    st.metric(
        "Saldo",
        format_brl(
            balance
        )
    )

with col4:

    st.metric(
        "Limite seguro",
        format_brl(
            safe_data[
                "safe_spend"
            ]
        )
    )


st.divider()


# =========================
# VISÃO DAS DESPESAS
# =========================

st.subheader(
    "Visão das despesas"
)

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
)

chart_col1, chart_col2 = (
    st.columns(
        [1.4, 1]
    )
)


with chart_col1:

    st.markdown(
        "#### Gastos por categoria"
    )

    bar_chart = (
        alt.Chart(
            category_df
        )
        .mark_bar(
            cornerRadiusEnd=5
        )
        .encode(
            x=alt.X(
                "Valor:Q",
                title="Valor gasto (R$)"
            ),
            y=alt.Y(
                "Categoria:N",
                title=None,
                sort="-x",
                axis=alt.Axis(
                    labelLimit=140,
                    labelFontSize=12
                )
            ),
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria"
                ),
                alt.Tooltip(
                    "Valor:Q",
                    title="Valor",
                    format=",.2f"
                ),
            ]
        )
        .properties(
            height=270
        )
    )

    st.altair_chart(
        bar_chart,
        use_container_width=True
    )


with chart_col2:

    st.markdown(
        "#### Participação nos gastos"
    )

    donut_chart = (
        alt.Chart(
            category_df
        )
        .mark_arc(
            innerRadius=60
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
                    columns=2
                )
            ),
            tooltip=[
                alt.Tooltip(
                    "Categoria:N",
                    title="Categoria"
                ),
                alt.Tooltip(
                    "Valor:Q",
                    title="Valor",
                    format=",.2f"
                ),
            ]
        )
        .properties(
            height=270
        )
    )

    st.altair_chart(
        donut_chart,
        use_container_width=True
    )


st.divider()


# =========================
# SAFE SPEND
# =========================

st.subheader(
    "Safe Spend"
)

st.write(
    "Simule uma compra e veja "
    "o impacto financeiro."
)

purchase = st.number_input(
    "Quanto você pretende gastar?",
    min_value=0.0,
    step=50.0,
    format="%.2f"
)

if st.button(
    "Analisar compra",
    type="primary"
):

    safe_spend = (
        safe_data[
            "safe_spend"
        ]
    )

    current_balance = (
        safe_data[
            "balance"
        ]
    )

    remaining_balance = (
        current_balance
        - purchase
    )

    remaining_safe_spend = (
        safe_spend
        - purchase
    )

    if safe_spend > 0:

        usage_percentage = (
            purchase
            / safe_spend
        ) * 100

    else:

        usage_percentage = 0.0

    c1, c2, c3 = (
        st.columns(3)
    )

    with c1:

        st.metric(
            "Valor da compra",
            format_brl(
                purchase
            )
        )

    with c2:

        st.metric(
            "Saldo após compra",
            format_brl(
                remaining_balance
            )
        )

    with c3:

        st.metric(
            "Uso do limite seguro",
            f"{usage_percentage:.1f}%"
        )

    if (
        purchase
        > safe_spend
    ):

        excess = (
            purchase
            - safe_spend
        )

        st.error(
            f"""
### RISCO ALTO

A compra ultrapassa o limite seguro
em **{format_brl(excess)}**.
"""
        )

    elif (
        usage_percentage
        >= 75
    ):

        st.warning(
            f"""
### RISCO MODERADO

Restariam
**{format_brl(remaining_safe_spend)}**
dentro do limite seguro.
"""
        )

    else:

        st.success(
            f"""
### RISCO BAIXO

Após a compra ainda restariam
**{format_brl(remaining_safe_spend)}**
dentro do limite seguro.
"""
        )


st.divider()


# =========================
# INSIGHTS
# =========================

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
                    f"### "
                    f"{item['description']}"
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

    c1, c2, c3 = (
        st.columns(3)
    )

    with c1:

        st.metric(
            "Saldo atual",
            format_brl(
                forecast[
                    "current_balance"
                ]
            )
        )

    with c2:

        st.metric(
            "Média diária",
            format_brl(
                forecast[
                    "average_daily_expense"
                ]
            )
        )

    with c3:

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
        "Despesas projetadas: "
        f"{format_brl(forecast['projected_remaining_expenses'])}"
    )


with tab3:

    if anomalies:

        st.warning(
            f"{len(anomalies)} gasto(s) "
            "fora do padrão."
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
            "Nenhum gasto fora do padrão."
        )


st.divider()


# =========================
# CHAT
# =========================

st.subheader(
    "FinPilot AI Assistant"
)

st.write(
    "Pergunte sobre os dados "
    "do extrato atualmente carregado."
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
        message["role"]
    ):

        st.markdown(
            message[
                "content"
            ]
        )


user_question = (
    st.chat_input(
        "Ex.: Posso gastar R$ 700?"
    )
)


if user_question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_question,
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
            "Analisando o extrato..."
        ):

            try:

                response = (
                    run_financial_agent(
                        user_question,
                        df
                    )
                )

                st.markdown(
                    response
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )

            except Exception as error:

                st.error(
                    "Não foi possível concluir "
                    "a análise agora."
                )

                print(
                    f"Erro no agente: "
                    f"{error}"
                )