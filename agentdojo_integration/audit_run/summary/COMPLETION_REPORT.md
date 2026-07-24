# Audit Completion Report

- Output: `agentdojo_integration/audit_run`
- Episodes: {'specs': 32, 'completed': 21, 'skipped': 11, 'errors': 0}

## Validations

- frozen_integrity_unchanged: **True**
- trace_integrity_all_ok: **True**
- replay_all_consistent: **True**
- authorization_replay_identical: **True**
- proofs_all_consistent: **True**

## Statistics headline

- Gamma decisions: 14 (PERMIT 11, SAFE_STATE 3)

## Artifacts

- **per_episode_dirs**: ['agentdojo_integration/audit_run/trace/workspace/user_task_0__injection_task_0', 'agentdojo_integration/audit_run/trace/workspace/user_task_1__injection_task_0', 'agentdojo_integration/audit_run/trace/workspace/user_task_3__injection_task_0', 'agentdojo_integration/audit_run/trace/workspace/user_task_2__injection_task_0', 'agentdojo_integration/audit_run/trace/workspace/user_task_5__injection_task_0', 'agentdojo_integration/audit_run/trace/workspace/user_task_6__injection_task_0', 'agentdojo_integration/audit_run/trace/workspace/user_task_7__injection_task_0', 'agentdojo_integration/audit_run/trace/workspace/user_task_8__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_0__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_1__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_2__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_3__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_4__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_5__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_6__injection_task_0', 'agentdojo_integration/audit_run/trace/banking/user_task_7__injection_task_0', 'agentdojo_integration/audit_run/trace/slack/user_task_0__injection_task_1', 'agentdojo_integration/audit_run/trace/slack/user_task_1__injection_task_1', 'agentdojo_integration/audit_run/trace/slack/user_task_2__injection_task_1', 'agentdojo_integration/audit_run/trace/slack/user_task_3__injection_task_1', 'agentdojo_integration/audit_run/trace/slack/user_task_4__injection_task_1', 'agentdojo_integration/audit_run/trace/slack/user_task_5__injection_task_1', 'agentdojo_integration/audit_run/trace/slack/user_task_6__injection_task_1', 'agentdojo_integration/audit_run/trace/slack/user_task_7__injection_task_1', 'agentdojo_integration/audit_run/trace/travel/user_task_0__injection_task_6', 'agentdojo_integration/audit_run/trace/travel/user_task_1__injection_task_6', 'agentdojo_integration/audit_run/trace/travel/user_task_2__injection_task_6', 'agentdojo_integration/audit_run/trace/travel/user_task_3__injection_task_6', 'agentdojo_integration/audit_run/trace/travel/user_task_4__injection_task_6', 'agentdojo_integration/audit_run/trace/travel/user_task_5__injection_task_6', 'agentdojo_integration/audit_run/trace/travel/user_task_6__injection_task_6', 'agentdojo_integration/audit_run/trace/travel/user_task_7__injection_task_6']
- **statistics**: ['statistics.json', 'statistics_tables.md', 'decisions.csv', 'predicates.csv']
- **reviewer**: ['reviewer/MASTER_REPORT.md', 'reviewer/episodes/ (33 files)']
- **proofs**: ['all_proofs.json', 'proofs/ (14 proofs)']
- **figures**: ['fig1_gamma_histogram', 'fig2_pi_histogram', 'fig3_predicate_heatmap', 'fig4_tool_authorization_heatmap', 'fig5_latency_by_event', 'fig6_policy_utilization']
- **graphs**: ['authorization_graph.dot', 'tool_graph.dot', 'benchmark_flow.mmd', 'decision_sankey.mmd']
- **dashboards**: ['dashboard.html', 'explorer.html']
- **summary**: ['BENCHMARK_SUMMARY.md', 'BENCHMARK_SUMMARY.json']
- **supplementary**: ['trace_event.schema.json', 'csv_schema.json', 'SUPPLEMENTARY_MATERIAL.md']
- **integrity**: ['frozen_integrity.json', 'trace_integrity_all.json', 'replay_validation.json']

## Limitations

- The local model (llama3.1:8b via Ollama) is non-deterministic even at temperature 0, so episode-level utility/security vary run-to-run; authorization-layer values are deterministic given a fixed candidate action (validated).
- false_permit_rate / false_deny_rate require external per-action ground-truth labels not present in the traces; they are reported as null, never fabricated.
- This corpus is a bounded batch (see batch counts); scaling to the full AgentDojo corpus is a runtime-budget matter and requires no code change.