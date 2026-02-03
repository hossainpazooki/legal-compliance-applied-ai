"""
Temporal workflows for compliance operations.

This package provides fault-tolerant, long-running workflow orchestration using Temporal.

Workflows:
- ComplianceCheckWorkflow: Parallel multi-jurisdiction compliance evaluation
- RuleVerificationWorkflow: Sequential tier-based rule verification
- CounterfactualAnalysisWorkflow: Baseline + parallel scenario analysis
- DriftDetectionWorkflow: Scheduled rule drift detection

Usage:
    # Start a workflow via client
    from backend.workflows import WorkflowClient, ComplianceCheckInput

    async with WorkflowClient() as client:
        workflow_id = await client.start_compliance_check(
            ComplianceCheckInput(
                issuer_jurisdiction="EU",
                target_jurisdictions=["UK", "SG"],
                facts={"instrument_type": "utility_token"},
            )
        )
        result = await client.get_compliance_check_result(workflow_id)

    # Run worker (standalone)
    python -m backend.workflows.worker

    # Use in FastAPI app
    from backend.workflows import workflow_router
    app.include_router(workflow_router)
"""

from .schemas import (
    # Enums
    WorkflowStatus,
    VerificationTier,
    JurisdictionStatus,
    ScenarioType,
    # ComplianceCheck schemas
    ComplianceCheckInput,
    ComplianceCheckOutput,
    ComplianceCheckProgress,
    JurisdictionResult,
    EquivalenceResult,
    ConflictResult,
    CompliancePathway,
    # RuleVerification schemas
    RuleVerificationInput,
    RuleVerificationOutput,
    RuleVerificationProgress,
    TierResult,
    # Counterfactual schemas
    CounterfactualInput,
    CounterfactualOutput,
    CounterfactualProgress,
    CounterfactualScenario,
    ScenarioResult,
    DeltaAnalysis,
    # DriftDetection schemas
    DriftDetectionInput,
    DriftDetectionOutput,
    DriftDetectionProgress,
    RuleDriftResult,
    DriftScheduleConfig,
    # Workflow info
    WorkflowInfo,
)

from .workflows import (
    ComplianceCheckWorkflow,
    RuleVerificationWorkflow,
    CounterfactualAnalysisWorkflow,
    DriftDetectionWorkflow,
)

from .client import (
    WorkflowClient,
    get_client,
    workflow_client,
)

from .router import router as workflow_router

from .worker import (
    create_client,
    create_worker,
    run_worker,
    ACTIVITIES,
    WORKFLOWS,
)


__all__ = [
    # Enums
    "WorkflowStatus",
    "VerificationTier",
    "JurisdictionStatus",
    "ScenarioType",
    # ComplianceCheck
    "ComplianceCheckInput",
    "ComplianceCheckOutput",
    "ComplianceCheckProgress",
    "ComplianceCheckWorkflow",
    "JurisdictionResult",
    "EquivalenceResult",
    "ConflictResult",
    "CompliancePathway",
    # RuleVerification
    "RuleVerificationInput",
    "RuleVerificationOutput",
    "RuleVerificationProgress",
    "RuleVerificationWorkflow",
    "TierResult",
    # Counterfactual
    "CounterfactualInput",
    "CounterfactualOutput",
    "CounterfactualProgress",
    "CounterfactualAnalysisWorkflow",
    "CounterfactualScenario",
    "ScenarioResult",
    "DeltaAnalysis",
    # DriftDetection
    "DriftDetectionInput",
    "DriftDetectionOutput",
    "DriftDetectionProgress",
    "DriftDetectionWorkflow",
    "RuleDriftResult",
    "DriftScheduleConfig",
    # Workflow info
    "WorkflowInfo",
    # Client
    "WorkflowClient",
    "get_client",
    "workflow_client",
    # Router
    "workflow_router",
    # Worker
    "create_client",
    "create_worker",
    "run_worker",
    "ACTIVITIES",
    "WORKFLOWS",
]
