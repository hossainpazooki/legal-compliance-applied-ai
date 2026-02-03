# Temporal Workflows & Orchestration

This document describes the Temporal-based workflow orchestration system for compliance operations and rule verification.

## Overview

The system uses [Temporal](https://temporal.io/) for durable workflow execution, providing:
- **Fault tolerance**: Automatic retries and recovery from failures
- **Observability**: Built-in progress tracking and query support
- **Scalability**: Parallel activity execution with fan-out/fan-in patterns
- **Durability**: Workflow state persisted across restarts

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Temporal Server                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  Task Queues    │  │  Workflow State │  │  Scheduled Triggers │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Workflow 1    │   │   Workflow 2    │   │   Workflow N    │
│  (Compliance)   │   │ (Verification)  │   │    (Drift)      │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
    ┌────┴────┐           ┌────┴────┐           ┌────┴────┐
    ▼         ▼           ▼         ▼           ▼         ▼
┌───────┐ ┌───────┐   ┌───────┐ ┌───────┐   ┌───────┐ ┌───────┐
│Act 1  │ │Act 2  │   │Act 1  │ │Act 2  │   │Act 1  │ │Act 2  │
└───────┘ └───────┘   └───────┘ └───────┘   └───────┘ └───────┘
```

## Module Structure

```
backend/workflows/
├── __init__.py      # Package exports
├── schemas.py       # Pydantic I/O models
├── workflows.py     # @workflow.defn classes
├── activities.py    # @activity.defn functions
└── aws/             # AWS deployment integrations
    └── __init__.py
```

---

## Workflows

### 1. ComplianceCheckWorkflow

**Pattern**: Fan-out/Fan-in for multi-jurisdiction evaluation

**Purpose**: Evaluate compliance across multiple jurisdictions in parallel, detect conflicts, and synthesize a unified compliance pathway.

#### Phases

| Phase | Activity | Pattern |
|-------|----------|---------|
| 1. Resolve | `resolve_jurisdictions_activity` | Sequential |
| 2. Equivalences | `get_equivalences_activity` | Parallel with Phase 3 |
| 3. Evaluate | `evaluate_jurisdiction_activity` | Fan-out (parallel per jurisdiction) |
| 4. Conflicts | `detect_conflicts_activity` | Sequential (after fan-in) |
| 5. Synthesize | `synthesize_pathway_activity` | Sequential |
| 6. Aggregate | `aggregate_obligations_activity` | Sequential |

#### Input Schema

```python
class ComplianceCheckInput(BaseModel):
    issuer_jurisdiction: str       # Issuer's home jurisdiction code
    target_jurisdictions: list[str] # Target market jurisdiction codes
    facts: dict[str, Any]          # Scenario facts for evaluation
    instrument_type: str | None    # Optional instrument type
    include_equivalences: bool     # Query equivalence determinations
    detect_conflicts: bool         # Detect inter-jurisdiction conflicts
```

#### Output Schema

```python
class ComplianceCheckOutput(BaseModel):
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None
    issuer_jurisdiction: str
    target_jurisdictions: list[str]
    jurisdiction_results: list[JurisdictionResult]
    equivalences: list[EquivalenceResult]
    conflicts: list[ConflictResult]
    pathway: CompliancePathway | None
    aggregated_obligations: list[dict]
    overall_status: JurisdictionStatus
    error: str | None
```

#### Queries & Signals

- **Query `progress`**: Returns `ComplianceCheckProgress` with phase and completion status

---

### 2. RuleVerificationWorkflow

**Pattern**: Sequential Saga with early termination

**Purpose**: Execute 5-tier consistency verification on a rule with optional fail-fast behavior.

#### Verification Tiers

| Tier | Name | Weight | Module | ML Dependency |
|------|------|--------|--------|---------------|
| 0 | Schema & Structural | 1.0 | `service.py` | None |
| 1 | Lexical & Heuristic | 0.8 | `service.py` | None |
| 2 | Semantic Similarity | 0.9 | `embeddings.py` | Optional: sentence-transformers |
| 3 | NLI Entailment | 0.95 | `nli.py` | Optional: transformers, torch |
| 4 | Cross-Rule Consistency | 0.7 | `cross_rule.py` | None |

#### Phases

```
Load Rule → Tier 0 → Tier 1 → Tier 2 → Tier 3 → Tier 4 → Compute Results
                ↓         ↓         ↓         ↓         ↓
            (fail_fast: stop on first failure)
```

#### Input Schema

```python
class RuleVerificationInput(BaseModel):
    rule_id: str                           # Rule ID to verify
    source_text: str | None                # Source regulatory text (tiers 1-3)
    max_tier: VerificationTier             # Maximum tier to run
    skip_tiers: list[VerificationTier]     # Tiers to skip
    fail_fast: bool                        # Stop on first failure
```

#### Output Schema

```python
class RuleVerificationOutput(BaseModel):
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None
    rule_id: str
    tier_results: list[TierResult]
    highest_tier_passed: VerificationTier | None
    overall_score: float
    overall_passed: bool
    stopped_early: bool
    stop_reason: str | None
    error: str | None
```

#### Queries & Signals

- **Query `progress`**: Returns current tier and completion status
- **Signal `skip_tier(tier: int)`**: Dynamically skip a tier during execution

---

### 3. CounterfactualAnalysisWorkflow

**Pattern**: Baseline + Parallel Scenario Analysis

**Purpose**: Evaluate how rule decisions change under different fact scenarios (what-if analysis).

#### Phases

| Phase | Activity | Pattern |
|-------|----------|---------|
| 1. Baseline | `evaluate_baseline_activity` | Sequential |
| 2. Counterfactuals | `analyze_counterfactual_activity` | Parallel (all scenarios) |
| 3. Deltas | `compute_delta_activity` | Parallel (all scenarios) |

#### Scenario Types

```python
class ScenarioType(str, Enum):
    JURISDICTION_CHANGE = "jurisdiction_change"
    ENTITY_CHANGE = "entity_change"
    ACTIVITY_RESTRUCTURE = "activity_restructure"
    THRESHOLD = "threshold"
    TEMPORAL = "temporal"
    PROTOCOL_CHANGE = "protocol_change"
    REGULATORY_CHANGE = "regulatory_change"
```

#### Input Schema

```python
class CounterfactualInput(BaseModel):
    rule_id: str                              # Rule to analyze
    baseline_facts: dict[str, Any]            # Baseline scenario facts
    scenarios: list[CounterfactualScenario]   # Counterfactual scenarios
    include_delta_analysis: bool              # Include delta analysis
```

#### Output Schema

```python
class CounterfactualOutput(BaseModel):
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None
    rule_id: str
    baseline_result: ScenarioResult
    scenario_results: list[ScenarioResult]
    delta_analyses: list[DeltaAnalysis]
    summary: str
    error: str | None
```

---

### 4. DriftDetectionWorkflow

**Pattern**: Scheduled Batch Processing

**Purpose**: Periodically check rules for drift (schema changes, broken references, source modifications).

#### Drift Types Detected

| Type | Description | Severity |
|------|-------------|----------|
| `rule_missing` | Rule no longer exists | critical |
| `schema_drift` | Rule structure changed | high |
| `reference_drift` | Source references broken | medium |
| `source_drift` | Source document modified | low |

#### Phases

| Phase | Activity | Pattern |
|-------|----------|---------|
| 1. Get Rules | `get_all_rule_ids_activity` | Sequential |
| 2. Check Drift | `check_rule_drift_activity` | Batched parallel (10 at a time) |
| 3. Notify | `notify_drift_detected_activity` | Sequential |

#### Input Schema

```python
class DriftDetectionInput(BaseModel):
    rule_ids: list[str] | None    # Specific rules (None = all)
    check_schema_drift: bool      # Check for schema changes
    check_source_drift: bool      # Check for source changes
    check_reference_drift: bool   # Check for broken references
    notify_on_drift: bool         # Send notifications
```

#### Scheduled Execution

```python
class DriftScheduleConfig(BaseModel):
    schedule_id: str              # Unique schedule identifier
    cron_expression: str          # Default: "0 0 * * *" (daily midnight)
    enabled: bool                 # Whether schedule is active
    input: DriftDetectionInput    # Workflow input configuration
```

---

## Activities

Activities are the atomic units of work that workflows orchestrate. Each wraps a service function with the `@activity.defn` decorator.

### Compliance Activities

| Activity | Purpose | Timeout |
|----------|---------|---------|
| `resolve_jurisdictions_activity` | Resolve applicable jurisdictions/regimes | 30s |
| `get_equivalences_activity` | Query equivalence determinations | 30s |
| `evaluate_jurisdiction_activity` | Evaluate facts against jurisdiction rules | 2m |
| `detect_conflicts_activity` | Detect inter-jurisdiction conflicts | 30s |
| `synthesize_pathway_activity` | Synthesize compliance pathway | 30s |
| `aggregate_obligations_activity` | Aggregate/deduplicate obligations | 30s |

### Verification Activities

| Activity | Purpose | Timeout | ML Fallback |
|----------|---------|---------|-------------|
| `load_rule_activity` | Load and validate rule exists | 30s | N/A |
| `verify_tier_0_activity` | Schema & structural checks | 2m | N/A |
| `verify_tier_1_activity` | Lexical & heuristic checks | 2m | N/A |
| `verify_tier_2_activity` | Semantic similarity (embeddings) | 2m | TF-IDF + n-gram |
| `verify_tier_3_activity` | NLI entailment checking | 2m | Keyword overlap |
| `verify_tier_4_activity` | Cross-rule consistency | 2m | N/A |

### Counterfactual Activities

| Activity | Purpose | Timeout |
|----------|---------|---------|
| `evaluate_baseline_activity` | Evaluate baseline scenario | 2m |
| `analyze_counterfactual_activity` | Analyze single counterfactual | 2m |
| `compute_delta_activity` | Compute baseline vs counterfactual delta | 30s |

### Drift Activities

| Activity | Purpose | Timeout |
|----------|---------|---------|
| `get_all_rule_ids_activity` | Get all rule IDs from loader | 2m |
| `check_rule_drift_activity` | Check single rule for drift | 2m |
| `notify_drift_detected_activity` | Send drift notifications | 30s |

---

## Retry Policy & Timeouts

### Default Retry Policy

```python
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)
```

### Activity Timeouts

| Timeout | Duration | Use Case |
|---------|----------|----------|
| `SHORT_TIMEOUT` | 30s | Simple queries, notifications |
| `MEDIUM_TIMEOUT` | 2m | Rule evaluation, verification tiers |
| `LONG_TIMEOUT` | 10m | Batch processing, complex analysis |

---

## Deployment

### Requirements

```toml
[project.dependencies]
temporalio = ">=1.9.0"
pydantic = ">=2.0.0"

