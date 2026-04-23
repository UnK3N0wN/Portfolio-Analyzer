"""
ai/utils.py
Helper functions to prepare portfolio data for AI analysis.
"""

def get_portfolio_summary(portfolio):
    """Convert portfolio object into a clean text summary for the LLM."""
    holdings = portfolio.holdings.all()

    if not holdings:
        return "The portfolio is currently empty."

    lines = [f"Portfolio: {portfolio.name}"]
    lines.append(f"Total Value:    ${portfolio.total_value():.2f}")
    lines.append(f"Total Invested: ${portfolio.total_invested():.2f}")
    lines.append(f"Total P/L:      ${portfolio.total_profit_loss():.2f} ({portfolio.profit_loss_percent():.2f}%)")
    lines.append("")
    lines.append("Holdings:")

    for h in holdings:
        lines.append(
            f"  - {h.symbol} ({h.name}): "
            f"{h.quantity} units @ avg ${float(h.avg_price):.2f}, "
            f"current ${float(h.current_price):.2f}, "
            f"P/L: ${h.profit_loss():.2f} ({h.profit_loss_percent():.2f}%)"
        )

    recent = portfolio.transactions.all()[:5]
    if recent:
        lines.append("")
        lines.append("Recent Transactions:")
        for t in recent:
            lines.append(
                f"  - {t.transaction_type.upper()} {t.quantity} {t.symbol} "
                f"@ ${float(t.price):.2f} on {t.date.strftime('%Y-%m-%d')}"
            )

    return "\n".join(lines)


def format_currency(value):
    """Format a number as currency string."""
    return f"${float(value):,.2f}"


def get_asset_allocation(portfolio):
    """Return asset allocation breakdown."""
    holdings = portfolio.holdings.all()
    total    = portfolio.total_value()

    if total == 0:
        return []

    allocation = []
    for h in holdings:
        pct = (h.current_value() / total) * 100
        allocation.append({
            'symbol':     h.symbol,
            'name':       h.name,
            'asset_type': h.asset_type,
            'value':      h.current_value(),
            'percent':    round(pct, 2),
        })

    return sorted(allocation, key=lambda x: x['value'], reverse=True)