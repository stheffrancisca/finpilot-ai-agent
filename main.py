from app.tools.financial_metrics import (
    load_transactions,
    calculate_total_income,
    calculate_total_expenses,
    calculate_balance,
    expenses_by_category,
    calculate_safe_spend,
)

FILEPATH = "data/sample_transactions.csv"

df = load_transactions(FILEPATH)

income = calculate_total_income(df)
expenses = calculate_total_expenses(df)
balance = calculate_balance(df)
safe_data = calculate_safe_spend(df)

print("\nFINPILOT AI")
print("-" * 30)

print(f"Receitas: R$ {income:,.2f}")
print(f"Despesas: R$ {expenses:,.2f}")
print(f"Saldo: R$ {balance:,.2f}")

print("\nDespesas por categoria:")
print(expenses_by_category(df))

print("\nSAFE SPEND")
print("-" * 30)

print(f"Reserva recomendada: R$ {safe_data['reserve']:,.2f}")
print(f"Valor seguro para gastar: R$ {safe_data['safe_spend']:,.2f}")

purchase = float(input("\nQuanto você quer gastar? R$ "))

safe_spend = safe_data["safe_spend"]
current_balance = safe_data["balance"]

remaining_balance = current_balance - purchase
remaining_safe_spend = safe_spend - purchase

if safe_spend > 0:
    usage_percentage = (purchase / safe_spend) * 100
else:
    usage_percentage = 0


print("\nANALISE DA COMPRA")
print("-" * 30)

print(f"Valor da compra: R$ {purchase:,.2f}")
print(f"Saldo atual: R$ {current_balance:,.2f}")
print(f"Saldo apos a compra: R$ {remaining_balance:,.2f}")
print(f"Limite seguro atual: R$ {safe_spend:,.2f}")
print(f"Uso do limite seguro: {usage_percentage:.1f}%")

if purchase > safe_spend:
    print("\nRISCO: ALTO")
    print("Essa compra ultrapassa o limite seguro.")

    excess = purchase - safe_spend

    print(f"Voce ultrapassaria o limite em R$ {excess:,.2f}.")
    print(f"Limite recomendado: R$ {safe_spend:,.2f}")

elif usage_percentage >= 75:
    print("\nRISCO: MODERADO")
    print("A compra cabe no seu limite, mas consumiria grande parte do valor livre.")

    print(
        f"Restariam apenas R$ {remaining_safe_spend:,.2f} "
        "dentro do limite seguro."
    )

else:
    print("\nRISCO: BAIXO")
    print("A compra esta dentro do limite seguro.")

    print(
        f"Apos a compra, ainda restariam R$ "
        f"{remaining_safe_spend:,.2f} do seu limite seguro."
    )