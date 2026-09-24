import io
import re
import unicodedata
from datetime import datetime

import pandas as pd
import pdfplumber


# =========================================================
# CATEGORIAS ENCONTRADAS NAS FATURAS
# =========================================================

CATEGORY_MAP = {
    "restaurantes": "Alimentação",
    "alimentacao": "Alimentação",
    "alimentação": "Alimentação",

    "saude": "Saúde",
    "saúde": "Saúde",

    "servicos": "Serviços",
    "serviços": "Serviços",

    "supermercados": "Supermercados",
    "supermercado": "Supermercados",

    "transporte": "Transporte",

    "compras parceladas": "Compras",
    "compras": "Compras",

    "pagamentos/creditos": "Créditos",
    "pagamentos/créditos": "Créditos",
}


# =========================================================
# LINHAS QUE NÃO DEVEM VIRAR TRANSAÇÕES
# =========================================================

IGNORE_TERMS = [
    "saldo fatura anterior",
    "total da fatura",
    "pagamento minimo",
    "pagamento mínimo",
    "limite unico",
    "limite único",
    "juros nesta fatura",
    "iof nesta fatura",
    "encargos financeiros",
    "valor original",
    "juros e encargos",
    "compras nacionais",
    "compras internacionais",
    "tarifas, encargos e multas",
]


# =========================================================
# NORMALIZA TEXTO
# =========================================================

