"""Risk alias resolution (Phase 4).

Maps common risk phrase variations to canonical risk names. Used by both rule
and LLM extractors to normalize risk names before storage.
"""

from __future__ import annotations

# Alias → canonical normalized risk name.
# These map common phrasings found in filings to a consistent normalized form.
_ALIAS_MAP: dict[str, str] = {
    # Supply chain
    "supplier dependence": "SUPPLY_CHAIN_DEPENDENCY",
    "supply chain dependency": "SUPPLY_CHAIN_DEPENDENCY",
    "vendor concentration": "SUPPLY_CHAIN_DEPENDENCY",
    "single source supplier": "SUPPLY_CHAIN_DEPENDENCY",
    "supply disruption": "SUPPLY_CHAIN_DISRUPTION",
    "supply chain disruption": "SUPPLY_CHAIN_DISRUPTION",
    "component shortage": "SUPPLY_CHAIN_DISRUPTION",
    # Regulatory
    "regulatory compliance": "REGULATORY_COMPLIANCE",
    "government regulation": "REGULATORY_COMPLIANCE",
    "regulatory change": "REGULATORY_CHANGE",
    "regulatory approval": "REGULATORY_APPROVAL",
    # Cybersecurity
    "cyber attack": "CYBERSECURITY_THREAT",
    "cyber threat": "CYBERSECURITY_THREAT",
    "data breach": "DATA_BREACH",
    "information security": "CYBERSECURITY_THREAT",
    "security breach": "DATA_BREACH",
    "ransomware": "CYBERSECURITY_THREAT",
    # Competition
    "competitive pressure": "COMPETITIVE_PRESSURE",
    "pricing competition": "COMPETITIVE_PRESSURE",
    "new market entrant": "COMPETITIVE_PRESSURE",
    # Technology
    "technological change": "TECHNOLOGY_DISRUPTION",
    "technology disruption": "TECHNOLOGY_DISRUPTION",
    "technology obsolescence": "TECHNOLOGY_DISRUPTION",
    # Liquidity
    "liquidity risk": "LIQUIDITY_RISK",
    "cash flow risk": "LIQUIDITY_RISK",
    "debt covenant": "DEBT_COVENANT_RISK",
    "refinancing risk": "REFINANCING_RISK",
    # Geopolitical
    "trade restriction": "GEOPOLITICAL_RISK",
    "political instability": "GEOPOLITICAL_RISK",
    "international conflict": "GEOPOLITICAL_RISK",
    "tariff risk": "GEOPOLITICAL_RISK",
    # Legal
    "litigation risk": "LITIGATION_RISK",
    "patent infringement": "IP_RISK",
    "intellectual property": "IP_RISK",
    "class action": "LITIGATION_RISK",
    # Environmental
    "climate change": "CLIMATE_RISK",
    "natural disaster": "NATURAL_DISASTER_RISK",
    "environmental regulation": "ENVIRONMENTAL_COMPLIANCE",
    "pandemic": "PANDEMIC_RISK",
    # Macroeconomic
    "economic downturn": "MACROECONOMIC_RISK",
    "recession risk": "MACROECONOMIC_RISK",
    "inflation risk": "INFLATION_RISK",
    "currency fluctuation": "CURRENCY_RISK",
    "foreign exchange": "CURRENCY_RISK",
    # Operational
    "key personnel": "KEY_PERSONNEL_RISK",
    "talent retention": "KEY_PERSONNEL_RISK",
    "operational disruption": "OPERATIONAL_DISRUPTION",
    "business continuity": "OPERATIONAL_DISRUPTION",
}


def resolve_risk_alias(name: str) -> str:
    """Resolve a risk name to its canonical normalized form.

    Returns the canonical name if found; otherwise normalizes the input to
    UPPER_SNAKE_CASE.
    """
    lower = name.strip().lower()
    if lower in _ALIAS_MAP:
        return _ALIAS_MAP[lower]
    # Fallback: generate a normalized name from the input
    return _normalize_risk_name(name)


def _normalize_risk_name(name: str) -> str:
    """Convert a risk name to UPPER_SNAKE_CASE canonical form."""
    cleaned = name.strip().upper()
    # Replace common separators with underscores
    for ch in ("-", "/", ".", ",", "'"):
        cleaned = cleaned.replace(ch, "_")
    # Collapse whitespace to underscores
    parts = cleaned.split()
    result = "_".join(p for p in parts if p)
    # Truncate to 128 chars (matches DB column)
    return result[:128]
