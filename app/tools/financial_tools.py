from app.tools.financial_metrics import (
    load_transactions,
    calculate_total_income,
    calculate_total_expenses,
    calculate_balance,
    expenses_by_category,
    calculate_safe_spend,
)

FILEPATH = "data/sample_transactions.csv"


# =========================================================
# RESUMO FINANCEIRO
# =========================================================

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


# =========================================================
# DESPESA POR CATEGORIA
# =========================================================

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


# =========================================================
# MAIOR CATEGORIA DE DESPESA
# =========================================================

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


# =========================================================
# IMPACTO DE UMA COMPRA
# =========================================================

def calculate_purchase_impact(purchase_amount: float):
    df = load_transactions(FILEPATH)

    safe_data = calculate_safe_spend(df)

    purchase_amount = float(purchase_amount)

    balance = float(
        safe_data["balance"]
    )

    safe_spend = float(
        safe_data["safe_spend"]
    )

    reserve = float(
        safe_data["reserve"]
    )

    remaining_balance = (
        balance - purchase_amount
    )

    remaining_safe_spend = (
        safe_spend - purchase_amount
    )

    # -----------------------------------------
    # Percentual do limite seguro utilizado
    # -----------------------------------------

    if safe_spend > 0:

        usage_percentage = (
            purchase_amount / safe_spend
        ) * 100

    else:

        usage_percentage = 0.0

    # -----------------------------------------
    # Classificação de risco
    # -----------------------------------------

    if purchase_amount > safe_spend:

        risk = "alto"

    elif usage_percentage >= 75:

        risk = "moderado"

    else:

        risk = "baixo"

    # -----------------------------------------
    # Quanto ultrapassa o limite
    # -----------------------------------------

    excess_amount = max(
        purchase_amount - safe_spend,
        0.0
    )

    # -----------------------------------------
    # Resultado final
    # -----------------------------------------

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