import json
import re

from app.services.gemini_service import ask_gemini
from app.tools.financial_tools import (
    get_financial_summary,
    get_expense_by_category,
    get_top_expense_category,
    calculate_purchase_impact,
)


# =========================================================
# EXTRAÇÃO E CONVERSÃO DE VALORES MONETÁRIOS
# =========================================================

def parse_money_value(value_text):
    """
    Converte valores escritos em formatos comuns para float.

    Exemplos:
    700 -> 700.00
    700,50 -> 700.50
    2.000 -> 2000.00
    2.000,50 -> 2000.50
    2000.50 -> 2000.50
    """

    value_text = value_text.strip()

    # Caso tenha ponto e vírgula
    # Exemplo brasileiro: 2.000,50
    if "." in value_text and "," in value_text:

        if value_text.rfind(",") > value_text.rfind("."):
            # Formato BR
            value_text = value_text.replace(".", "")
            value_text = value_text.replace(",", ".")

        else:
            # Formato US: 2,000.50
            value_text = value_text.replace(",", "")

    # Apenas vírgula
    elif "," in value_text:

        parts = value_text.split(",")

        if len(parts[-1]) <= 2:
            # 700,50
            value_text = value_text.replace(",", ".")
        else:
            # 2,000
            value_text = value_text.replace(",", "")

    # Apenas ponto
    elif "." in value_text:

        parts = value_text.split(".")

        # 2.000 → separador de milhar
        if (
            len(parts) > 1
            and all(len(part) == 3 for part in parts[1:])
        ):
            value_text = value_text.replace(".", "")

        # 700.50 continua decimal

    try:
        return float(value_text)

    except ValueError:
        return None


def extract_money_value(text):
    """
    Procura primeiro valores acompanhados de R$.
    Se não encontrar, procura valores numéricos comuns.
    """

    # Prioridade para valores com R$
    currency_match = re.search(
        r"R\$\s*(\d[\d.,]*)",
        text,
        flags=re.IGNORECASE
    )

    if currency_match:
        return parse_money_value(
            currency_match.group(1)
        )

    # Caso o usuário não escreva R$
    generic_match = re.search(
        r"\b(\d[\d.,]*)\b",
        text
    )

    if generic_match:
        return parse_money_value(
            generic_match.group(1)
        )

    return None


# =========================================================
# IDENTIFICAÇÃO DE CATEGORIA
# =========================================================

def detect_category(question):

    categories = {
        "moradia": "Moradia",
        "alimentacao": "Alimentacao",
        "alimentação": "Alimentacao",
        "contas": "Contas",
        "lazer": "Lazer",
        "transporte": "Transporte",
        "saude": "Saude",
        "saúde": "Saude",
        "assinaturas": "Assinaturas",
    }

    question_lower = question.lower()

    for keyword, category in categories.items():

        if keyword in question_lower:
            return category

    return None


# =========================================================
# AGENTE FINANCEIRO
# =========================================================

def run_financial_agent(question):

    question_lower = question.lower()

    # -----------------------------------------------------
    # 1. SIMULAÇÃO DE COMPRA
    # -----------------------------------------------------

    purchase_value = extract_money_value(question)

    purchase_keywords = [
        "gastar",
        "gasto",
        "comprar",
        "compra",
        "posso",
        "pagar",
        "custar",
        "adquirir",
    ]

    is_purchase_question = any(
        keyword in question_lower
        for keyword in purchase_keywords
    )

    if (
        purchase_value is not None
        and is_purchase_question
    ):

        tool_result = calculate_purchase_impact(
            purchase_value
        )

        prompt = f"""
Você é o FinPilot AI, um assistente de análise financeira.

PERGUNTA DO USUÁRIO:

{question}

Uma ferramenta financeira determinística em Python
calculou o impacto da compra.

RESULTADO DA FERRAMENTA:

{json.dumps(tool_result, ensure_ascii=False, indent=2)}

REGRAS OBRIGATÓRIAS:

- Use exatamente o valor da compra retornado pela ferramenta.
- Não faça novos cálculos.
- Não altere nenhum número.
- Não invente informações.
- Não arredonde valores de forma diferente dos valores fornecidos.
- Mostre valores monetários com 2 casas decimais.
- Mostre percentuais com no máximo 2 casas decimais.
- Informe o nível de risco.
- Informe o saldo atual.
- Informe o saldo após a compra.
- Informe o limite seguro.
- Informe quanto do limite seguro será utilizado.
- Informe o limite seguro restante.
- Se o risco for alto, deixe claro que a compra ultrapassa
  o limite seguro definido pelo sistema.
- Não diga simplesmente que uma compra é "tranquila"
  sem apresentar os números.
- Responda em português do Brasil.
- Seja objetivo.

Não invente nenhum valor além dos retornados pela ferramenta Python.
"""

        return ask_gemini(prompt)

    # -----------------------------------------------------
    # 2. MAIOR CATEGORIA DE DESPESA
    # -----------------------------------------------------

    if (
        "categoria" in question_lower
        and (
            "mais" in question_lower
            or "maior" in question_lower
        )
    ):

        tool_result = get_top_expense_category()

        prompt = f"""
Você é o FinPilot AI.

PERGUNTA:

{question}

RESULTADO DA FERRAMENTA PYTHON:

{json.dumps(tool_result, ensure_ascii=False, indent=2)}

Responda em português do Brasil.

Use somente os valores fornecidos pela ferramenta.
Não invente informações.
Seja objetivo.
"""

        return ask_gemini(prompt)

    # -----------------------------------------------------
    # 3. GASTO EM CATEGORIA ESPECÍFICA
    # -----------------------------------------------------

    category = detect_category(question)

    if category:

        tool_result = get_expense_by_category(
            category
        )

        prompt = f"""
Você é o FinPilot AI.

PERGUNTA:

{question}

RESULTADO DA FERRAMENTA PYTHON:

{json.dumps(tool_result, ensure_ascii=False, indent=2)}

Explique o resultado em português do Brasil.

Use somente os valores fornecidos.
Não invente informações.
Seja objetivo.
"""

        return ask_gemini(prompt)

    # -----------------------------------------------------
    # 4. PERGUNTAS FINANCEIRAS GERAIS
    # -----------------------------------------------------

    summary = get_financial_summary()

    prompt = f"""
Você é o FinPilot AI.

PERGUNTA:

{question}

RESUMO FINANCEIRO CALCULADO POR PYTHON:

{json.dumps(summary, ensure_ascii=False, indent=2)}

REGRAS:

- Use somente esses dados.
- Não invente valores.
- Não invente transações.
- Não invente datas.
- Caso os dados sejam insuficientes,
  informe claramente que não é possível responder.
- Responda em português do Brasil.
- Seja objetivo e educativo.
"""

    return ask_gemini(prompt)