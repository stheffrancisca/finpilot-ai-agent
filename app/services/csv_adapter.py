import csv
import io
import re
import unicodedata

import pandas as pd


# =========================================================
# ALIASES DE COLUNAS
# =========================================================

COLUMN_ALIASES = {

    "date": {
        "date",
        "data",
        "data transacao",
        "data da transacao",
        "transaction date",
        "transaction_date",
        "created at",
        "created_at",
        "posted date",
        "posting date",
        "data lancamento",
        "data de lancamento",
        "data movimento",
    },

    "description": {
        "description",
        "descricao",
        "historico",
        "history",
        "memo",
        "title",
        "titulo",
        "merchant",
        "estabelecimento",
        "nome",
        "transaction",
        "transacao",
        "detalhes",
        "details",
    },

    "category": {
        "category",
        "categoria",
        "merchant category",
        "merchant_category",
    },

    "type": {
        "type",
        "tipo",
        "transaction type",
        "transaction_type",
        "natureza",
        "nature",
        "movimento",
    },

    "amount": {
        "amount",
        "valor",
        "value",
        "transaction amount",
        "transaction_amount",
        "valor transacao",
        "valor da transacao",
        "montante",
        "total",
    },

    "debit": {
        "debit",
        "debito",
        "withdrawal",
        "saida",
        "valor debito",
    },

    "credit": {
        "credit",
        "credito",
        "deposit",
        "entrada",
        "valor credito",
    },
}


# =========================================================
# TEXTO
# =========================================================

def normalize_text(value):

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
        r"[_\-]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# =========================================================
# VALOR MONETÁRIO
# =========================================================

def parse_money(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    negative_parentheses = (
        text.startswith("(")
        and text.endswith(")")
    )

    text = (
        text
        .replace("R$", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace("\u00a0", "")
        .replace(" ", "")
    )

    text = re.sub(
        r"[^0-9,\.\-\+]",
        "",
        text
    )

    if not text:
        return None

    # Ex.: 1.234,56
    if "," in text and "." in text:

        if text.rfind(",") > text.rfind("."):

            text = (
                text
                .replace(".", "")
                .replace(",", ".")
            )

        # Ex.: 1,234.56
        else:

            text = text.replace(
                ",",
                ""
            )

    # Ex.: 1234,56
    elif "," in text:

        parts = text.split(",")

        if (
            len(parts) == 2
            and len(parts[-1]) <= 2
        ):

            text = text.replace(
                ",",
                "."
            )

        else:

            text = text.replace(
                ",",
                ""
            )

    # Ex.: 1.234
    elif "." in text:

        parts = text.split(".")

        if (
            len(parts) == 2
            and len(parts[-1]) == 3
        ):

            text = text.replace(
                ".",
                ""
            )

    try:

        result = float(text)

        if negative_parentheses:
            result = -abs(result)

        return result

    except ValueError:

        return None


# =========================================================
# SEPARADOR
# =========================================================

def detect_separator(text):

    sample = text[:10000]

    try:

        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=[
                ",",
                ";",
                "\t",
                "|",
            ],
        )

        return dialect.delimiter

    except Exception:

        counts = {
            ",": sample.count(","),
            ";": sample.count(";"),
            "\t": sample.count("\t"),
            "|": sample.count("|"),
        }

        separator = max(
            counts,
            key=counts.get
        )

        if counts[separator] == 0:
            return ","

        return separator


# =========================================================
# LEITURA FLEXÍVEL
# =========================================================

def read_csv_flexible(uploaded_file):

    raw_bytes = uploaded_file.getvalue()

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1",
    ]

    last_error = None

    for encoding in encodings:

        try:

            text = raw_bytes.decode(
                encoding
            )

            separator = detect_separator(
                text
            )

            df = pd.read_csv(
                io.StringIO(text),
                sep=separator,
                engine="python",
            )

            if len(df.columns) > 1:

                return (
                    df,
                    {
                        "encoding": encoding,
                        "separator": separator,
                    },
                )

        except Exception as error:

            last_error = error

    raise ValueError(
        "Não foi possível interpretar o CSV. "
        f"Último erro: {last_error}"
    )


