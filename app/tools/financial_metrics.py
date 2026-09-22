import pandas as pd


def load_transactions(filepath):
    return pd.read_csv(filepath)


def calculate_total_income(df):
    return df[df["type"] == "entrada"]["amount"].sum()


def calculate_total_expenses(df):
    return df[df["type"] == "saida"]["amount"].sum()


def calculate_balance(df):
    return calculate_total_income(df) - calculate_total_expenses(df)


def expenses_by_category(df):
    expenses = df[df["type"] == "saida"]

    return (
        expenses.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )


def calculate_safe_spend(df, reserve_percentage=0.10):
    income = calculate_total_income(df)
    expenses = calculate_total_expenses(df)
    balance = income - expenses

    reserve = income * reserve_percentage
    safe_spend = balance - reserve

    if safe_spend < 0:
        safe_spend = 0

    return {
        "income": income,
        "expenses": expenses,
        "balance": balance,
        "reserve": reserve,
        "safe_spend": safe_spend
    }