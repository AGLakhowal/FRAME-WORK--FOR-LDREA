# AgentDojo external validation design

## Goal

This module turns AgentDojo-style tool invocations into deterministic Externally Effective Actions (EEAs) and evaluates them through the same L-DREA/Gamma decision structure already used by the LAB v1.0 harness in this repository.

## Constraints

- Preserve the existing Gamma/L-DREA runtime logic.
- Avoid changing AgentDojo benchmark logic because no AgentDojo source tree is present in this workspace.
- Keep the flow fully reproducible and evidence-driven.

## Proposed architecture

1. AgentDojo task / tool call is represented as a structured action record.
2. The adapter converts that action into an EEA object with:
   - action type
   - target
   - sensitivity
   - authority requirements
   - execution context (token, freshness, staleness, risk)
3. The runtime bridge evaluates the EEA through:
   - LUIPM-style predicate evaluation
   - Gamma/G0 authorization logic
4. The report generator emits:
   - JSON report
   - JSONL replay manifest
   - HTML dashboard

## Minimal interception point

Because this workspace does not contain the AgentDojo codebase, the safest interception point is the point where an action is about to be executed. The harness models that boundary as a single function call that receives the candidate action and returns PERMIT or SAFE_STATE before any actual tool execution occurs.

## Scenario mapping

The adapter maps representative AgentDojo actions into the following EEA classes:

- file deletion -> file system effect
- browser purchase -> financial effect
- email send -> external communication effect
- database write -> data mutation effect
- system command -> command execution effect
- safe read -> non-sensitive observation effect

## Evidence model

Every action produces:

- a deterministic decision
- a replay hash chain entry
- a manifest record suitable for independent verification

## Reproducibility

The harness uses only standard library modules and deterministic scenario data. Running the report generator writes the JSON/JSONL/HTML artifacts in a repeatable way.
