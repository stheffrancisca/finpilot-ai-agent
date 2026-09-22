import pandas as pd

from app.tools.financial_metrics import (
    calculate_total_income,
    calculate_total_expenses,
    calculate_balance,
    expenses_by_category,
    calculate_safe_spend,
)


# =========================================================
# RESUMO FINANCEIRO
# =========================================================

def get_financial_summary(df):
    income = calculate_total_income(df)
    expenses = calculate_total_expenses(df)
    balance = calculate_balance(df)
    safe_data = calculate_safe_spend(df)

    return {
        "income": round(float(income), 2),
        "expenses": round(float(expenses), 2),
        "balance": round(float(balance), 2),
        "reserve": round(float(safe_data["reserve"]), 2),
        "safe_spend": round(float(safe_data["safe_spend"]), 2),
    }


# =========================================================
# DESPESA POR CATEGORIA
# =========================================================

def get_expense_by_category(df, category: str):
    categories = expenses_by_category(df)

    normalized_category = category.strip().lower()

    for category_name, value in categories.items():

        if category_name.lower() == normalized_category:
            return {
                "category": category_name,
                "amount": round(float(value), 2),
                "found": True,
            }

    return {
        "category": category,
        "amount": 0.0,
        "found": False,
    }


# =========================================================
# MAIOR CATEGORIA
# =========================================================

def get_top_expense_category(df):
    categories = expenses_by_category(df)

    if categories.empty:
        return {
            "category": None,
            "amount": 0.0,
        }

    category = categories.index[0]
    amount = categories.iloc[0]

    return {
        "category": category,
        "amount": round(float(amount), 2),
    }


# =========================================================
# IMPACTO DE UMA COMPRA
# =========================================================

def calculate_purchase_impact(df, purchase_amount: float):
    safe_data = calculate_safe_spend(df)

    purchase_amount = float(purchase_amount)
    balance = float(safe_data["balance"])
    safe_spend = float(safe_data["safe_spend"])
    reserve = float(safe_data["reserve"])

    remaining_balance = balance - purchase_amount
    remaining_safe_spend = safe_spend - purchase_amount

    if safe_spend > 0:
        usage_percentage = (
            purchase_amount / safe_spend
        ) * 100
    else:
        usage_percentage = 0.0

    if purchase_amount > safe_spend:
        risk = "alto"

    elif usage_percentage >= 75:
        risk = "moderado"

    else:
        risk = "baixo"

    excess_amount = max(
        purchase_amount - safe_spend,
        0.0
    )

    return {
        "purchase_amount": round(
            purchase_amount,
            2
        ),
        "current_balance": round(
            balance,
            2
        ),
        "reserve": round(
            reserve,
            2
        ),
        "safe_spend": round(
            safe_spend,
            2
        ),
        "remaining_balance": round(
            remaining_balance,
            2
        ),
        "remaining_safe_spend": round(
            remaining_safe_spend,
            2
        ),
        "usage_percentage": round(
            usage_percentage,
            2
        ),
        "excess_amount": round(
            excess_amount,
            2
        ),
        "risk": risk,
    }


# =========================================================
# GASTOS RECORRENTES
# =========================================================

def detect_recurring_expenses(df):
    expenses = df[
        df["type"] == "saida"
    ].copy()

    if expenses.empty:
        return []

    recurring = (
        expenses
        .groupby(
            [
                "description",
                "category"
            ]
        )["amount"]
        .agg(
            [
                "count",
                "sum",
                "mean"
            ]
        )
        .reset_index()
    )

    recurring = recurring[
        recurring["count"] >= 2
    ].copy()

    recurring = recurring.sort_values(
        by="sum",
        ascending=False
    )

    results = []

    for _, row in recurring.iterrows():

        results.append(
            {
                "description": row["description"],
                "category": row["category"],
                "occurrences": int(
                    row["count"]
                ),
                "total_amount": round(
                    float(row["sum"]),
                    2
                ),
                "average_amount": round(
                    float(row["mean"]),
                    2
                ),
            }
        )

    return results


# =========================================================
# FORECAST
# =========================================================

def forecast_month_end_balance(df):
    working_df = df.copy()

    working_df["date"] = pd.to_datetime(
        working_df["date"]
    )

    expenses = working_df[
        working_df["type"] == "saida"
    ].copy()

    income = working_df[
        working_df["type"] == "entrada"
    ]["amount"].sum()

    total_expenses = expenses["amount"].sum()

    current_balance = (
        income - total_expenses
    )

    if working_df.empty:
        return {
            "current_balance": 0.0,
            "average_daily_expense": 0.0,
            "days_observed": 0,
            "days_remaining": 0,
            "projected_remaining_expenses": 0.0,
            "projected_month_end_balance": 0.0,
        }

    first_date = working_df["date"].min()
    last_date = working_df["date"].max()

    days_observed = (
        last_date - first_date
    ).days + 1

    if days_observed <= 0:
        days_observed = 1

    average_daily_expense = (
        total_expenses / days_observed
        if days_observed > 0
        else 0.0
    )

    month_end = (
        last_date
        + pd.offsets.MonthEnd(0)
    )

    days_remaining = max(
        (month_end - last_date).days,
        0
    )

    projected_remaining_expenses = (
        average_daily_expense
        * days_remaining
    )

    projected_month_end_balance = (
        current_balance
        - projected_remaining_expenses
    )

    return {
        "current_balance": round(
            float(current_balance),
            2
        ),
        "average_daily_expense": round(
            float(average_daily_expense),
            2
        ),
        "days_observed": int(
            days_observed
        ),
        "days_remaining": int(
            days_remaining
        ),
        "projected_remaining_expenses": round(
            float(projected_remaining_expenses),
            2
        ),
        "projected_month_end_balance": round(
            float(projected_month_end_balance),
            2
        ),
    }


# =========================================================
# DETECÇÃO DE ANOMALIAS
# =========================================================

def detect_spending_anomalies(
    df,
    threshold_multiplier: float = 2.0
):
    expenses = df[
        df["type"] == "saida"
    ].copy()

    if expenses.empty:
        return []

    results = []

    grouped = expenses.groupby(
        [
            "description",
            "category"
        ]
    )

    for (
        description,
        category
    ), group in grouped:

        if len(group) < 2:
            continue

        average_amount = (
            group["amount"].mean()
        )

        threshold = (
            average_amount
            * threshold_multiplier
        )

        anomalies = group[
            group["amount"] > threshold
        ]

        for _, row in anomalies.iterrows():

            results.append(
                {
                    "date": str(
                        row["date"]
                    ),
                    "description": description,
                    "category": category,
                    "amount": round(
                        float(row["amount"]),
                        2
                    ),
                    "average_amount": round(
                        float(average_amount),
                        2
                    ),
                    "threshold": round(
                        float(threshold),
                        2
                    ),
                    "difference_from_average": round(
                        float(
                            row["amount"]
                            - average_amount
                        ),
                        2
                    ),
                }
            )

    return results