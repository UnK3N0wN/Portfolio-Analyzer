"""
ai/llm.py
Optimized LLM integration using Groq API with Llama models.
Token-efficient + production-ready version.
"""

import os
from django.conf import settings

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


# ── Models ────────────────────────────────────────────────────────────────
FAST_MODEL  = "llama-3.1-8b-instant"       # Fast + cheap
SMART_MODEL = "llama-3.3-70b-versatile"    # Deep analysis


# ── Optimized System Prompt (SHORT = LESS TOKENS) ─────────────────────────
SYSTEM_PROMPT = """You are PortfolioAI. Give concise financial insights.
Instructions:
- Use plain text only (NO Markdown like **, ##, or #).
- Use simple dashes (-) for lists.
- Use ALL CAPS for headers and stock tickers.
- Max 3 bullet points per section.
Required Footer: Invest at your own risk. Past performance != future results."""


# ── Groq Client ───────────────────────────────────────────────────────────
def get_groq_client():
    api_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
    if not api_key or not GROQ_AVAILABLE:
        return None
    return Groq(api_key=api_key)


# ── Optional: Compress Portfolio Context ──────────────────────────────────
def compress_portfolio(portfolio_context: str, max_chars: int = 800) -> str:
    """
    Reduce token usage by trimming large portfolio inputs.
    We can later replace this with smarter summarization.
    """
    if not portfolio_context:
        return ""

    if len(portfolio_context) <= max_chars:
        return portfolio_context

    return portfolio_context[:max_chars] + "\n... (truncated)"


# ── Core LLM Call ─────────────────────────────────────────────────────────
def ask_llm(user_message, portfolio_context="", model=FAST_MODEL):
    """
    Send message to Groq LLM with optimized token usage.
    """

    client = get_groq_client()

    if not client:
        return "⚠️ AI service unavailable. Add GROQ_API_KEY in .env"

    # Compress portfolio to save tokens
    portfolio_context = compress_portfolio(portfolio_context)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Add portfolio context ONLY if exists
    if portfolio_context:
        messages.append({
            "role": "user",
            "content": f"Portfolio summary:\n{portfolio_context}"
        })

    # Add actual user query
    messages.append({
        "role": "user",
        "content": user_message
    })

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=400,      # Reduced from 1024
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Error: {str(e)}"


# ── Preset Analysis Functions (SMART MODEL) ───────────────────────────────
def analyze_portfolio(portfolio_context):
    return ask_llm(
        "Analyze my portfolio: performance, diversification, top & worst assets, and give 3 actions.",
        portfolio_context,
        model=SMART_MODEL
    )


def get_risk_assessment(portfolio_context):
    return ask_llm(
        "Assess portfolio risk: concentration, diversification, volatility, and mitigation steps.",
        portfolio_context,
        model=SMART_MODEL
    )


def get_buy_sell_suggestions(portfolio_context):
    return ask_llm(
        "Give buy/sell suggestions based on performance, diversification gaps, and trends.",
        portfolio_context,
        model=SMART_MODEL
    )


# ── Optional: Token Estimator (Rough) ─────────────────────────────────────
def estimate_tokens(text: str) -> int:
    """
    Rough token estimator: 1 token ≈ 4 characters
    """
    if not text:
        return 0
    return len(text) // 4