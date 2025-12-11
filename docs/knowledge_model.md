# Knowledge Model

This document describes the ontology and knowledge representation used in the Droit regulatory reasoning system.

## Overview

The knowledge model transforms legal text into structured, executable knowledge. It represents regulatory concepts as typed objects with explicit relationships, enabling:

- **Formal reasoning** over legal requirements
- **Traceable decisions** linked to source provisions
- **Version-controlled rules** with effective dates
- **Explicit interpretation** documentation

## Core Ontology

### Entity Types

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LEGAL TEXT LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│  Provision                                                          │
│  ├── type: definition | scope | requirement | prohibition | ...     │
│  ├── source: SourceReference                                        │
│  └── text: string                                                   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ extracts
┌─────────────────────────────────────────────────────────────────────┐
│                       NORMATIVE CONTENT                             │
├─────────────────────────────────────────────────────────────────────┤
│  Obligation    "MUST do X"                                          │
│  Permission    "MAY do X"                                           │
│  Prohibition   "MUST NOT do X"                                      │
│  └── Each links back to source Provision                            │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ applies to
┌─────────────────────────────────────────────────────────────────────┐
│                       REGULATED DOMAIN                              │
├─────────────────────────────────────────────────────────────────────┤
│  Actor         issuer | investor | trading_platform | ...           │
│  Instrument    art | emt | stablecoin | utility_token | ...         │
│  Activity      public_offer | custody | exchange | ...              │
└─────────────────────────────────────────────────────────────────────┘
```

### Type Definitions

#### Actor
A regulated entity or person.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| type | ActorType | issuer, offeror, trading_platform, custodian, investor, competent_authority |
| jurisdiction | string | ISO country code or "EU" |
| attributes | dict | Additional properties (e.g., is_credit_institution) |

#### Instrument
A financial instrument or crypto-asset.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| type | InstrumentType | art, emt, stablecoin, utility_token, security_token, nft, other_crypto |
| reference_asset | string | For ARTs: the asset(s) referenced |
| issuer_id | string | Link to issuing Actor |

#### Activity
A regulated activity.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| type | ActivityType | public_offer, admission_to_trading, custody, exchange, execution, ... |
| actor_id | string | Actor performing the activity |
| instrument_id | string | Instrument involved |

#### Provision
A unit of legal text.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| type | ProvisionType | definition, scope, requirement, prohibition, exception, procedure, sanction |
| source | SourceReference | Citation to source document |
| text | string | The legal text |
| effective_from | date | When provision takes effect |

#### Obligation / Permission / Prohibition
Normative content extracted from provisions.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| provision_id | string | Source provision |
| action | string | What must/may/must not be done |
| applies_to_actor | ActorType | Actor type this applies to |
| applies_to_instrument | InstrumentType | Instrument type |
| conditions | ConditionGroup | Applicability conditions |

### Relations

Relations connect entities in the knowledge graph:

| Relation | From → To | Example |
|----------|-----------|---------|
| IMPOSES_OBLIGATION_ON | Provision → Actor | Art. 36(1) → Issuer |
| PERMITS | Provision → Activity | Art. 5 → Public offer |
| PROHIBITS | Provision → Activity | Art. 76 → Market manipulation |
| EXEMPTS | Provision → Actor | Art. 36(2) → Credit institution |
| APPLIES_TO | Rule → Instrument | mica_art36 → ART |
| REGULATES | CompetentAuthority → Actor | EBA → Significant ART issuer |

## Worked Example: MiCA Article 36

### Source Text

> **Article 36 — Authorisation**
>
> 1. No person shall make a public offer in the Union of an asset-referenced token, or seek admission of such a crypto-asset to trading on a trading platform for crypto-assets, unless that person is:
>    (a) a legal person or other undertaking that is established in the Union and that has been authorised in accordance with Article 21...
>    (b) a credit institution...

### Knowledge Extraction

**Step 1: Identify the Provision**

```yaml
provision:
  id: mica_art36_1
  type: requirement
  source:
    document_id: mica_2023
    article: "36(1)"
    pages: [65]
  text: "No person shall make a public offer..."
  effective_from: 2024-06-30
```

**Step 2: Extract Normative Content**

The provision contains a **prohibition** (implicit) with an **exception**:

```yaml
prohibition:
  id: art36_public_offer_prohibition
  provision_id: mica_art36_1
  action: "make public offer of ART without authorization"
  applies_to_actor: issuer
  applies_to_instrument: art

permission:
  id: art36_authorized_issuer
  provision_id: mica_art36_1
  action: "make public offer of ART"
  applies_to_actor: issuer
  conditions:
    any:
      - field: authorized
        operator: "=="
        value: true
      - field: is_credit_institution
        operator: "=="
        value: true
```

**Step 3: Create Executable Rule**

```yaml
rule_id: mica_art36_public_offer_authorization
applies_if:
  all:
    - field: instrument_type
      operator: in
      value: [art, stablecoin]
    - field: activity
      operator: "=="
      value: public_offer
    - field: jurisdiction
      operator: "=="
      value: EU

