import os
from typing import Any

from mcp.server import MCPServer


# =========================================================
# SERVIDOR MCP
# =========================================================

mcp = MCPServer(
    "FinPilot MCP"
)


# =========================================================
# AUXILIARES
# =========================================================

def round_money(value: float) -> float:
    return round(
        float(value or 0),
        2
    )


def safe_percentage(
    numerator: float,
    denominator: float,
) -> float:

    if not denominator:
        return 0.0

    return round(
        (
            float(numerator)
            / float(denominator)
        )
        * 100,
        2,
    )


# =========================================================
# 1. RESUMO FINANCEIRO
# =========================================================

@mcp.tool()
def financial_summary(
    monthly_income: float,
    purchases: float,
    refunds: float = 0.0,
    reserve_percentage: float = 0.10,
) -> dict[str, Any]:
    """
    Calcula um resumo financeiro determinístico.

    Use quando o usuário pedir:
    - resumo financeiro
    - saldo
    - gastos líquidos
    - limite seguro
    - situação financeira
    - comprometimento da renda

    Args:
        monthly_income:
            Renda líquida mensal do usuário.

        purchases:
            Total de compras ou despesas.

        refunds:
            Total de devoluções ou estornos.

        reserve_percentage:
            Percentual da renda destinado à reserva.
            O padrão é 10%.

    Returns:
        Principais métricas financeiras.
    """

    monthly_income = float(
        monthly_income or 0
    )

    purchases = float(
        purchases or 0
    )

    refunds = float(
        refunds or 0
    )

    reserve_percentage = float(
        reserve_percentage or 0.10
    )

    net_expenses = max(
        purchases - refunds,
        0.0
    )

    balance = (
        monthly_income
        - net_expenses
    )

    reserve = (
        monthly_income
        * reserve_percentage
    )

    safe_spend = max(
        balance - reserve,
        0.0
    )

    expense_ratio = safe_percentage(
        net_expenses,
        monthly_income,
    )

    return {
        "status":
            "success",

        "monthly_income":
            round_money(
                monthly_income
            ),

        "purchases":
            round_money(
                purchases
            ),

        "refunds":
            round_money(
                refunds
            ),

        "net_expenses":
            round_money(
                net_expenses
            ),

        "balance":
            round_money(
                balance
            ),

        "reserve":
            round_money(
                reserve
            ),

        "safe_spend":
            round_money(
                safe_spend
            ),

        "expense_ratio_percent":
            expense_ratio,
    }


# =========================================================
# 2. MAIOR CATEGORIA
# =========================================================

@mcp.tool()
def top_expense_category(
    expenses_by_category: dict[str, float],
) -> dict[str, Any]:
    """
    Identifica a categoria com maior gasto.

    Args:
        expenses_by_category:
            Dicionário contendo categoria e valor.
            Exemplo:
            {
                "Transporte": 304.20,
                "Alimentação": 77.88
            }

    Returns:
        Categoria de maior gasto e valor.
    """

    if not expenses_by_category:

        return {
            "status":
                "no_data",

            "message":
                "Nenhuma categoria de gasto foi informada.",
        }

    cleaned = {}

    for category, value in (
        expenses_by_category.items()
    ):

        try:

            cleaned[
                str(category)
            ] = float(
                value or 0
            )

        except Exception:

            continue

    if not cleaned:

        return {
            "status":
                "no_data",

            "message":
                "Nenhum valor de gasto válido foi informado.",
        }

    top_category = max(
        cleaned,
        key=cleaned.get,
    )

    top_value = cleaned[
        top_category
    ]

    total = sum(
        cleaned.values()
    )

    share = safe_percentage(
        top_value,
        total,
    )

    return {
        "status":
            "success",

        "category":
            top_category,

        "amount":
            round_money(
                top_value
            ),

        "share_of_expenses_percent":
            share,

        "total_expenses":
            round_money(
                total
            ),
    }


# =========================================================
# 3. IMPACTO DE COMPRA
# =========================================================

