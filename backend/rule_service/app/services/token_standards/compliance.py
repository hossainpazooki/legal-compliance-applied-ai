"""
Token standard compliance checker for regulatory classification.

Implements SEC Howey Test analysis and GENIUS Act stablecoin provisions
for ERC-20, ERC-721, BEP-20, SPL, and other token standards.

References:
- SEC Framework for "Investment Contract" Analysis of Digital Assets
- GENIUS Act (Guiding and Establishing National Innovation for US Stablecoins)
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TokenStandard(str, Enum):
    """Blockchain token standards."""
    ERC_20 = "erc_20"       # Ethereum fungible token
    ERC_721 = "erc_721"     # Ethereum NFT
    ERC_1155 = "erc_1155"   # Ethereum multi-token
    BEP_20 = "bep_20"       # BNB Chain fungible
    SPL = "spl"             # Solana Program Library
    TRC_20 = "trc_20"       # Tron fungible


class TokenClassification(str, Enum):
    """Regulatory classification for digital assets."""
    PAYMENT_STABLECOIN = "payment_stablecoin"
    SECURITY_TOKEN = "security_token"
    UTILITY_TOKEN = "utility_token"
    NFT = "nft"
    GOVERNANCE_TOKEN = "governance_token"
    COMMODITY_TOKEN = "commodity_token"


class HoweyProng(str, Enum):
    """The four prongs of the SEC Howey Test."""
    INVESTMENT_OF_MONEY = "investment_of_money"
    COMMON_ENTERPRISE = "common_enterprise"
    EXPECTATION_OF_PROFITS = "expectation_of_profits"
    EFFORTS_OF_OTHERS = "efforts_of_others"


class HoweyTestResult(BaseModel):
    """
    Result of SEC Howey Test analysis for security classification.

    A token is classified as a security if ALL four prongs are satisfied.
    """
    investment_of_money: bool = Field(
        ...,
        description="Whether purchasers invested money or other consideration"
    )
    common_enterprise: bool = Field(
        ...,
        description="Whether there is horizontal or vertical commonality"
    )
    expectation_of_profits: bool = Field(
        ...,
        description="Whether purchasers have reasonable expectation of profits"
    )
    efforts_of_others: bool = Field(
        ...,
        description="Whether profits derive from efforts of promoter or third party"
    )

    # Analysis details
    analysis_notes: list[str] = Field(default_factory=list)
    decentralization_factor: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Degree of decentralization (0=centralized, 1=fully decentralized)"
    )

    @property
    def is_security(self) -> bool:
        """Token is a security if all four Howey prongs are met."""
        return all([
            self.investment_of_money,
            self.common_enterprise,
            self.expectation_of_profits,
            self.efforts_of_others,
        ])

    @property
    def prongs_satisfied(self) -> int:
        """Count of Howey prongs satisfied."""
        return sum([
            self.investment_of_money,
            self.common_enterprise,
            self.expectation_of_profits,
            self.efforts_of_others,
        ])


class GeniusActAnalysis(BaseModel):
    """
    Analysis under the GENIUS Act for payment stablecoin classification.

    The GENIUS Act establishes a federal framework for payment stablecoins,
    requiring 1:1 reserve backing and prohibiting algorithmic mechanisms.
    """
    is_payment_stablecoin: bool = Field(
        ...,
        description="Whether token qualifies as payment stablecoin under GENIUS Act"
    )
    backed_by_permitted_assets: bool = Field(
        ...,
        description="Whether reserves consist of permitted assets (USD, Treasuries, etc.)"
    )
    has_one_to_one_backing: bool = Field(
        ...,
        description="Whether token maintains 1:1 reserve ratio"
    )
    is_algorithmic: bool = Field(
        ...,
        description="Whether token uses algorithmic stabilization (prohibited)"
    )
    issuer_type: str = Field(
        ...,
        description="Type of issuer: bank, non_bank_qualified, foreign"
    )
    reserve_transparency: bool = Field(
        ...,
        description="Whether issuer provides required reserve attestations"
    )

    # Compliance determination
    compliance_status: str = Field(
        ...,
        description="compliant, non_compliant, requires_registration"
    )
    compliance_notes: list[str] = Field(default_factory=list)

    @property
    def meets_genius_requirements(self) -> bool:
        """Check if stablecoin meets core GENIUS Act requirements."""
        return (
            self.is_payment_stablecoin
            and self.backed_by_permitted_assets
            and self.has_one_to_one_backing
            and not self.is_algorithmic
            and self.reserve_transparency
        )


class TokenComplianceResult(BaseModel):
    """Comprehensive compliance analysis result for a digital asset."""
    standard: TokenStandard
    classification: TokenClassification
    requires_sec_registration: bool
    genius_act_applicable: bool

    # Detailed analysis
    howey_analysis: Optional[HoweyTestResult] = None
    genius_analysis: Optional[GeniusActAnalysis] = None

    # Compliance requirements
    compliance_requirements: list[str] = Field(default_factory=list)
    regulatory_risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)

    # Jurisdictional notes
    sec_jurisdiction: bool = Field(
        False,
        description="Falls under SEC jurisdiction"
    )
    cftc_jurisdiction: bool = Field(
        False,
        description="Falls under CFTC jurisdiction"
    )


def apply_howey_test(
    *,
    investment_of_money: bool,
    common_enterprise: bool,
    expectation_of_profits: bool,
    efforts_of_others: bool,
    decentralization_score: float = 0.0,
    is_functional_network: bool = False,
) -> HoweyTestResult:
    """
    Apply SEC Howey Test to determine security classification.

    Args:
        investment_of_money: Purchasers invested money or consideration
        common_enterprise: Horizontal or vertical commonality exists
        expectation_of_profits: Purchasers expect profits from investment
        efforts_of_others: Profits depend on promoter/third party efforts
        decentralization_score: Degree of decentralization (0-1)
        is_functional_network: Whether network is functional and decentralized

    Returns:
        HoweyTestResult with analysis
    """
    notes = []

    # Sufficient decentralization may negate "efforts of others" prong
    # Per SEC guidance, once network is sufficiently decentralized,
    # purchasers no longer rely on issuer's efforts
    adjusted_efforts_of_others = efforts_of_others
    if decentralization_score >= 0.8 and is_functional_network:
        adjusted_efforts_of_others = False
        notes.append(
            "Network deemed sufficiently decentralized - "
            "'efforts of others' prong not satisfied per SEC guidance"
        )

    if expectation_of_profits and not efforts_of_others:
        notes.append(
            "Profit expectation exists but not derived from others' efforts - "
            "may qualify as commodity rather than security"
        )

    return HoweyTestResult(
        investment_of_money=investment_of_money,
        common_enterprise=common_enterprise,
        expectation_of_profits=expectation_of_profits,
        efforts_of_others=adjusted_efforts_of_others,
        analysis_notes=notes,
        decentralization_factor=decentralization_score,
    )


def analyze_genius_act_compliance(
    *,
    is_stablecoin: bool,
    pegged_currency: str,
    reserve_assets: list[str],
    reserve_ratio: float,
    uses_algorithmic_mechanism: bool,
    issuer_charter_type: str,
    has_reserve_attestation: bool,
    attestation_frequency_days: int = 0,
) -> GeniusActAnalysis:
    """
    Analyze compliance with GENIUS Act stablecoin provisions.

    Args:
        is_stablecoin: Whether token is designed as stablecoin
        pegged_currency: Currency peg (USD, EUR, etc.)
        reserve_assets: List of reserve asset types
        reserve_ratio: Reserve-to-liability ratio
        uses_algorithmic_mechanism: Whether uses algorithmic stabilization
        issuer_charter_type: bank, non_bank_qualified, foreign
        has_reserve_attestation: Whether attestations are provided
        attestation_frequency_days: Days between attestations

    Returns:
        GeniusActAnalysis with compliance status
    """
    notes = []

    # Check if this is a USD-pegged payment stablecoin
    is_payment_stablecoin = is_stablecoin and pegged_currency == "USD"

    # Permitted reserve assets under GENIUS Act
    permitted_assets = {
        "usd_cash",
        "us_treasury_bills",
        "us_treasury_notes",
        "reverse_repo",
        "money_market_funds",
        "insured_deposits",
    }
    reserve_set = set(ra.lower().replace(" ", "_") for ra in reserve_assets)
    backed_by_permitted = reserve_set.issubset(permitted_assets)

    if not backed_by_permitted:
        unpermitted = reserve_set - permitted_assets
        notes.append(f"Reserve contains non-permitted assets: {unpermitted}")

    # 1:1 backing requirement
    has_one_to_one = reserve_ratio >= 1.0
    if not has_one_to_one:
        notes.append(f"Reserve ratio {reserve_ratio:.2%} is below 1:1 requirement")

    # Algorithmic stablecoins are prohibited
    if uses_algorithmic_mechanism:
        notes.append("Algorithmic stabilization mechanism prohibited under GENIUS Act")

    # Reserve transparency requirements
    reserve_transparent = has_reserve_attestation and attestation_frequency_days <= 30
    if not reserve_transparent:
        notes.append("Monthly reserve attestation required")

    # Determine compliance status
    if not is_payment_stablecoin:
        compliance_status = "not_applicable"
    elif uses_algorithmic_mechanism:
        compliance_status = "prohibited"
    elif backed_by_permitted and has_one_to_one and reserve_transparent:
        compliance_status = "compliant"
    else:
        compliance_status = "requires_remediation"

    return GeniusActAnalysis(
        is_payment_stablecoin=is_payment_stablecoin,
        backed_by_permitted_assets=backed_by_permitted,
        has_one_to_one_backing=has_one_to_one,
        is_algorithmic=uses_algorithmic_mechanism,
        issuer_type=issuer_charter_type,
        reserve_transparency=reserve_transparent,
        compliance_status=compliance_status,
        compliance_notes=notes,
    )


def analyze_token_compliance(
    *,
    standard: TokenStandard,
    has_profit_expectation: bool,
    is_decentralized: bool,
    backed_by_fiat: bool,
    # Howey test inputs
    investment_of_money: bool = True,
    common_enterprise: bool = True,
    efforts_of_promoter: bool = True,
    decentralization_score: float = 0.0,
    is_functional_network: bool = False,
    # GENIUS Act inputs
    is_stablecoin: bool = False,
    pegged_currency: str = "USD",
    reserve_assets: Optional[list[str]] = None,
    reserve_ratio: float = 1.0,
    uses_algorithmic_mechanism: bool = False,
    issuer_charter_type: str = "non_bank_qualified",
    has_reserve_attestation: bool = False,
    attestation_frequency_days: int = 30,
) -> TokenComplianceResult:
    """
    Comprehensive token compliance analysis for US regulatory requirements.

    Applies SEC Howey Test and GENIUS Act provisions to determine
    regulatory classification and compliance requirements.

    Args:
        standard: Token standard (ERC-20, SPL, etc.)
        has_profit_expectation: Whether purchasers expect profits
        is_decentralized: Whether network is decentralized
        backed_by_fiat: Whether backed by fiat currency
        ... (additional parameters for detailed analysis)

    Returns:
        TokenComplianceResult with full analysis
    """
    compliance_requirements = []
    regulatory_risks = []
    recommended_actions = []

    # Apply Howey Test
    howey_result = apply_howey_test(
        investment_of_money=investment_of_money,
        common_enterprise=common_enterprise,
        expectation_of_profits=has_profit_expectation,
        efforts_of_others=efforts_of_promoter,
        decentralization_score=decentralization_score,
        is_functional_network=is_functional_network,
    )

    # Apply GENIUS Act analysis for stablecoins
    genius_result = None
    if is_stablecoin or backed_by_fiat:
        genius_result = analyze_genius_act_compliance(
            is_stablecoin=is_stablecoin or backed_by_fiat,
            pegged_currency=pegged_currency,
            reserve_assets=reserve_assets or ["usd_cash"],
            reserve_ratio=reserve_ratio,
            uses_algorithmic_mechanism=uses_algorithmic_mechanism,
            issuer_charter_type=issuer_charter_type,
            has_reserve_attestation=has_reserve_attestation,
            attestation_frequency_days=attestation_frequency_days,
        )

    # Determine classification
    if standard == TokenStandard.ERC_721:
        classification = TokenClassification.NFT
        sec_jurisdiction = False
        cftc_jurisdiction = False
    elif genius_result and genius_result.is_payment_stablecoin:
        classification = TokenClassification.PAYMENT_STABLECOIN
        sec_jurisdiction = False
        cftc_jurisdiction = False
        if genius_result.compliance_status != "compliant":
            compliance_requirements.append("Obtain GENIUS Act compliant status")
            regulatory_risks.append("Operating as non-compliant stablecoin")
    elif howey_result.is_security:
        classification = TokenClassification.SECURITY_TOKEN
        sec_jurisdiction = True
        cftc_jurisdiction = False
        compliance_requirements.extend([
            "Register with SEC or qualify for exemption",
            "Comply with Securities Act of 1933",
            "File periodic reports under Exchange Act",
        ])
        regulatory_risks.append("Unregistered securities offering liability")
    elif has_profit_expectation and not howey_result.is_security:
        # Commodity treatment - profits expected but not from others' efforts
        classification = TokenClassification.COMMODITY_TOKEN
        sec_jurisdiction = False
        cftc_jurisdiction = True
        compliance_requirements.append("Comply with CFTC anti-fraud provisions")
    else:
        classification = TokenClassification.UTILITY_TOKEN
        sec_jurisdiction = False
        cftc_jurisdiction = False

    # SEC registration required if classified as security
    requires_sec = classification == TokenClassification.SECURITY_TOKEN

    # GENIUS Act applicable for payment stablecoins
    genius_applicable = (
        genius_result is not None
        and genius_result.is_payment_stablecoin
    )

    # Build recommended actions
    if requires_sec:
        recommended_actions.append("Consult securities counsel for registration options")
        recommended_actions.append("Consider Regulation D or Regulation A+ exemptions")
    if genius_applicable and genius_result.compliance_status != "compliant":
        recommended_actions.append("Work with qualified issuer to achieve GENIUS Act compliance")

    return TokenComplianceResult(
        standard=standard,
        classification=classification,
        requires_sec_registration=requires_sec,
        genius_act_applicable=genius_applicable,
        howey_analysis=howey_result,
        genius_analysis=genius_result,
        compliance_requirements=compliance_requirements,
        regulatory_risks=regulatory_risks,
        recommended_actions=recommended_actions,
        sec_jurisdiction=sec_jurisdiction,
        cftc_jurisdiction=cftc_jurisdiction,
    )