[project.optional-dependencies]
verification = [
    "sentence-transformers>=2.2.0",  # Tier 2 ML
    "transformers>=4.30.0",          # Tier 3 ML
    "torch>=2.0.0",                  # Tier 3 ML
]
```

### Temporal Server Setup

```bash
# Local development (Docker)
docker run -d --name temporal \
  -p 7233:7233 \
  -p 8233:8233 \
  temporalio/auto-setup:latest

# Verify connection
temporal operator namespace describe default
```

### Worker Registration

```python
from temporalio.client import Client
from temporalio.worker import Worker

from backend.workflows.workflows import (
    ComplianceCheckWorkflow,
    RuleVerificationWorkflow,
    CounterfactualAnalysisWorkflow,
    DriftDetectionWorkflow,
)
from backend.workflows.activities import (
    resolve_jurisdictions_activity,
    evaluate_jurisdiction_activity,
    verify_tier_0_activity,
    verify_tier_1_activity,
    verify_tier_2_activity,
    verify_tier_3_activity,
    verify_tier_4_activity,
    # ... all other activities
)

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="compliance-workflows",
        workflows=[
            ComplianceCheckWorkflow,
            RuleVerificationWorkflow,
            CounterfactualAnalysisWorkflow,
            DriftDetectionWorkflow,
        ],
        activities=[
            resolve_jurisdictions_activity,
            evaluate_jurisdiction_activity,
            verify_tier_0_activity,
            verify_tier_1_activity,
            verify_tier_2_activity,
            verify_tier_3_activity,
            verify_tier_4_activity,
            # ... all other activities
        ],
    )

    await worker.run()