@mcp.tool()
def purchase_impact(
    monthly_income: float,
    current_expenses: float,
    purchase_amount: float,
    refunds: float = 0.0,
    reserve_percentage: float = 0.10,
) -> dict[str, Any]:
    """
    Simula o impacto financeiro de uma compra.

    O FinPilot não executa compras, PIX,
    pagamentos ou transferências.

    Args:
        monthly_income:
            Renda mensal líquida.

        current_expenses:
            Gastos atuais.

        purchase_amount:
            Valor da compra que o usuário quer simular.

        refunds:
            Devoluções ou estornos existentes.

        reserve_percentage:
            Percentual reservado.

    Returns:
        Saldo antes e depois da compra,
        limite seguro e nível de impacto.
    """

    monthly_income = float(
        monthly_income or 0
    )

    current_expenses = float(
        current_expenses or 0
    )

    purchase_amount = float(
        purchase_amount or 0
    )

    refunds = float(
        refunds or 0
    )

    reserve_percentage = float(
        reserve_percentage or 0.10
    )

    net_expenses = max(
        current_expenses - refunds,
        0.0,
    )

    current_balance = (
        monthly_income
        - net_expenses
    )

    reserve = (
        monthly_income
        * reserve_percentage
    )

    safe_spend = max(
        current_balance
        - reserve,
        0.0,
    )

    balance_after_purchase = (
        current_balance
        - purchase_amount
    )

    if safe_spend <= 0:

        impact_level = "high"

        safe_spend_usage = 100.0

    else:

        safe_spend_usage = (
            purchase_amount
            / safe_spend
        ) * 100

        if safe_spend_usage <= 50:

            impact_level = "low"

        elif safe_spend_usage <= 80:

            impact_level = "moderate"

        else:

            impact_level = "high"

    return {
        "status":
            "success",

        "purchase_amount":
            round_money(
                purchase_amount
            ),

        "current_balance":
            round_money(
                current_balance
            ),

        "reserve":
            round_money(
                reserve
            ),

        "safe_spend":
            round_money(
                safe_spend
            ),

        "balance_after_purchase":
            round_money(
                balance_after_purchase
            ),

        "safe_spend_usage_percent":
            round(
                safe_spend_usage,
                2,
            ),

        "impact_level":
            impact_level,

        "transaction_executed":
            False,
    }


# =========================================================
# 4. FORECAST
# =========================================================

@mcp.tool()
def month_end_forecast(
    monthly_income: float,
    current_expenses: float,
    days_observed: int,
    days_in_month: int = 30,
    refunds: float = 0.0,
) -> dict[str, Any]:
    """
    Projeta o saldo para o fim do mês.

    Args:
        monthly_income:
            Renda mensal.

        current_expenses:
            Gastos observados até agora.

        days_observed:
            Quantidade de dias já observados.

        days_in_month:
            Quantidade total de dias no mês.

        refunds:
            Devoluções ou estornos.

    Returns:
        Média diária,
        despesas projetadas
        e saldo projetado.
    """

    monthly_income = float(
        monthly_income or 0
    )

    current_expenses = float(
        current_expenses or 0
    )

    refunds = float(
        refunds or 0
    )

    days_observed = max(
        int(
            days_observed or 0
        ),
        1,
    )

    days_in_month = max(
        int(
            days_in_month or 30
        ),
        days_observed,
    )

    net_expenses = max(
        current_expenses
        - refunds,
        0.0,
    )

    average_daily_expense = (
        net_expenses
        / days_observed
    )

    projected_month_expenses = (
        average_daily_expense
        * days_in_month
    )

    projected_balance = (
        monthly_income
        - projected_month_expenses
    )

    days_remaining = max(
        days_in_month
        - days_observed,
        0,
    )

    return {
        "status":
            "success",

        "days_observed":
            days_observed,

        "days_remaining":
            days_remaining,

        "average_daily_expense":
            round_money(
                average_daily_expense
            ),

        "projected_month_expenses":
            round_money(
                projected_month_expenses
            ),

        "projected_month_end_balance":
            round_money(
                projected_balance
            ),
    }


# =========================================================
# 5. GASTOS RECORRENTES
# =========================================================

