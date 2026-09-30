# ADR-0010: Local Software Department Workflow Automation

## Status

Accepted

## Context

Stage 2 (`ARCHITECTURE.md` Section 5 & 13.3) requires executable local software department workflow automation enforcing:
1. Codex orchestration-only constraints (Codex creates TaskContracts, selects local model roles, requires evidence, but never writes production code).
2. Local model department role isolation (Local Coder, Local Tester, Local Reviewer).
3. Automated TaskContract validation, evidence auditing, and session handoff generation.

## Decision

### 1. Module Ownership

`src/nps_core/department_orchestration/` owns `TaskContractSpec`, `DepartmentWorkflowEngine`, `HandoffGenerator`, and domain exceptions (`DepartmentError`, `OrchestrationRuleViolationError`, `HandoffValidationError`).

### 2. Contract Verification & Audit

`DepartmentWorkflowEngine.verify_contract` validates that TaskContracts assign implementation strictly to local model roles (`local_coder`, `local_tester`, `local_reviewer`), preventing direct production code writing by Codex. `audit_evidence` verifies evidence packets against task specs.

### 3. Session Handoff Automation

`HandoffGenerator.generate` produces formatted markdown session handoff documentation adhering to repository standards.

## Consequences

- Stage 2 — Local Software Department exit criteria are 100% fulfilled.
- Standard-library runtime dependencies only; zero network calls or external I/O.
