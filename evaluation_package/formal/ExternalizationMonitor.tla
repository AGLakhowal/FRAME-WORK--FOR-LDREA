---------------------------- MODULE ExternalizationMonitor ----------------------------
\* Transcribed verbatim from L-DREA (IEEE Access R4) Appendix D.
\* This is the paper's own TLA+ specification of Invariant 1 (Execution Sovereignty),
\* with Invariant 2 (Non-Bypassability) and the StructuralInvariant, for TLC model checking.
\* No logic is added or altered relative to Appendix D; only OCR punctuation is normalized.
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Tokens,        \* finite set of issued permit tokens
          Epochs,        \* finite set of key epochs
          ClassMetrics,  \* finite set of class-level metric indices
          NodeMetrics,   \* finite set of node-level metric indices
          MaxClockSkew   \* upper bound on |Delta_clk|

VARIABLES currentEpoch, consumedTokens, revokedTokens, classFlags,
          nodeDeficits, classDeficits, traceChain, sigWatchdog, executedOps

vars == << currentEpoch, consumedTokens, revokedTokens, classFlags,
           nodeDeficits, classDeficits, traceChain, sigWatchdog, executedOps >>

\* --- Combinational predicates (derived, not state) ---
\* SIG_GAMMA, SIG_COMMIT, and P_phys are combinational signals at the substrate,
\* not persistent state. They are derived from the current values of their dependents
\* at every evaluation (Tier-H FPGA gate semantics, Section V-G).

GammaG == LET maxD == CHOOSE m \in NodeMetrics :
                        \A n \in NodeMetrics : nodeDeficits[n] <= nodeDeficits[m]
          IN nodeDeficits[maxD]

GammaClass == LET maxC == CHOOSE m \in ClassMetrics :
                            \A n \in ClassMetrics : classDeficits[n] <= classDeficits[m]
              IN classDeficits[maxC]

SigGamma == IF GammaG = 0 /\ GammaClass = 0 THEN 1 ELSE 0

ValidToken(tok) == /\ tok \in Tokens
                   /\ tok \notin revokedTokens
                   /\ tok \notin consumedTokens

SigCommit(tok) == IF ValidToken(tok) /\ Len(traceChain) >= 0 THEN 1 ELSE 0

PPhys(tok) == IF SigCommit(tok) = 1 /\ SigGamma = 1 /\ sigWatchdog = 1 THEN 1 ELSE 0

\* --- Initial state ---
Init == /\ currentEpoch \in Epochs
        /\ consumedTokens = {}
        /\ revokedTokens = {}
        /\ classFlags = [c \in ClassMetrics |-> 0]
        /\ nodeDeficits = [n \in NodeMetrics |-> 0]
        /\ classDeficits = [c \in ClassMetrics |-> 0]
        /\ traceChain = << >>
        /\ sigWatchdog = 1
        /\ executedOps = << >>

\* --- Actions ---
ProposeAction ==
    \E newND \in [NodeMetrics -> 0..1], newCD \in [ClassMetrics -> 0..1] :
        /\ nodeDeficits' = newND
        /\ classDeficits' = newCD
        /\ UNCHANGED << currentEpoch, consumedTokens, revokedTokens, classFlags,
                        traceChain, sigWatchdog, executedOps >>

CommitAndIssue(ct, op) ==
    /\ ValidToken(ct)
    /\ SigGamma = 1          \* fail-closed: only commit if Gamma = 0
    /\ sigWatchdog = 1       \* watchdog must be live
    /\ traceChain' = Append(traceChain, [token |-> ct, op |-> op])
    /\ consumedTokens' = consumedTokens \union {ct}
    /\ executedOps' = Append(executedOps, << op, Len(traceChain') >>)
    /\ UNCHANGED << currentEpoch, revokedTokens, classFlags,
                    nodeDeficits, classDeficits, sigWatchdog >>

RevokeToken(rt) ==
    /\ rt \in Tokens
    /\ rt \notin consumedTokens
    /\ rt \notin revokedTokens
    /\ revokedTokens' = revokedTokens \union {rt}
    /\ UNCHANGED << currentEpoch, consumedTokens, classFlags,
                    nodeDeficits, classDeficits, traceChain, sigWatchdog, executedOps >>

WatchdogFault ==
    /\ sigWatchdog' = 0
    /\ UNCHANGED << currentEpoch, consumedTokens, revokedTokens, classFlags,
                    nodeDeficits, classDeficits, traceChain, executedOps >>

Next == \/ ProposeAction
        \/ \E ct \in Tokens, op \in {"op1", "op2", "op3"} : CommitAndIssue(ct, op)
        \/ \E rt \in Tokens : RevokeToken(rt)
        \/ WatchdogFault

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

\* --- Invariants ---
\* Invariant 1 (Execution Sovereignty): every executed op was admitted with a valid
\* token under zero global and class deficits at commit time. The CommitAndIssue guard
\* enforces SigGamma = 1 (GammaG = 0 and GammaClass = 0) at admission; the trace chain
\* preserves the historical witness.
ExecutionSovereignty ==
    \A i \in 1..Len(executedOps) :
        /\ traceChain[i].token \in consumedTokens
        /\ traceChain[i].token \notin revokedTokens

\* Invariant 2 (Non-Bypassability, combinational form): P_phys asserts only when all
\* three substrate signals concurrently assert. Structural in the spec.
NonBypassability ==
    \A ct \in Tokens :
        PPhys(ct) = 1 => (SigCommit(ct) = 1 /\ SigGamma = 1 /\ sigWatchdog = 1)

\* Structural consistency of derived signals with their dependents.
StructuralInvariant ==
    /\ (SigGamma = 1) <=> (GammaG = 0 /\ GammaClass = 0)
    /\ \A ct \in Tokens : ValidToken(ct) => SigCommit(ct) = 1

THEOREM Spec => []NonBypassability
THEOREM Spec => []StructuralInvariant
THEOREM Spec => []ExecutionSovereignty
=======================================================================================