# =========================================================
# DETECÇÃO DE COLUNAS
# =========================================================

def detect_columns(df):

    normalized_columns = {
        column: normalize_text(column)
        for column in df.columns
    }

    mapping = {}

    for target, aliases in COLUMN_ALIASES.items():

        normalized_aliases = {
            normalize_text(alias)
            for alias in aliases
        }

        for original, normalized in normalized_columns.items():

            if normalized in normalized_aliases:

                mapping[target] = original
                break

        if target in mapping:
            continue

        for original, normalized in normalized_columns.items():

            for alias in normalized_aliases:

                if (
                    alias in normalized
                    or normalized in alias
                ):

                    if len(alias) >= 4:

                        mapping[target] = original
                        break

            if target in mapping:
                break

    return mapping


# =========================================================
# TIPO DE TRANSAÇÃO
# =========================================================

def normalize_transaction_type(value):

    text = normalize_text(value)

    entrada_terms = {
        "entrada",
        "receita",
        "credito",
        "credit",
        "income",
        "deposit",
        "deposito",
        "recebimento",
        "received",
    }

    saida_terms = {
        "saida",
        "despesa",
        "debito",
        "debit",
        "expense",
        "withdrawal",
        "pagamento",
        "purchase",
        "compra",
    }

    if text in entrada_terms:
        return "entrada"

    if text in saida_terms:
        return "saida"

    for term in entrada_terms:

        if term in text:
            return "entrada"

    for term in saida_terms:

        if term in text:
            return "saida"

    return None


# =========================================================
# DETECÇÃO DE EXTRATO DE CARTÃO
# =========================================================

def detect_statement_kind(df, mapping):

    amount_column = mapping.get(
        "amount"
    )

    description_column = mapping.get(
        "description"
    )

    if not amount_column:
        return "unknown"

    amounts = (
        df[amount_column]
        .apply(parse_money)
        .dropna()
    )

    if amounts.empty:
        return "unknown"

    descriptions = ""

    if description_column:

        descriptions = " ".join(
            df[description_column]
            .fillna("")
            .astype(str)
            .map(normalize_text)
            .tolist()
        )

    card_markers = [
        "pagamento recebido",
        "parcela",
        "boleto no credito",
        "iof",
        "fatura",
    ]

    marker_score = sum(
        marker in descriptions
        for marker in card_markers
    )

    has_positive = (
        amounts > 0
    ).any()

    has_negative = (
        amounts < 0
    ).any()

    # Estrutura típica do CSV de fatura Nubank:
    # compras positivas + pagamento/crédito negativo
    if (
        marker_score >= 1
        and has_positive
        and has_negative
    ):
        return "credit_card"

    return "bank_account"


# =========================================================
# CATEGORIZAÇÃO
# =========================================================

