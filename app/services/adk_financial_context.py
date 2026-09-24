import json
import math

import pandas as pd


# =========================================================
# AUXILIARES
# =========================================================

def _safe_float(value):
    try:

        value = float(value)

        if math.isnan(value):
            return 0.0

        return value

    except Exception:
        return 0.0


def _clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


# =========================================================
# PREPARA DATAFRAME
# =========================================================

def prepare_financial_dataframe(df):

    required_columns = [
        "date",
        "description",
        "category",
        "type",
        "amount",
    ]

    if df is None:

        return pd.DataFrame(
            columns=required_columns
        )

    result = df.copy()

    for column in required_columns:

        if column not in result.columns:

            if column == "amount":
                result[column] = 0.0

            else:
                result[column] = ""

    result["amount"] = pd.to_numeric(
        result["amount"],
        errors="coerce",
    ).fillna(0.0)

    result["description"] = (
        result["description"]
        .astype(str)
        .str.strip()
    )

    result["category"] = (
        result["category"]
        .astype(str)
        .str.strip()
    )

    result["type"] = (
        result["type"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    result["date"] = pd.to_datetime(
        result["date"],
        errors="coerce",
    )

    return result


# =========================================================
# IDENTIFICA RENDA INFORMADA
# =========================================================

def get_monthly_income(df):

    if df.empty:
        return 0.0

    normalized_description = (
        df["description"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    income_mask = (
        normalized_description
        .str.contains(
            "renda mensal informada",
            na=False,
        )
    )

    monthly_income = float(
        df.loc[
            income_mask,
            "amount",
        ].sum()
    )

    # fallback para bases antigas
    if monthly_income <= 0:

        income_mask = (
            (df["type"] == "entrada")
            &
            (
                df["category"]
                .astype(str)
                .str.lower()
                .str.strip()
                == "receita"
            )
        )

        monthly_income = float(
            df.loc[
                income_mask,
                "amount",
            ].sum()
        )

    return monthly_income


# =========================================================
# DEVOLUÇÕES
# =========================================================

def get_refund_mask(df):

    categories = (
        df["category"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    descriptions = (
        df["description"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    refund_terms = [
        "devolução",
        "devolucao",
        "devoluções",
        "devolucoes",
        "estorno",
        "estornos",
        "reembolso",
        "refund",
    ]

    mask = pd.Series(
        False,
        index=df.index,
    )

    for term in refund_terms:

        mask = (
            mask
            | categories.str.contains(
                term,
                na=False,
            )
            | descriptions.str.contains(
                term,
                na=False,
            )
        )

    return mask


# =========================================================
# CRIA CONTEXTO FINANCEIRO
# =========================================================

def build_financial_context(df):

    df = prepare_financial_dataframe(
        df
    )

    monthly_income = (
        get_monthly_income(
            df
        )
    )

    refund_mask = (
        get_refund_mask(
            df
        )
    )

    # -----------------------------------------------------
    # COMPRAS / DESPESAS
    # -----------------------------------------------------

    purchases_df = (
        df[
            (df["type"] == "saida")
            &
            (~refund_mask)
        ]
        .copy()
    )

    purchases = float(
        purchases_df[
            "amount"
        ].sum()
    )

    # -----------------------------------------------------
    # DEVOLUÇÕES
    # -----------------------------------------------------

    refunds_df = (
        df[
            refund_mask
        ]
        .copy()
    )

    refunds = float(
        refunds_df[
            "amount"
        ].sum()
    )

    # -----------------------------------------------------
    # GASTO LÍQUIDO
    # -----------------------------------------------------

    net_expenses = max(
        purchases - refunds,
        0.0,
    )

    balance = (
        monthly_income
        - net_expenses
    )

    reserve = (
        monthly_income
        * 0.10
    )

    safe_spend = max(
        balance
        - reserve,
        0.0,
    )

    expense_ratio = 0.0

    if monthly_income > 0:

        expense_ratio = (
            net_expenses
            / monthly_income
        ) * 100

    # -----------------------------------------------------
    # CATEGORIAS
    # -----------------------------------------------------

    expenses_by_category = {}

    if not purchases_df.empty:

        grouped = (
            purchases_df
            .groupby(
                "category"
            )["amount"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        expenses_by_category = {
            str(category):
                round(
                    _safe_float(value),
                    2,
                )

            for category, value
            in grouped.items()
        }

    # -----------------------------------------------------
    # TRANSAÇÕES
    # -----------------------------------------------------

    transactions = []

    for _, row in (
        purchases_df.iterrows()
    ):

        date_value = ""

        if pd.notna(
            row["date"]
        ):

            date_value = (
                row["date"]
                .strftime(
                    "%Y-%m-%d"
                )
            )

        transactions.append(
            {
                "date":
                    date_value,

                "description":
                    _clean_text(
                        row[
                            "description"
                        ]
                    ),

                "category":
                    _clean_text(
                        row[
                            "category"
                        ]
                    ),

                "amount":
                    round(
                        _safe_float(
                            row[
                                "amount"
                            ]
                        ),
                        2,
                    ),
            }
        )

    # -----------------------------------------------------
    # DEVOLUÇÕES DETALHADAS
    # -----------------------------------------------------

    refunds_list = []

    for _, row in (
        refunds_df.iterrows()
    ):

        date_value = ""

        if pd.notna(
            row["date"]
        ):

            date_value = (
                row["date"]
                .strftime(
                    "%Y-%m-%d"
                )
            )

        refunds_list.append(
            {
                "date":
                    date_value,

                "description":
                    _clean_text(
                        row[
                            "description"
                        ]
                    ),

                "amount":
                    round(
                        _safe_float(
                            row[
                                "amount"
                            ]
                        ),
                        2,
                    ),
            }
        )

    # -----------------------------------------------------
    # MAIOR CATEGORIA
    # -----------------------------------------------------

    top_category = None
    top_category_amount = 0.0

    if expenses_by_category:

        top_category = max(
            expenses_by_category,
            key=expenses_by_category.get,
        )

        top_category_amount = (
            expenses_by_category[
                top_category
            ]
        )

    return {
        "monthly_income":
            round(
                monthly_income,
                2,
            ),

        "purchases":
            round(
                purchases,
                2,
            ),

        "refunds":
            round(
                refunds,
                2,
            ),

        "net_expenses":
            round(
                net_expenses,
                2,
            ),

        "balance":
            round(
                balance,
                2,
            ),

        "reserve_percentage":
            10.0,

        "reserve":
            round(
                reserve,
                2,
            ),

        "safe_spend":
            round(
                safe_spend,
                2,
            ),

        "expense_ratio_percent":
            round(
                expense_ratio,
                2,
            ),

        "top_category":
            top_category,

        "top_category_amount":
            round(
                top_category_amount,
                2,
            ),

        "expenses_by_category":
            expenses_by_category,

        "transactions":
            transactions,

        "refund_transactions":
            refunds_list,

        "transaction_count":
            len(
                transactions
            ),
    }


# =========================================================
# CONTEXTO PARA O PROMPT
# =========================================================

def build_context_prompt(
    df
):

    context = (
        build_financial_context(
            df
        )
    )

    context_json = json.dumps(
        context,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
CONTEXTO FINANCEIRO ATUAL DO USUÁRIO

Os dados abaixo foram extraídos e normalizados pelo FinPilot
a partir do arquivo financeiro fornecido pelo usuário.

Eles são a fonte de verdade desta consulta.

{context_json}

REGRAS PARA UTILIZAÇÃO DO CONTEXTO:

1. Não peça novamente informações que já estejam disponíveis acima.
2. Use as ferramentas financeiras para cálculos.
3. Não invente transações ou valores.
4. Pagamentos de fatura não são renda.
5. Devoluções e estornos reduzem o gasto líquido,
   mas devem continuar sendo apresentados separadamente.
6. A renda mensal é aquela registrada em monthly_income.
7. Para descobrir a maior categoria, use expenses_by_category.
8. Para recorrências e anomalias, use transactions.
9. Se um dado realmente não estiver disponível, diga isso claramente.
""".strip()