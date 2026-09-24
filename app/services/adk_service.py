import asyncio
import uuid

from google.adk import Runner
from google.adk.sessions import (
    InMemorySessionService,
)
from google.genai import types

from google_agent.agent import (
    root_agent,
)

from app.services.adk_financial_context import (
    build_context_prompt,
)

from app.services.guardrails import (
    check_input_guardrail,
    check_output_guardrail,
)

from app.services.audit import (
    write_audit_event,
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

APP_NAME = "finpilot_streamlit"

USER_ID = "finpilot_user"


# =========================================================
# EXECUÇÃO ASSÍNCRONA DO ADK
# =========================================================

async def _call_adk_agent(
    prompt
):

    # -----------------------------------------------------
    # SESSÃO LOCAL
    # -----------------------------------------------------

    session_service = (
        InMemorySessionService()
    )

    session = (
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
        )
    )

    # -----------------------------------------------------
    # RUNNER
    # -----------------------------------------------------

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[
            types.Part(
                text=prompt
            )
        ],
    )

    final_response = None

    # -----------------------------------------------------
    # EXECUTA AGENTE
    # -----------------------------------------------------

    async for event in (
        runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=content,
        )
    ):

        if (
            event.is_final_response()
        ):

            if (
                event.content
                and event.content.parts
            ):

                text_parts = []

                for part in (
                    event.content.parts
                ):

                    text = getattr(
                        part,
                        "text",
                        None,
                    )

                    if text:

                        text_parts.append(
                            text
                        )

                if text_parts:

                    final_response = (
                        "\n".join(
                            text_parts
                        )
                    )

    if not final_response:

        raise RuntimeError(
            "O agente ADK não retornou "
            "uma resposta final."
        )

    return final_response


# =========================================================
# EXECUTOR SINCRONO
# =========================================================

def _run_async(
    coroutine
):

    try:

        return asyncio.run(
            coroutine
        )

    except RuntimeError as error:

        # fallback caso já exista
        # um event loop ativo
        if (
            "asyncio.run() cannot be called"
            not in str(error)
        ):

            raise

        loop = (
            asyncio.new_event_loop()
        )

        try:

            return loop.run_until_complete(
                coroutine
            )

        finally:

            loop.close()


# =========================================================
# AGENTE FINANCEIRO ADK
# =========================================================

def run_adk_financial_agent(
    question,
    df,
):

    # -----------------------------------------------------
    # VALIDAÇÃO
    # -----------------------------------------------------

    if not question:

        return (
            "Digite uma pergunta para que eu "
            "possa analisar sua situação financeira."
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

    if not input_guardrail.get(
        "allowed",
        False,
    ):

        write_audit_event(
            event_type="input_guardrail",
            status="blocked",
            input_guardrail=input_guardrail,
            extra={
                "prompt":
                    question,

                "engine":
                    "google_adk",
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

    write_audit_event(
        event_type="input_guardrail",
        status="allowed",
        input_guardrail=input_guardrail,
        extra={
            "prompt":
                question,

            "engine":
                "google_adk",
        },
    )

    # =====================================================
    # CONTEXTO FINANCEIRO
    # =====================================================

    financial_context = (
        build_context_prompt(
            df
        )
    )

    # -----------------------------------------------------
    # PROMPT FINAL
    # -----------------------------------------------------

    prompt = f"""
{financial_context}


PERGUNTA DO USUÁRIO

{question}


INSTRUÇÕES PARA ESTA RESPOSTA

- Responda à pergunta utilizando o contexto financeiro acima.
- Não peça valores que já estejam presentes no contexto.
- Utilize as ferramentas do FinPilot quando for necessário calcular.
- Não invente informações.
- Responda em português do Brasil.
""".strip()

    # =====================================================
    # AUDITORIA
    # =====================================================

    request_id = str(
        uuid.uuid4()
    )

    write_audit_event(
        event_type="agent_request",
        status="success",
        extra={
            "prompt":
                question,

            "engine":
                "google_adk",

            "request_id":
                request_id,
        },
    )

    # =====================================================
    # EXECUÇÃO DO ADK
    # =====================================================

    try:

        response = (
            _run_async(
                _call_adk_agent(
                    prompt
                )
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

                "engine":
                    "google_adk",

                "request_id":
                    request_id,

                "error":
                    error_text,
            },
        )

        # -------------------------------------------------
        # 503
        # -------------------------------------------------

        if (
            "503"
            in error_text

            or "UNAVAILABLE"
            in error_text.upper()

            or "high demand"
            in error_text.lower()
        ):

            return (
                "O modelo de IA está temporariamente "
                "com alta demanda. Os seus dados financeiros "
                "foram processados normalmente. "
                "Tente novamente em alguns instantes."
            )

        # -------------------------------------------------
        # 429
        # -------------------------------------------------

        if (
            "429"
            in error_text

            or "RESOURCE_EXHAUSTED"
            in error_text.upper()

            or "quota"
            in error_text.lower()
        ):

            return (
                "A API de IA atingiu temporariamente "
                "o limite de uso. Os cálculos financeiros "
                "do FinPilot continuam disponíveis."
            )

        # -------------------------------------------------
        # MODELO
        # -------------------------------------------------

        if (
            "404"
            in error_text

            or "NOT_FOUND"
            in error_text.upper()
        ):

            return (
                "O modelo de IA configurado não está "
                "disponível neste momento."
            )

        return (
            "Não foi possível concluir a análise "
            "com a camada de IA agora."
        )

    # =====================================================
    # OUTPUT GUARDRAIL
    # =====================================================

    output_guardrail = (
        check_output_guardrail(
            response
        )
    )

    if not output_guardrail.get(
        "allowed",
        False,
    ):

        write_audit_event(
            event_type="output_guardrail",
            status="blocked",
            output_guardrail=output_guardrail,
            extra={
                "prompt":
                    question,

                "engine":
                    "google_adk",

                "request_id":
                    request_id,
            },
        )

        return (
            output_guardrail.get(
                "message"
            )
            or
            "A resposta foi bloqueada pelas "
            "regras de segurança do FinPilot."
        )

    write_audit_event(
        event_type="output_guardrail",
        status="allowed",
        output_guardrail=output_guardrail,
        extra={
            "prompt":
                question,

            "engine":
                "google_adk",

            "request_id":
                request_id,
        },
    )

    # =====================================================
    # SUCESSO
    # =====================================================

    write_audit_event(
        event_type="agent_response",
        status="success",
        extra={
            "prompt":
                question,

            "engine":
                "google_adk",

            "request_id":
                request_id,
        },
    )

    return (
        output_guardrail.get(
            "message"
        )
        or response
    )