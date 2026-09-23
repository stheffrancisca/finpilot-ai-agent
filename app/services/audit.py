import json
from datetime import datetime
from pathlib import Path


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "audit_log.jsonl"


def ensure_log_directory():
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def write_audit_event(
    event_type: str,
    user_question: str = None,
    input_guardrail: dict = None,
    output_guardrail: dict = None,
    status: str = None,
    error: str = None,
    extra: dict = None,
):
    ensure_log_directory()

    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "user_question": user_question,
        "input_guardrail": input_guardrail,
        "output_guardrail": output_guardrail,
        "status": status,
        "error": error,
        "extra": extra or {},
    }

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(
                event,
                ensure_ascii=False
            )
            + "\n"
        )


def read_audit_log():
    ensure_log_directory()

    if not LOG_FILE.exists():
        return []

    events = []

    with open(
        LOG_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            try:
                events.append(
                    json.loads(line)
                )

            except json.JSONDecodeError:
                continue

    return events