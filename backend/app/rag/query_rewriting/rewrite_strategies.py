"""Query rewriting prompt templates and strategy instructions."""

from __future__ import annotations

from app.rag.query_rewriting.models import QueryClass

STRATEGY_PROMPTS = {
    QueryClass.FINANCIAL_METRIC: (
        "Focus on extracting relevant financial terminology, metrics, and statement concepts. "
        "Rewrite the query to include terms like revenue, profit, cash flow, operating margin, capex, balance sheet items. "
        "Example: 'How profitable is Tesla?' -> 'Tesla net profit operating margin EBITDA net income cash flow performance'"
    ),
    QueryClass.RISK: (
        "Focus on risk factors, vulnerabilities, and potential business disruptions. "
        "Include terminology like supply chain risk, logistics concentration, regulatory compliance, legal liability, cybersecurity, and market competition. "
        "Example: 'Tesla supply chain concerns' -> 'Supply chain risk supplier concentration manufacturing dependency logistics disruption'"
    ),
    QueryClass.TONE: (
        "Focus on qualitative language, sentiment indicators, confidence expressions, and hedging verbs. "
        "Include terms like management discussion, prepared remarks, optimism, uncertainty, transcript sentiment. "
        "Example: 'What is Elon Musk's outlook?' -> 'management outlook confidence levels sentiment analysis cautious optimistic transcripts'"
    ),
    QueryClass.GUIDANCE: (
        "Focus on forward-looking statements, guidance forecasts, expectations, and future fiscal projections. "
        "Include terms like outlook guidance, revenue projection, future targets, estimated growth. "
        "Example: 'What did Apple predict for next year?' -> 'forward guidance outlook projections future targets expectations forecast'"
    ),
    QueryClass.GENERAL: (
        "Focus on corporate overview, business model, product details, and general operational facts. "
        "Include terms like company profile, business operations, core products, key executives. "
        "Example: 'What does Microsoft do?' -> 'Microsoft business model product overview services profile core operations'"
    ),
    QueryClass.MIXED: (
        "The query contains multiple components. Break it down into sub-queries if applicable, and generate a blended "
        "rewritten query covering both financial metrics, risks, or qualitative discussions."
    )
}