def infer_category(description):

    text = normalize_text(
        description
    )

    rules = {

        "Tecnologia": [
            "netlify",
            "github",
            "vercel",
            "aws",
            "azure",
            "google cloud",
            "digital ocean",
            "hostinger",
        ],

        "Assinaturas": [
            "anthropic",
            "claude",
            "chatgpt",
            "openai",
            "netflix",
            "spotify",
            "youtube premium",
            "google one",
            "icloud",
            "amazon prime",
            "prime video",
            "disney",
            "hbo",
            "globoplay",
            "canva",
            "adobe",
        ],

        "Impostos e Taxas": [
            "iof",
            "tarifa",
            "taxa",
            "encargo",
            "juros",
        ],

        "Financeiro": [
            "boleto no credito",
            "boleto",
            "pagamento fatura",
            "pagamento recebido",
            "parcelamento",
        ],

        "Compras": [
            "mercadolivre",
            "mercado livre",
            "amazon",
            "shopee",
            "shein",
            "magalu",
            "magazine luiza",
            "renner",
            "riachuelo",
            "zara",
            "aliexpress",
            "americanas",
            "casas bahia",
        ],

        "Transporte": [
            "uber",
            "99",
            "cabify",
            "taxi",
            "posto",
            "shell",
            "ipiranga",
            "gasolina",
            "combustivel",
            "estacionamento",
            "metro",
            "onibus",
            "pedagio",
        ],

        "Alimentacao": [
            "ifood",
            "rappi",
            "restaurante",
            "mercado",
            "supermercado",
            "padaria",
            "mcdonald",
            "burger king",
            "pizza",
            "cafeteria",
            "carrefour",
            "assai",
            "atacadao",
            "outback",
            "starbucks",
        ],

        "Saude": [
            "farmacia",
            "drogaria",
            "hospital",
            "clinica",
            "medico",
            "laboratorio",
            "dentista",
            "academia",
            "smart fit",
        ],

        "Moradia": [
            "aluguel",
            "condominio",
            "imobiliaria",
            "quintoandar",
        ],

        "Contas": [
            "energia",
            "internet",
            "telefone",
            "agua",
            "sabesp",
            "enel",
            "vivo",
            "claro",
            "tim",
            "comgas",
        ],

        "Lazer": [
            "cinema",
            "cinemark",
            "shopping",
            "hotel",
            "airbnb",
            "show",
            "sympla",
        ],

        "Educacao": [
            "curso",
            "faculdade",
            "universidade",
            "udemy",
            "coursera",
            "alura",
            "hotmart",
            "estacio",
            "fgv",
            "insper",
        ],
    }

    for category, keywords in rules.items():

        for keyword in keywords:

            if normalize_text(keyword) in text:
                return category

    if "pix" in text:
        return "Transferencias"

    if "transferencia" in text:
        return "Transferencias"

    if "compra" in text:
        return "Compras"

    if "pagamento" in text:
        return "Financeiro"

    return "Outros"


# =========================================================
# NORMALIZAÇÃO PARA FINPILOT
# =========================================================

