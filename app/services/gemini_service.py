import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


# =========================================================
# CONFIGURAÇÃO
# =========================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY não encontrada. "
        "Verifique o arquivo .env."
    )


client = genai.Client(
    api_key=api_key
)


# =========================================================
# CONFIGURAÇÃO DO AGENTE
# =========================================================

SYSTEM_INSTRUCTION = """
Você é o FinPilot AI, um agente de análise financeira educacional.

REGRAS:

1. Sempre que uma pergunta depender de dados financeiros,
   use uma das ferramentas Python disponíveis.

2. Não invente valores.

3. Não realize cálculos financeiros mentalmente quando
   existir uma ferramenta apropriada.

4. Use exatamente os valores retornados pelas ferramentas.

5. Responda sempre em português do Brasil.

6. Valores monetários devem ser apresentados no formato:
   R$ 1.500,00

7. Percentuais devem ter no máximo duas casas decimais.

8. Caso os dados sejam insuficientes, informe claramente
   que não existem informações suficientes.

9. Não forneça recomendações de investimento.

10. Explique a conclusão de forma objetiva e educativa.
"""


# =========================================================
# ENVIO PARA GEMINI COM FUNCTION CALLING
# =========================================================

def run_gemini_agent(
    message,
    tools,
    max_retries=2
):

    last_error = None

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=tools,
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(
                            maximum_remote_calls=5
                        )
                    ),
                ),
            )

            if not response.text:
                raise ValueError(
                    "O Gemini não retornou uma resposta textual."
                )

            return response.text

        except Exception as error:

            last_error = error

            print(
                f"Tentativa {attempt + 1} falhou: "
                f"{type(error).__name__}: {error}"
            )

            if attempt < max_retries - 1:
                time.sleep(0.5)

    raise last_error