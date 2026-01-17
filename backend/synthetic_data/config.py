"""Configuration for synthetic data generation.

Contains thresholds, distributions, and parameters used across generators.
"""

from typing import Any

# =============================================================================
# Threshold Values for Edge Case Testing
# =============================================================================

THRESHOLDS: dict[str, list[int | float]] = {
    # MiCA significant ART threshold (Art. 43)
    "reserve_value_eur": [4_999_999, 5_000_000, 5_000_001, 100_000_000],
    # Token value tiers
    "total_token_value_eur": [999_999, 1_000_000, 5_000_000, 100_000_000],
    # Reserve ratio requirements
    "reserve_ratio": [0.99, 1.0, 1.01, 1.02],
    # Customer count thresholds
    "customer_count": [99, 100, 1000, 10000],
    # Transaction volume thresholds
    "daily_transaction_volume": [999_999, 1_000_000, 10_000_000],
    # Whitepaper page limits
    "whitepaper_pages": [1, 10, 50, 100],
}

# =============================================================================
# Scenario Categories and Distributions
# =============================================================================

SCENARIO_CATEGORIES: dict[str, dict[str, Any]] = {
    "happy_path": {
        "count": 150,
        "description": "Valid compliant scenarios",
        "characteristics": {
            "authorized": True,
            "has_whitepaper": True,
            "reserve_ratio": 1.02,
        },
    },
    "edge_case": {
        "count": 150,
        "description": "Threshold boundary scenarios",
        "characteristics": {
            "test_thresholds": True,
            "boundary_values": True,
        },
    },
    "negative": {
        "count": 100,
        "description": "Rule violation scenarios",
        "characteristics": {
            "authorized": False,
            "has_whitepaper": False,
            "reserve_ratio": 0.95,
        },
    },
    "cross_border": {
        "count": 75,
        "description": "Multi-jurisdiction scenarios",
        "characteristics": {
            "multi_jurisdiction": True,
            "target_markets": ["EU", "UK", "US", "CH", "SG"],
        },
    },
    "temporal": {
        "count": 25,
        "description": "Version-dependent scenarios",
        "characteristics": {
            "test_effective_dates": True,
            "version_transitions": True,
        },
    },
}

# =============================================================================
# Rule Generation Distributions
# =============================================================================

RULE_DISTRIBUTIONS: dict[str, dict[str, Any]] = {
    "mica_eu": {
        "count_range": (15, 20),
        "framework": "MiCA",
        "jurisdiction": "EU",
        "document_id": "mica_2023",
        "accuracy": "high",
        "articles": [
            "Art. 3 (Definitions)",
            "Art. 4 (Scope)",
            "Art. 16 (Whitepaper requirements)",
            "Art. 17 (Whitepaper content)",
            "Art. 36 (Authorization)",
            "Art. 38 (Reserve assets)",
            "Art. 43 (Significant ARTs)",
            "Art. 44 (EMT requirements)",
            "Art. 48 (Significant EMTs)",
            "Art. 59 (CASP authorization)",
            "Art. 60 (CASP obligations)",
            "Art. 86 (Market abuse)",
        ],
    },
    "fca_uk": {
        "count_range": (12, 15),
        "framework": "FCA Crypto",
        "jurisdiction": "UK",
        "document_id": "fca_crypto_2024",
        "accuracy": "high",
        "articles": [
            "COBS 4.12A.1 (Scope)",
            "COBS 4.12A.2 (Risk warnings)",
            "COBS 4.12A.3 (Promotions)",
            "COBS 4.12A.4 (Clear and fair)",
            "COBS 4.12A.5 (Cooling-off)",
            "PS22/10 (Financial promotions)",
            "FSMA 2023 (Gateway)",
        ],
    },
    "genius_us": {
        "count_range": (10, 15),
        "framework": "GENIUS Act",
        "jurisdiction": "US",
        "document_id": "genius_act_2025",
        "accuracy": "high",
        "note": "Enacted law (July 2025)",
        "articles": [
            "Sec. 101 (Definitions)",
            "Sec. 102 (Issuer requirements)",
            "Sec. 103 (Reserve requirements)",
            "Sec. 104 (Redemption rights)",
            "Sec. 105 (AML compliance)",
            "Sec. 201 (Registration)",
            "Sec. 202 (Reporting)",
        ],
    },
    "rwa_tokenization": {
        "count_range": (10, 15),
        "framework": "RWA Tokenization",
        "jurisdiction": "EU",
        "document_id": "rwa_eu_2025",
        "accuracy": "low",
        "note": "Hypothetical framework",
        "articles": [
            "Art. 1 (Scope)",
            "Art. 2 (Definitions)",
            "Art. 3 (Authorization)",
            "Art. 4 (Custody requirements)",
            "Art. 5 (Tokenization process)",
            "Art. 6 (Transfer restrictions)",
            "Art. 7 (Disclosure)",
        ],
    },
    "finma_ch": {
        "count_range": (8, 12),
        "framework": "FINMA DLT",
        "jurisdiction": "CH",
        "document_id": "finma_dlt_2021",
        "accuracy": "high",
        "articles": [
            "ICO Guidelines (Token classification)",
            "FMIA Art. 2(b) (Securities definition)",
            "FMIA Art. 73a-73f (DLT Trading Facilities)",
            "Banking Act Art. 16 (Custody segregation)",
            "AMLA (AML for payment tokens)",
            "Stablecoin Supplement (Classification)",
        ],
    },
    "mas_sg": {
        "count_range": (8, 12),
        "framework": "MAS PSA",
        "jurisdiction": "SG",
        "document_id": "psa_2019",
        "accuracy": "high",
        "articles": [
            "PSA Part 2 (DPT licensing)",
            "PSA Part 3 (Asset segregation)",
            "PSN02 (AML/CFT requirements)",
            "Consumer Protection Guidelines",
            "Stablecoin Framework (2023)",
            "FSMA (DTSP offshore)",
        ],
    },
}

