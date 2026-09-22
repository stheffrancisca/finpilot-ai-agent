import pandas as pd

from app.tools.financial_metrics import (
    load_transactions,
    calculate_total_income,
    calculate_total_expenses,
    calculate_balance,
    expenses_by_category,
    calculate_safe_spend,
)

FILEPATH = "data/sample_transactions.csv"


def get_financial_summary():
    df = load_transactions(FILEPATH)

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


def get_expense_by_category(category: str):
    df = load_transactions(FILEPATH)

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


def get_top_expense_category():
    df = load_transactions(FILEPATH)

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


def calculate_purchase_impact(purchase_amount: float):
    df = load_transactions(FILEPATH)

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
        "purchase_amount": round(purchase_amount, 2),
        "current_balance": round(balance, 2),
        "reserve": round(reserve, 2),
        "safe_spend": round(safe_spend, 2),
        "remaining_balance": round(remaining_balance, 2),
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


def detect_recurring_expenses():
    df = load_transactions(FILEPATH)

    expenses = df[
        df["type"] == "saida"
    ].copy()

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


def forecast_month_end_balance():
    df = load_transactions(FILEPATH)

    df["date"] = pd.to_datetime(df["date"])

    expenses = df[
        df["type"] == "saida"
    ].copy()

    income = df[
        df["type"] == "entrada"
    ]["amount"].sum()

    total_expenses = expenses["amount"].sum()

    current_balance = (
        income - total_expenses
    )

    if expenses.empty:
        return {
            "current_balance": round(
                float(current_balance),
                2
            ),
            "average_daily_expense": 0.0,
            "days_observed": 0,
            "days_remaining": 0,
            "projected_remaining_expenses": 0.0,
            "projected_month_end_balance": round(
                float(current_balance),
                2
            ),
        }

    first_date = df["date"].min()
    last_date = df["date"].max()

    days_observed = (
        last_date - first_date
    ).days + 1

    average_daily_expense = (
        total_expenses / days_observed
    )

    month_end = (
        last_date
        + pd.offsets.MonthEnd(0)
    )

    days_remaining = (
        month_end - last_date
    ).days

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