decision_tree:
  node_id: check_exemption
  condition:
    field: is_credit_institution
    operator: "=="
    value: true
  true_branch:
    result: exempt
  false_branch:
    node_id: check_authorization
    condition:
      field: authorized
      operator: "=="
      value: true
    true_branch:
      result: authorized
    false_branch:
      result: not_authorized
      obligations:
        - id: obtain_authorization_art21
          description: "Obtain authorization per Article 21"
```

**Step 4: Trace Execution**

For scenario: `{instrument_type: "art", activity: "public_offer", jurisdiction: "EU", authorized: false, is_credit_institution: false}`

```json
{
  "decision": "not_authorized",
  "trace": [
    {"node": "applicability.all[0]", "condition": "instrument_type in [art, stablecoin]", "result": true, "value_checked": "art"},
    {"node": "applicability.all[1]", "condition": "activity == public_offer", "result": true, "value_checked": "public_offer"},
    {"node": "applicability.all[2]", "condition": "jurisdiction == EU", "result": true, "value_checked": "EU"},
    {"node": "check_exemption", "condition": "is_credit_institution == true", "result": false, "value_checked": false},
    {"node": "check_authorization", "condition": "authorized == true", "result": false, "value_checked": false}
  ],
  "obligations": [
    {"id": "obtain_authorization_art21", "source": "MiCA Art. 36(1), p. 65"}
  ]
}
```

## Modeling Guidelines

### 1. Separate Structure from Interpretation

- **Structure**: The syntactic organization of legal text (articles, sections, paragraphs)
- **Interpretation**: The semantic meaning we assign to that structure

Document interpretation choices in `interpretation_notes` fields.

### 2. Preserve Source Links

Every piece of derived knowledge must link back to its source provision with pinpoint citations (article, paragraph, page).

### 3. Make Conditions Explicit

Legal texts often have implicit conditions. Make these explicit:

```yaml
# Implicit in text: "issuers of significant ARTs"
# Explicit in model:
applies_if:
  all:
    - field: actor_type
      operator: "=="
      value: issuer
    - field: is_significant
      operator: "=="
      value: true
```

### 4. Handle Exceptions Systematically

Exceptions should be modeled as early exits in the decision tree, not as modifications to the base rule.

### 5. Version Everything

- Rules have `version`, `effective_from`, `effective_to`
- Source references include document version/date
- Interpretation notes explain reasoning at time of modeling

## Instrument Type Taxonomy (MiCA)

| Type | MiCA Definition | Key Characteristics |
|------|-----------------|---------------------|
| ART | Asset-Referenced Token | Value references basket of assets; requires authorization |
| EMT | E-Money Token | Value references single fiat currency; must be issued by credit/e-money institution |
| Utility Token | — | Provides access to a good/service; lighter regulation |
| Other Crypto-Asset | — | Catch-all for non-ART, non-EMT, non-utility tokens |

## RWA Instrument Type Taxonomy

Real-World Asset (RWA) tokens represent ownership or claims on off-chain assets that are tokenized on-chain.

| Type | Definition | Key Characteristics |
|------|------------|---------------------|
| RWAToken | Generic tokenized real-world asset | Base type for any tokenized RWA |
| RWADebt | Tokenized debt instrument | Bonds, loans, receivables; requires disclosure of credit terms |
| RWAEquity | Tokenized equity | Shares, fund units; subject to securities regulations |
| RWAProperty | Tokenized real estate | Property rights, REITs; requires property valuation and title verification |

### RWA-Specific Actors

| Actor Type | Description |
|------------|-------------|
| AssetOriginator | Entity that owns/originates the real-world asset being tokenized |
| Custodian | Entity responsible for safekeeping the underlying asset or its documentation |

## Activity Taxonomy

| Activity | Description | Relevant MiCA Articles |
|----------|-------------|------------------------|
| public_offer | Offering crypto-assets to the public | Art. 4-14 (white paper), Art. 36 (ART authorization) |
| admission_to_trading | Seeking trading platform listing | Art. 4-14, Art. 36 |
| custody | Safekeeping crypto-assets | Art. 75 |
| exchange | Trading crypto for fiat/other crypto | Art. 76 |

## RWA Activity Taxonomy

| Activity | Description | Regulatory Considerations |
|----------|-------------|---------------------------|
| tokenization | Converting real-world asset to on-chain token | Requires legal structuring, asset verification, smart contract deployment |
| disclosure | Ongoing disclosure of asset information | Periodic reporting on asset performance, valuation updates |
| valuation | Asset valuation and pricing | Independent valuation, mark-to-market requirements |

## Future Extensions

- **Temporal reasoning**: Handle rules that change over time
- **Jurisdictional layering**: EU regulations + member state implementations
- **Conflict resolution**: When multiple rules apply with different outcomes
- **Confidence scores**: Uncertainty in interpretation