@mcp.tool()
def recurring_expenses(
    transactions: list[dict[str, Any]],
    minimum_occurrences: int = 2,
) -> dict[str, Any]:
    """
    Identifica descrições que aparecem repetidamente.

    Args:
        transactions:
            Lista de transações.
            Cada item deve conter:
            description e amount.

        minimum_occurrences:
            Número mínimo de ocorrências para considerar recorrente.

    Returns:
        Lista de gastos recorrentes.
    """

    if not transactions:

        return {
            "status":
                "no_data",

            "recurring_expenses":
                [],
        }

    grouped = {}

    for transaction in transactions:

        description = str(
            transaction.get(
                "description",
                ""
            )
        ).strip()

        if not description:

            continue

        try:

            amount = float(
                transaction.get(
                    "amount",
                    0
                )
                or 0
            )

        except Exception:

            amount = 0.0

        key = (
            description
            .lower()
            .strip()
        )

        if key not in grouped:

            grouped[
                key
            ] = {
                "description":
                    description,

                "occurrences":
                    0,

                "total_amount":
                    0.0,
            }

        grouped[
            key
        ][
            "occurrences"
        ] += 1

        grouped[
            key
        ][
            "total_amount"
        ] += amount

    recurring = []

    for item in grouped.values():

        if (
            item[
                "occurrences"
            ]
            >= minimum_occurrences
        ):

            item[
                "total_amount"
            ] = round_money(
                item[
                    "total_amount"
                ]
            )

            item[
                "average_amount"
            ] = round_money(
                item[
                    "total_amount"
                ]
                / item[
                    "occurrences"
                ]
            )

            recurring.append(
                item
            )

    recurring = sorted(
        recurring,
        key=lambda item: (
            item[
                "total_amount"
            ]
        ),
        reverse=True,
    )

    return {
        "status":
            "success",

        "count":
            len(
                recurring
            ),

        "recurring_expenses":
            recurring,
    }


# =========================================================
# 6. ANOMALIAS
# =========================================================

@mcp.tool()
def spending_anomalies(
    transactions: list[dict[str, Any]],
    multiplier: float = 2.0,
) -> dict[str, Any]:
    """
    Identifica transações muito acima da média.

    Args:
        transactions:
            Lista de transações contendo
            description, category e amount.

        multiplier:
            Multiplicador da média usado
            como limite de anomalia.

    Returns:
        Transações acima do limite.
    """

    if not transactions:

        return {
            "status":
                "no_data",

            "anomalies":
                [],
        }

    valid = []

    for transaction in transactions:

        try:

            amount = float(
                transaction.get(
                    "amount",
                    0
                )
                or 0
            )

        except Exception:

            continue

        if amount <= 0:

            continue

        valid.append(
            {
                "description":
                    str(
                        transaction.get(
                            "description",
                            ""
                        )
                    ),

                "category":
                    str(
                        transaction.get(
                            "category",
                            "Outros"
                        )
                    ),

                "amount":
                    amount,
            }
        )

    if not valid:

        return {
            "status":
                "no_data",

            "anomalies":
                [],
        }

    average = (
        sum(
            item[
                "amount"
            ]
            for item in valid
        )
        / len(
            valid
        )
    )

    threshold = (
        average
        * float(
            multiplier
        )
    )

    anomalies = []

    for item in valid:

        if (
            item[
                "amount"
            ]
            > threshold
        ):

            anomalies.append(
                {
                    "description":
                        item[
                            "description"
                        ],

                    "category":
                        item[
                            "category"
                        ],

                    "amount":
                        round_money(
                            item[
                                "amount"
                            ]
                        ),

                    "average_amount":
                        round_money(
                            average
                        ),

                    "difference_from_average":
                        round_money(
                            item[
                                "amount"
                            ]
                            - average
                        ),
                }
            )

    anomalies = sorted(
        anomalies,
        key=lambda item: (
            item[
                "amount"
            ]
        ),
        reverse=True,
    )

    return {
        "status":
            "success",

        "average_transaction":
            round_money(
                average
            ),

        "threshold":
            round_money(
                threshold
            ),

        "count":
            len(
                anomalies
            ),

        "anomalies":
            anomalies,
    }


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "8080",
        )
    )

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        json_response=True,
        stateless_http=True,
    )