# =============================================================================
# Rule Complexity Levels
# =============================================================================

RULE_COMPLEXITY: dict[str, dict[str, Any]] = {
    "simple": {
        "percentage": 0.30,
        "description": "Single condition -> single outcome",
        "max_depth": 1,
        "max_conditions": 2,
    },
    "medium": {
        "percentage": 0.50,
        "description": "2-3 nested conditions",
        "max_depth": 3,
        "max_conditions": 5,
    },
    "complex": {
        "percentage": 0.20,
        "description": "Multi-branch decision trees",
        "max_depth": 5,
        "max_conditions": 10,
    },
}

# =============================================================================
# Verification Tiers
# =============================================================================

VERIFICATION_TIERS: dict[int, dict[str, Any]] = {
    0: {
        "name": "Schema validation",
        "percentage": 0.40,
        "check_types": [
            "required_fields",
            "type_validation",
            "enum_values",
            "date_format",
        ],
    },
    1: {
        "name": "Semantic consistency",
        "percentage": 0.25,
        "check_types": [
            "text_similarity",
            "keyword_presence",
            "citation_accuracy",
        ],
    },
    2: {
        "name": "Cross-rule checks",
        "percentage": 0.15,
        "check_types": [
            "conflict_detection",
            "overlap_analysis",
            "gap_identification",
        ],
    },
    3: {
        "name": "Temporal consistency",
        "percentage": 0.10,
        "check_types": [
            "effective_date_ordering",
            "version_compatibility",
            "supersession_chains",
        ],
    },
    4: {
        "name": "External alignment",
        "percentage": 0.10,
        "check_types": [
            "source_text_match",
            "regulatory_update_check",
            "cross_reference_validation",
        ],
    },
}

# =============================================================================
# Confidence Score Ranges
# =============================================================================

CONFIDENCE_RANGES: dict[str, tuple[float, float]] = {
    "passing": (0.85, 0.99),
    "marginal": (0.70, 0.84),
    "failing": (0.40, 0.69),
}

# =============================================================================
# Ontology Dimensions (mirrors backend/core/ontology/types.py)
# =============================================================================

INSTRUMENT_TYPES: list[str] = [
    "art",
    "emt",
    "stablecoin",
    "utility_token",
    "other_crypto",
    "security_token",
    "nft",
]

ACTIVITY_TYPES: list[str] = [
    "public_offer",
    "admission_to_trading",
    "custody",
    "exchange",
    "execution",
    "placement",
    "transfer",
    "advice",
    "portfolio_management",
]

ACTOR_TYPES: list[str] = [
    "issuer",
    "offeror",
    "trading_platform",
    "custodian",
    "investor",
    "competent_authority",
    "other",
]

JURISDICTIONS: list[str] = ["EU", "UK", "US", "CH", "SG"]

# =============================================================================
# Decision Outcomes
# =============================================================================

DECISION_OUTCOMES: list[str] = [
    "authorized",
    "not_authorized",
    "requires_authorization",
    "exempt",
    "prohibited",
    "compliant",
    "non_compliant",
    "pending_review",
]

# =============================================================================
# Data Volume Targets
# =============================================================================

TARGET_VOLUMES: dict[str, int] = {
    "rules": 100,
    "scenarios": 500,
    "verification_results": 200,
    "verification_evidence": 400,
    "embeddings": 500,
    "graph_nodes": 500,
    "graph_edges": 1000,
}
