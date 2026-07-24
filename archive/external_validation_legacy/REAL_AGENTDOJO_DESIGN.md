# Real AgentDojo integration design for L-DREA

## Objective

Integrate the real open-source AgentDojo benchmark with L-DREA as an execution-boundary authorization layer without modifying AgentDojo’s benchmark logic, task definitions, or scoring.

## Source of truth

The official repository is:

- https://github.com/ethz-spylab/agentdojo

The project is documented at:

- https://agentdojo.spylab.ai/

## What AgentDojo is

AgentDojo is an open-source benchmark for evaluating prompt-injection attacks and defenses for LLM agents. It provides:

- benchmark suites and tasks
- an agent pipeline
- tool-calling LLM support
- a functions runtime that executes tool calls
- a benchmark runner that orchestrates tasks and collects results

## Architecture summary

AgentDojo is composed of four layers:

1. Benchmark layer
   - task suites
   - user tasks and injection tasks
   - benchmark runner and result collection

2. Agent pipeline layer
   - system prompt injection
   - LLM interaction
   - tool-call generation
   - looped tool execution

3. Functions runtime layer
   - tool registration
   - argument validation
   - dependency injection
   - function dispatch

4. Environment/task layer
   - task-specific state
   - environment objects
   - tool access and observability

## How tasks are executed

The benchmark runner creates an AgentPipeline and runs each task through a loop:

- the model is asked to solve the task
- the model can emit tool calls
- the tool-execution component executes those calls
- the model sees the results and may continue reasoning or stop

This is driven by the benchmark entry point in the repository’s benchmark script and by the AgentPipeline execution loop.

## How tools are invoked

Tools are not executed directly by the LLM. They are represented as structured function calls in the conversation history. The execution stage parses these calls and dispatches them through the FunctionsRuntime.

The relevant execution path is:

- the LLM emits a tool call
- the tool-execution component inspects the latest assistant message
- each tool call is validated against the registered tools
- the runtime dispatches the call to the underlying function implementation

## Exact execution boundary

The precise interception point for L-DREA is the call from the AgentDojo tool-execution component into the FunctionsRuntime dispatcher.

In the official source, this occurs at:

- src/agentdojo/agent_pipeline/tool_execution.py
- the call to runtime.run_function(env, tool_call.function, tool_call.args)

That is the last point before AgentDojo’s runtime actually executes the tool implementation.

This is the correct place for L-DREA to evaluate every candidate externally effective action because:

- the tool name is known
- the arguments are known
- the execution context is available
- the tool implementation has not yet run
- the authorization decision can prevent side effects

## Why this is the right boundary

This boundary is superior to:

- before planning: too early; the model may still change its plan
- after tool execution: too late; side effects already occurred
- inside individual tool wrappers: too narrow; it would miss other tool classes and could be bypassed by future tool implementations
- inside environment wrappers: too late and too environment-specific

The correct model is:

- AgentDojo decides what action the agent wants to perform
- L-DREA decides whether that action is authorized to cross the execution boundary
- only authorized actions proceed to the underlying tool implementation

## Mapping AgentDojo actions to L-DREA’s execution-boundary model

Every AgentDojo tool invocation should be treated as an Externally Effective Action (EEA) candidate.

Examples:

- file operations -> file-system effect
- email sending -> external communication effect
- database writes -> data mutation effect
- browser or purchase actions -> financial effect
- shell/command execution -> system-effect effect

The mapping should be done at the tool-call boundary using the following fields:

- tool name
- tool arguments
- task context
- environment state
- user/task identity
- whether the action is read-only or state-changing
- whether the action crosses a sensitive external boundary

## Recommended integration strategy

Integration should occur at the FunctionsRuntime dispatch boundary, not by modifying the benchmark logic.

Recommended approach:

1. Leave AgentDojo’s benchmark runner and task definitions unchanged.
2. Interpose L-DREA between the tool-execution layer and the underlying tool implementation.
3. Evaluate each tool call before the tool implementation executes.
4. If authorized, let the existing tool implementation run unchanged.
5. If denied, return a safe-state result or a structured deny response to the agent loop.

This preserves AgentDojo’s semantics while ensuring every effective action passes through L-DREA.

## Proposed control flow

1. The model emits a tool call.
2. AgentDojo’s tool-execution component identifies the tool and parses arguments.
3. L-DREA receives the tool invocation as an EEA candidate.
4. L-DREA evaluates the action using its runtime authorization logic.
5. If the decision is PERMIT, the normal tool implementation executes.
6. If the decision is SAFE_STATE, execution is blocked and the tool loop records a deny outcome.
7. Evidence is emitted for replay and audit.

## Architectural placement

The integration should be implemented as a thin authorization layer inserted at the runtime dispatch boundary, conceptually between:

- AgentDojo’s ToolsExecutor / tool-execution loop
- and the underlying tool implementation registered in FunctionsRuntime

In other words:

- AgentDojo remains the benchmark orchestrator
- FunctionsRuntime remains the tool dispatcher
- L-DREA becomes the gate before the dispatcher completes the tool call

## Design constraints

The integration must:

- preserve AgentDojo’s benchmark methodology
- preserve task definitions and scoring
- avoid modifying the LLM policy loop more than necessary
- keep authorization decisions deterministic and replayable
- emit evidence that can be independently verified

## Non-goals

This design does not include:

- modifying AgentDojo tasks
- changing AgentDojo scoring
- changing AgentDojo benchmark logic
- faking or estimating results
- replacing AgentDojo with a simulator

## Expected outcome

Once implemented, the integration will allow the real AgentDojo benchmark to exercise L-DREA’s execution-boundary authorization model under a third-party open-source benchmark, while retaining AgentDojo’s own task structure and evaluation semantics.
