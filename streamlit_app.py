import streamlit as st

from app.agents.financial_agent import run_financial_agent
from app.tools.financial_metrics import (
    load_transactions,
    calculate_total_income,
    calculate_total_expenses,
    calculate_balance,
    expenses_by_category,
    calculate_safe_spend,
)

# =========================
# CONFIGURAÇÕES
# =========================

FILEPATH = "data/sample_transactions.csv"

st.set_page_config(
    page_title="FinPilot AI",
    page_icon="💰",
    layout="wide"
)

# =========================
# CARREGAMENTO DOS DADOS
# =========================

df = load_transactions(FILEPATH)

income = calculate_total_income(df)
expenses = calculate_total_expenses(df)
balance = calculate_balance(df)
safe_data = calculate_safe_spend(df)
category_data = expenses_by_category(df)

# =========================
# CABEÇALHO
# =========================

st.title("FinPilot AI")
st.caption("Seu copiloto inteligente para decisões financeiras")

st.divider()

# =========================
# INDICADORES
# =========================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Receitas",
        value=f"R$ {income:,.2f}"
    )

with col2:
    st.metric(
        label="Despesas",
        value=f"R$ {expenses:,.2f}"
    )

with col3:
    st.metric(
        label="Saldo",
        value=f"R$ {balance:,.2f}"
    )

with col4:
    st.metric(
        label="Limite seguro",
        value=f"R$ {safe_data['safe_spend']:,.2f}"
    )

st.divider()

# =========================
# GRÁFICO
# =========================

st.subheader("Despesas por categoria")

st.bar_chart(category_data)

st.divider()

# =========================
# SAFE SPEND
# =========================

st.subheader("Safe Spend")

st.write(
    "Simule uma compra e veja o impacto na sua situação financeira."
)

purchase = st.number_input(
    "Quanto você pretende gastar?",
    min_value=0.0,
    step=50.0,
    format="%.2f"
)

if st.button("Analisar compra", type="primary"):

    safe_spend = safe_data["safe_spend"]
    current_balance = safe_data["balance"]

    remaining_balance = current_balance - purchase
    remaining_safe_spend = safe_spend - purchase

    if safe_spend > 0:
        usage_percentage = (purchase / safe_spend) * 100
    else:
        usage_percentage = 0

    st.subheader("Análise da compra")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Valor da compra",
            f"R$ {purchase:,.2f}"
        )

    with c2:
        st.metric(
            "Saldo após compra",
            f"R$ {remaining_balance:,.2f}"
        )

    with c3:
        st.metric(
            "Uso do limite seguro",
            f"{usage_percentage:.1f}%"
        )

    if purchase > safe_spend:

        excess = purchase - safe_spend

        st.error(
            f"""
### RISCO ALTO

Essa compra ultrapassa seu limite seguro em **R$ {excess:,.2f}**.

**Limite recomendado:** R$ {safe_spend:,.2f}
"""
        )

    elif usage_percentage >= 75:

        st.warning(
            f"""
### RISCO MODERADO

A compra cabe no seu limite, mas consumirá uma parte significativa
do valor disponível.

**Valor restante dentro do limite seguro:**
R$ {remaining_safe_spend:,.2f}
"""
        )

    else:

        st.success(
            f"""
### RISCO BAIXO

A compra está dentro do limite seguro.

Após a compra, ainda restariam:

**R$ {remaining_safe_spend:,.2f}**

dentro do seu limite seguro.
"""
        )

st.divider()

# =========================
# CHAT COM AGENTE
# =========================

st.subheader("FinPilot AI Assistant")

st.write(
    "Pergunte sobre sua situação financeira com base nos dados analisados."
)

# Cria memória do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra o histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de pergunta
user_question = st.chat_input(
    "Ex.: Posso gastar R$ 700 em um tênis?"
)

# =========================
# PROCESSAMENTO DA PERGUNTA
# =========================

if user_question:

    # Salva pergunta no histórico
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_question
        }
    )

    # Exibe pergunta
    with st.chat_message("user"):
        st.markdown(user_question)

    # Executa o agente financeiro
    with st.chat_message("assistant"):

        with st.spinner(
            "Analisando e executando ferramentas financeiras..."
        ):

            try:

                response = run_financial_agent(
                    user_question
                )

                st.markdown(response)

                # Salva somente respostas válidas
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response
                    }
                )

            except Exception as error:

                st.error(
                    "O FinPilot não conseguiu concluir a análise agora. "
                    "Tente novamente em alguns segundos."
                )

                # Mostra o erro somente no terminal
                print(
                    f"Erro no agente financeiro: {error}"
                )