```

### Starting Workflows

```python
from temporalio.client import Client
from backend.workflows.schemas import RuleVerificationInput, VerificationTier

async def verify_rule(rule_id: str, source_text: str | None = None):
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        "RuleVerificationWorkflow",
        RuleVerificationInput(
            rule_id=rule_id,
            source_text=source_text,
            max_tier=VerificationTier.CROSS_RULE,
            fail_fast=True,
        ),
        id=f"verify-{rule_id}",
        task_queue="compliance-workflows",
    )

    return result
```

### Scheduled Workflows (Cron)

```python
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow

async def schedule_drift_detection():
    client = await Client.connect("localhost:7233")

    await client.create_schedule(
        "daily-drift-check",
        Schedule(
            action=ScheduleActionStartWorkflow(
                "DriftDetectionWorkflow",
                DriftDetectionInput(notify_on_drift=True),
                id="drift-detection-scheduled",
                task_queue="compliance-workflows",
            ),
            spec=ScheduleSpec(
                cron_expressions=["0 0 * * *"],  # Daily at midnight
            ),
        ),
    )
```

---

## AWS Integration

The `backend/*/aws/` folders are prepared for AWS-specific integrations:

### Planned Integrations

| Service | Purpose |
|---------|---------|
| **AWS Step Functions** | Alternative workflow orchestration |
| **Amazon SQS** | Activity task queues |
| **AWS Lambda** | Serverless activity execution |
| **Amazon CloudWatch** | Workflow metrics and logging |
| **AWS Secrets Manager** | Credential management |
| **Amazon S3** | Rule and source document storage |

### Temporal on AWS

For production deployment, consider:
- **Temporal Cloud**: Managed Temporal service
- **Self-hosted on EKS**: Kubernetes deployment with Helm charts
- **Amazon Aurora**: PostgreSQL-compatible persistence layer

---

## Monitoring & Observability

### Progress Queries

All workflows support `@workflow.query` for real-time progress:

```python
# Query workflow progress
handle = client.get_workflow_handle("verify-rule-123")
progress = await handle.query(RuleVerificationWorkflow.progress)
print(f"Current tier: {progress.current_tier}")
print(f"Completed: {progress.tiers_completed}")
```

### Temporal Web UI

Access the Temporal Web UI at `http://localhost:8233` for:
- Workflow execution history
- Activity retry status
- Signal/query interaction
- Scheduled workflow management

### Metrics

Key metrics to monitor:
- Workflow completion rate
- Activity retry count
- Tier-specific pass/fail rates
- Drift detection frequency

---

## Error Handling

### Workflow-Level Errors

All workflows catch exceptions and return structured error information:

```python
try:
    # Workflow execution
    ...
except Exception as e:
    self._status = WorkflowStatus.FAILED
    self._error = str(e)
    return Output(
        status=self._status,
        error=self._error,
        ...
    )
```

### Activity-Level Errors

Activities use the default retry policy with exponential backoff. Non-retryable errors should raise `ApplicationError` with `non_retryable=True`.

### Fail-Fast Behavior

The `RuleVerificationWorkflow` supports fail-fast mode:

```python
if input.fail_fast and not result.passed:
    self._stopped_early = True
    self._stop_reason = f"Tier {tier.value} ({result.tier_name}) failed"
    break  # Exit tier loop early
```

---

## References

- [Temporal Python SDK Documentation](https://docs.temporal.io/dev-guide/python)
- [Consistency Engine Implementation](./consistency_engine_implementation.md)
- [Semantic Consistency Specification](./semantic_consistency_regulatory_kg.md)