def normalize_text(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# =========================================================
# CONVERTE VALOR BRASILEIRO
# =========================================================

def parse_brl(value):

    if value is None:
        return None

    value = str(value).strip()

    value = (
        value
        .replace("R$", "")
        .replace(" ", "")
    )

    if "," in value:

        value = (
            value
            .replace(".", "")
            .replace(",", ".")
        )

    try:
        return float(value)

    except Exception:
        return None


# =========================================================
# DESCOBRE ANO DA FATURA
# =========================================================

def detect_invoice_year(full_text):

    matches = re.findall(
        r"\b\d{2}/\d{2}/(\d{4})\b",
        full_text
    )

    years = []

    for year in matches:

        try:
            years.append(
                int(year)
            )

        except Exception:
            pass

    if years:

        return max(
            set(years),
            key=years.count
        )

    return datetime.now().year


# =========================================================
# DESCOBRE MÊS DA FATURA
# =========================================================

def detect_invoice_month(full_text):

    months = {
        "janeiro": 1,
        "fevereiro": 2,
        "marco": 3,
        "março": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }

    text = normalize_text(
        full_text
    )

    for month_name, month_number in months.items():

        month_name = normalize_text(
            month_name
        )

        if (
            f"fatura de {month_name}"
            in text
        ):

            return month_number

    return None


# =========================================================
# IDENTIFICA CATEGORIA
# =========================================================

def detect_category(line):

    normalized = normalize_text(
        line
    )

    normalized = (
        normalized
        .replace(":", "")
        .strip()
    )

    for source, target in CATEGORY_MAP.items():

        if (
            normalized
            == normalize_text(source)
        ):

            return target

    return None


# =========================================================
# LINHAS IGNORADAS
# =========================================================

def should_ignore_line(line):

    normalized = normalize_text(
        line
    )

    for term in IGNORE_TERMS:

        if (
            normalize_text(term)
            in normalized
        ):

            return True

    return False


# =========================================================
# DATA DD/MM → DATA COMPLETA
# =========================================================

def build_transaction_date(
    date_text,
    invoice_year,
    invoice_month=None,
):

    try:

        day, month = (
            date_text.split("/")
        )

        day = int(day)
        month = int(month)

        year = invoice_year

        # Fatura de janeiro pode possuir
        # transações de dezembro do ano anterior.
        if (
            invoice_month == 1
            and month == 12
        ):

            year -= 1

        return pd.Timestamp(
            year=year,
            month=month,
            day=day,
        )

    except Exception:

        return pd.NaT


# =========================================================
# CLASSIFICA CRÉDITOS
# =========================================================

def classify_credit(
    description
):

    normalized = normalize_text(
        description
    )

    # -----------------------------------------------------
    # DEVOLUÇÕES / ESTORNOS
    # -----------------------------------------------------

    refund_keywords = [
        "devolucao",
        "devolução",
        "estorno",
        "reembolso",
        "refund",
        "credito compra",
        "crédito compra",
        "cancelamento compra",
    ]

    for keyword in refund_keywords:

        if (
            normalize_text(keyword)
            in normalized
        ):

            return (
                "Devoluções",
                "devolucao",
            )

    # -----------------------------------------------------
    # PAGAMENTO DE FATURA
    # -----------------------------------------------------

    payment_keywords = [
        "pgto",
        "pagamento",
        "pagto",
        "cash ag",
        "pag fatura",
        "pagamento fatura",
    ]

    for keyword in payment_keywords:

        if (
            normalize_text(keyword)
            in normalized
        ):

            return (
                "Pagamento da fatura",
                "pagamento_fatura",
            )

    # -----------------------------------------------------
    # OUTROS CRÉDITOS
    # -----------------------------------------------------

    return (
        "Outros créditos",
        "credito",
    )


# =========================================================
# PARSE DA TRANSAÇÃO
# =========================================================

def parse_transaction_line(
    line,
    current_category,
    invoice_year,
    invoice_month,
):

    line = (
        str(line)
        .replace("\u00a0", " ")
        .strip()
    )

    pattern = re.compile(
        r"""
        ^
        (?P<date>\d{2}/\d{2})
        \s+
        (?P<description>.+?)
        \s+
        (?:
            (?P<country>[A-Z]{2})
            \s+
        )?
        R\$
        \s*
        (?P<amount>-?[\d\.]+,\d{2})
        $
        """,
        re.VERBOSE
    )

    match = pattern.match(
        line
    )

    if not match:

        return None

    date_text = (
        match.group(
            "date"
        )
    )

    description = (
        match.group(
            "description"
        )
        .strip()
    )

    amount_raw = parse_brl(
        match.group(
            "amount"
        )
    )

    if amount_raw is None:

        return None

    transaction_date = (
        build_transaction_date(
            date_text,
            invoice_year,
            invoice_month,
        )
    )

    if pd.isna(
        transaction_date
    ):

        return None

    # =====================================================
    # NEGATIVO = CRÉDITO / DEVOLUÇÃO / PAGAMENTO
    # =====================================================

    if amount_raw < 0:

        category, movement_kind = (
            classify_credit(
                description
            )
        )

        transaction_type = (
            "entrada"
        )

    # =====================================================
    # POSITIVO = COMPRA
    # =====================================================

    else:

        category = (
            current_category
            or "Outros"
        )

        movement_kind = (
            "compra"
        )

        transaction_type = (
            "saida"
        )

    return {
        "date":
            transaction_date,

        "description":
            description,

        "category":
            category,

        "type":
            transaction_type,

        "amount":
            abs(
                amount_raw
            ),

        "movement_kind":
            movement_kind,
    }


# =========================================================
# EXTRAI RESUMO DA FATURA
# =========================================================

def extract_invoice_summary(
    full_text
):

    summary = {}

    patterns = {

        "invoice_total":
            r"Total\s+R\$\s*([\d\.]+,\d{2})",

        "national_purchases":
            r"Compras nacionais\s+R\$\s*([\d\.]+,\d{2})",

        "international_purchases":
            r"Compras internacionais\s+R\$\s*([\d\.]+,\d{2})",

        "payments_credits":
            r"Pagamentos/Cr[eé]ditos\s+R\$\s*(-?[\d\.]+,\d{2})",
    }

    for key, pattern in patterns.items():

        match = re.search(
            pattern,
            full_text,
            flags=re.IGNORECASE,
        )

        if match:

            value = parse_brl(
                match.group(1)
            )

            if value is not None:

                summary[
                    key
                ] = value

    return summary


# =========================================================
# EXTRAI TRANSAÇÕES
# =========================================================

def extract_transactions_from_text(
    full_text
):

    invoice_year = (
        detect_invoice_year(
            full_text
        )
    )

    invoice_month = (
        detect_invoice_month(
            full_text
        )
    )

    lines = (
        full_text
        .splitlines()
    )

    transactions = []

    current_category = None

    inside_transactions = False

    for raw_line in lines:

        line = (
            str(raw_line)
            .replace("\u00a0", " ")
            .replace("\r", "")
            .strip()
        )

        if not line:

            continue

        normalized = normalize_text(
            line
        )

        # -------------------------------------------------
        # INÍCIO DOS LANÇAMENTOS
        # -------------------------------------------------

        if (
            "lancamentos nesta fatura"
            in normalized
        ):

            inside_transactions = True
            continue

        if (
            "data descricao pais valor"
            in normalized
        ):

            inside_transactions = True
            continue

        if not inside_transactions:

            continue

        # -------------------------------------------------
        # FINAL
        # -------------------------------------------------

        if (
            "total da fatura"
            in normalized
        ):

            break

        # -------------------------------------------------
        # CABEÇALHOS
        # -------------------------------------------------

        if (
            normalized
            == "data descricao pais valor"
        ):

            continue

        if (
            normalized.startswith(
                "pagina "
            )
        ):

            continue

        if (
            "cartao"
            in normalized
            and "sthefani"
            in normalized
        ):

            continue

        # -------------------------------------------------
        # CATEGORIA
        # -------------------------------------------------

        category = (
            detect_category(
                line
            )
        )

        if category:

            current_category = (
                category
            )

            continue

        # -------------------------------------------------
        # IGNORA TEXTO
        # -------------------------------------------------

        if should_ignore_line(
            line
        ):

            continue

        # -------------------------------------------------
        # TRANSAÇÃO
        # -------------------------------------------------

        transaction = (
            parse_transaction_line(
                line,
                current_category,
                invoice_year,
                invoice_month,
            )
        )

        if transaction:

            transactions.append(
                transaction
            )

    return (
        transactions,
        invoice_year,
        invoice_month,
    )


# =========================================================
# LEITURA PRINCIPAL
# =========================================================

def read_pdf_flexible(
    uploaded_file
):

    try:

        raw_bytes = (
            uploaded_file.getvalue()
        )

    except Exception as error:

        raise ValueError(
            "Não foi possível ler o PDF. "
            f"Detalhe: {error}"
        )

    try:

        pdf = pdfplumber.open(
            io.BytesIO(
                raw_bytes
            )
        )

    except Exception as error:

        raise ValueError(
            "Não foi possível abrir o PDF. "
            f"Detalhe: {error}"
        )

    try:

        pages_text = []

        for page in pdf.pages:

            text = (
                page.extract_text(
                    x_tolerance=2,
                    y_tolerance=3,
                )
            )

            if text:

                pages_text.append(
                    text
                )

        full_text = "\n".join(
            pages_text
        )

        if not full_text.strip():

            raise ValueError(
                "Este PDF não possui texto pesquisável."
            )

        (
            transactions,
            invoice_year,
            invoice_month,
        ) = (
            extract_transactions_from_text(
                full_text
            )
        )

        if not transactions:

            raise ValueError(
                "Não encontrei lançamentos "
                "financeiros reconhecíveis no PDF."
            )

        df = pd.DataFrame(
            transactions
        )

        # =================================================
        # LIMPEZA
        # =================================================

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["amount"] = pd.to_numeric(
            df["amount"],
            errors="coerce",
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

        df["type"] = (
            df["type"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        df["movement_kind"] = (
            df["movement_kind"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        df = (
            df.dropna(
                subset=[
                    "date",
                    "amount",
                ]
            )
            .drop_duplicates()
            .reset_index(
                drop=True
            )
        )

        # =================================================
        # RESUMO
        # =================================================

        invoice_summary = (
            extract_invoice_summary(
                full_text
            )
        )

        purchases = float(
            df.loc[
                df[
                    "movement_kind"
                ]
                == "compra",
                "amount",
            ].sum()
        )

        refunds = float(
            df.loc[
                df[
                    "movement_kind"
                ]
                == "devolucao",
                "amount",
            ].sum()
        )

        payments = float(
            df.loc[
                df[
                    "movement_kind"
                ]
                == "pagamento_fatura",
                "amount",
            ].sum()
        )

        other_credits = float(
            df.loc[
                df[
                    "movement_kind"
                ]
                == "credito",
                "amount",
            ].sum()
        )

        # Para análise do período:
        # compras - devoluções.
        net_expenses = max(
            purchases
            - refunds,
            0.0,
        )

        report = {

            "source_type":
                "credit_card_pdf",

            "pages":
                len(
                    pdf.pages
                ),

            "invoice_year":
                invoice_year,

            "invoice_month":
                invoice_month,

            "transactions_found":
                len(
                    df
                ),

            "unresolved_types":
                0,

            "invoice_summary":
                invoice_summary,

            "purchases":
                purchases,

            "refunds":
                refunds,

            "payments":
                payments,

            "other_credits":
                other_credits,

            "net_expenses":
                net_expenses,
        }

        return (
            df,
            report,
        )

    finally:

        pdf.close()