def normalize_bank_dataframe(
    df,
    manual_mapping=None
):

    working_df = df.copy()

    automatic_mapping = (
        detect_columns(
            working_df
        )
    )

    mapping = (
        automatic_mapping.copy()
    )

    if manual_mapping:

        for key, value in manual_mapping.items():

            if value:
                mapping[key] = value

    statement_kind = (
        detect_statement_kind(
            working_df,
            mapping
        )
    )

    # -----------------------------------------------------
    # DATA
    # -----------------------------------------------------

    date_column = mapping.get(
        "date"
    )

    if not date_column:

        raise ValueError(
            "Não consegui identificar "
            "a coluna de data."
        )

    # -----------------------------------------------------
    # DESCRIÇÃO
    # -----------------------------------------------------

    description_column = mapping.get(
        "description"
    )

    if description_column:

        description = (
            working_df[
                description_column
            ]
            .fillna("")
            .astype(str)
        )

    else:

        description = pd.Series(
            "Transação bancária",
            index=working_df.index,
        )

    amount_column = mapping.get(
        "amount"
    )

    debit_column = mapping.get(
        "debit"
    )

    credit_column = mapping.get(
        "credit"
    )

    if (
        not amount_column
        and not debit_column
        and not credit_column
    ):

        raise ValueError(
            "Não consegui identificar "
            "a coluna de valor, débito ou crédito."
        )

    result = pd.DataFrame(
        index=working_df.index
    )

    result["date"] = pd.to_datetime(
        working_df[
            date_column
        ],
        errors="coerce",
        dayfirst=True,
    )

    result["description"] = (
        description
    )

    # =====================================================
    # DÉBITO / CRÉDITO SEPARADOS
    # =====================================================

    if (
        debit_column
        or credit_column
    ):

        if debit_column:

            debit_values = (
                working_df[
                    debit_column
                ]
                .apply(
                    parse_money
                )
                .fillna(0)
                .abs()
            )

        else:

            debit_values = pd.Series(
                0.0,
                index=working_df.index,
            )

        if credit_column:

            credit_values = (
                working_df[
                    credit_column
                ]
                .apply(
                    parse_money
                )
                .fillna(0)
                .abs()
            )

        else:

            credit_values = pd.Series(
                0.0,
                index=working_df.index,
            )

        net_values = (
            credit_values
            - debit_values
        )

        result["amount"] = (
            net_values.abs()
        )

        result["type"] = (
            net_values.apply(
                lambda value:
                    "entrada"
                    if value > 0
                    else "saida"
            )
        )

    # =====================================================
    # COLUNA ÚNICA DE VALOR
    # =====================================================

    else:

        raw_amounts = (
            working_df[
                amount_column
            ]
            .apply(
                parse_money
            )
        )

        result["amount"] = (
            raw_amounts.abs()
        )

        # -------------------------------------------------
        # EXTRATO DE CARTÃO
        # -------------------------------------------------

        if statement_kind == "credit_card":

            result["type"] = (
                raw_amounts.apply(
                    lambda value:
                        (
                            "saida"
                            if value > 0
                            else "entrada"
                        )
                        if pd.notna(value)
                        else None
                )
            )

        # -------------------------------------------------
        # CONTA CORRENTE
        # -------------------------------------------------

        else:

            type_column = mapping.get(
                "type"
            )

            if type_column:

                result["type"] = (
                    working_df[
                        type_column
                    ]
                    .apply(
                        normalize_transaction_type
                    )
                )

                unresolved = (
                    result[
                        "type"
                    ]
                    .isna()
                )

                result.loc[
                    unresolved,
                    "type"
                ] = (
                    raw_amounts[
                        unresolved
                    ]
                    .apply(
                        lambda value:
                            (
                                "entrada"
                                if value > 0
                                else "saida"
                            )
                            if pd.notna(value)
                            else None
                    )
                )

            else:

                has_positive = (
                    raw_amounts > 0
                ).any()

                has_negative = (
                    raw_amounts < 0
                ).any()

                if (
                    has_positive
                    and has_negative
                ):

                    result["type"] = (
                        raw_amounts.apply(
                            lambda value:
                                (
                                    "entrada"
                                    if value > 0
                                    else "saida"
                                )
                                if pd.notna(value)
                                else None
                        )
                    )

                else:

                    result["type"] = None

    # =====================================================
    # CATEGORIA
    # =====================================================

    category_column = mapping.get(
        "category"
    )

    if category_column:

        result["category"] = (
            working_df[
                category_column
            ]
            .astype(str)
            .str.strip()
        )

        missing_category = (
            result[
                "category"
            ]
            .isin(
                [
                    "",
                    "nan",
                    "None",
                    "none",
                ]
            )
        )

        result.loc[
            missing_category,
            "category"
        ] = (
            result.loc[
                missing_category,
                "description"
            ]
            .apply(
                infer_category
            )
        )

    else:

        result["category"] = (
            result[
                "description"
            ]
            .apply(
                infer_category
            )
        )

    # -----------------------------------------------------
    # CRÉDITOS / PAGAMENTOS DA FATURA
    # -----------------------------------------------------

    if statement_kind == "credit_card":

        credit_mask = (
            result[
                "type"
            ]
            == "entrada"
        )

        result.loc[
            credit_mask,
            "category"
        ] = "Crédito da fatura"

    else:

        income_mask = (
            result[
                "type"
            ]
            == "entrada"
        )

        result.loc[
            income_mask,
            "category"
        ] = "Receita"

    # =====================================================
    # LIMPEZA
    # =====================================================

    result = (
        result
        .dropna(
            subset=[
                "date",
                "amount",
            ]
        )
    )

    result = (
        result[
            result[
                "amount"
            ] > 0
        ]
    )

    result[
        "description"
    ] = (
        result[
            "description"
        ]
        .astype(str)
        .str.strip()
    )

    result[
        "category"
    ] = (
        result[
            "category"
        ]
        .astype(str)
        .str.strip()
    )

    unresolved_types = int(
        result[
            "type"
        ]
        .isna()
        .sum()
    )

    report = {
        "detected_mapping":
            mapping,

        "rows":
            len(result),

        "unresolved_types":
            unresolved_types,

        "statement_kind":
            statement_kind,
    }

    return (
        result.reset_index(
            drop=True
        ),
        report,
    )