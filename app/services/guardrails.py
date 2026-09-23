import re


# =========================================================
# PADRÕES DE RISCO
# =========================================================

PROMPT_INJECTION_PATTERNS = [
    r"ignore .*instru",
    r"ignore .*regra",
    r"ignore .*prompt",
    r"revele .*prompt",
    r"mostre .*instru",
    r"mostre .*config",
    r"system prompt",
    r"jailbreak",
    r"modo desenvolvedor",
    r"developer mode",
]

TRANSACTION_PATTERNS = [
    r"faça .*pix",
    r"fazer .*pix",
    r"envie .*dinheiro",
    r"transfira .*dinheiro",
    r"realize .*pagamento",
    r"execute .*transfer",
]

SENSITIVE_INFERENCE_PATTERNS = [
    r"tenho .*doença",
    r"tenho .*problema de saúde",
    r"qual .*minha religião",
    r"sou .*religioso",
    r"qual .*minha orientação",
    r"qual .*meu partido",
    r"qual .*minha ideologia",
    r"descubra .*minha saúde",
    r"infira .*saúde",
]

DANGEROUS_OUTPUT_PATTERNS = [
    r"executei .*pix",
    r"transferência realizada",
    r"pagamento realizado",
    r"acesso à sua conta",
    r"acessei sua conta",
]


# =========================================================
# GUARDRAIL DE ENTRADA
# =========================================================

def check_input_guardrail(user_input: str) -> dict:

    text = user_input.lower().strip()

    for pattern in PROMPT_INJECTION_PATTERNS:

        if re.search(pattern, text):

            return {
                "allowed": False,
                "reason": "prompt_injection",
                "message": (
                    "Essa solicitação tenta alterar ou contornar "
                    "as regras de segurança do FinPilot. "
                    "Posso continuar ajudando com análises financeiras."
                ),
            }

    for pattern in TRANSACTION_PATTERNS:

        if re.search(pattern, text):

            return {
                "allowed": False,
                "reason": "financial_action",
                "message": (
                    "O FinPilot não executa PIX, transferências ou pagamentos. "
                    "Posso simular o impacto financeiro da operação antes "
                    "de você decidir."
                ),
            }

    for pattern in SENSITIVE_INFERENCE_PATTERNS:

        if re.search(pattern, text):

            return {
                "allowed": False,
                "reason": "sensitive_inference",
                "message": (
                    "Não é apropriado inferir informações sensíveis, como "
                    "saúde, religião, orientação ou posição política, "
                    "a partir de dados financeiros."
                ),
            }

    return {
        "allowed": True,
        "reason": None,
        "message": None,
    }


# =========================================================
# GUARDRAIL DE SAÍDA
# =========================================================

def check_output_guardrail(response: str) -> dict:

    text = response.lower().strip()

    for pattern in DANGEROUS_OUTPUT_PATTERNS:

        if re.search(pattern, text):

            return {
                "allowed": False,
                "reason": "unsafe_output",
                "message": (
                    "A resposta foi bloqueada pelo guardrail de saída "
                    "por indicar uma ação que o FinPilot não pode executar."
                ),
            }

    return {
        "allowed": True,
        "reason": None,
        "message": response,
    }