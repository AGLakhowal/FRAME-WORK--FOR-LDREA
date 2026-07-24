#!/usr/bin/env python3
"""Local, warn-only single-authorization-engine guardrail (Commit 0.2).

PURPOSE
    Detect potential *competing* authorization implementations during engineering:
    Python code that COMPUTES an authorization outcome locally
    (``gamma_g`` / ``gamma_class`` / ``pi`` / ``permit`` selection, or a
    ``"PERMIT"`` / ``"SAFE_STATE"`` decision) instead of obtaining it from the
    single frozen engine ``gamma_test_runner.evaluate_decision``.

WHAT THIS IS NOT
    This tool performs OBSERVATION ONLY. It authors no authorization logic, imports
    nothing from Gamma, and changes no predicate, threshold, decision, metric,
    replay, Evidence Quad, or Hydra Ledger behaviour. It is not part of Gamma,
    L-DREA, FULL_SPEC, or any scientific artifact.

DISCIPLINE (Engineering Migration Roadmap, Commit 0.2)
    * warn-only: prints findings, never fails, ALWAYS exits 0.
    * additive: creates/reads nothing but its own registry; never edits source.
    * deterministic: pure AST analysis + a JSON registry; no network, no state.
    * standard library only (ast, json, argparse, pathlib) -- no dependencies.
    * CI-independent: runs locally; later CI can invoke it unchanged.

DETECTION (AST, not regex -- comments/strings/docs cannot trip it)
    A construct in a scanned, non-exempt file is reported when it is one of:
      1. auth_output_assignment    -- assignment to a name in AUTH_OUTPUT_NAMES
                                      whose right-hand side is NOT an evaluate_decision(...) call
      2. decision_literal_selection-- an ``X if cond else Y`` where both branches
                                      are decision-literal constants ("PERMIT"/"SAFE_STATE")
      3. decision_literal_assignment- assignment whose value is a bare decision-literal constant

    Exemption is path-level and comes from the registry (tools/authorization_registry.json):
    the frozen engine, its reuse callers, replay verification, and documented
    separate layers (C-2/C-3) are exempt; known pending defects (C-1/C-4/C-5) are
    NOT exempt and are expected to warn until their migration commit resolves them.

USAGE
    python3 tools/check_single_engine.py                 # scan the repository (warn-only)
    python3 tools/check_single_engine.py --root DIR      # scan an alternate root (used by the self-test)
    python3 tools/check_single_engine.py --registry FILE # use an alternate registry
    python3 tools/check_single_engine.py --quiet         # summary only
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import namedtuple
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
DEFAULT_REGISTRY = TOOLS_DIR / "authorization_registry.json"

# Names that, when assigned a locally-computed value, denote an authorization outcome.
AUTH_OUTPUT_NAMES = {
    "gamma_g", "gamma_class", "pi", "permit", "yhat_permit", "compensatory_permit",
}
# The two canonical decision literals.
DECISION_LITERALS = {"PERMIT", "SAFE_STATE"}
# The single frozen engine entry point; RHS that reduces to a call to this is REUSE, not a defect.
ENGINE_FUNC = "evaluate_decision"

# Directory/segment names that are never scanned.
EXCLUDE_PARTS = {".venv", "__pycache__", ".git", "tests", "tools", "archive"}

Finding = namedtuple("Finding", ["lineno", "kind", "detail"])


# --------------------------------------------------------------------------- #
# AST helpers
# --------------------------------------------------------------------------- #
def _target_id(target: ast.AST):
    """Return the leading identifier a target binds to (Name/Attribute/Subscript base)."""
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Subscript):
        base = target.value
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
    return None


def _iter_target_ids(target: ast.AST):
    """Yield identifiers for a target, flattening tuple/list targets."""
    if isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _iter_target_ids(elt)
    else:
        tid = _target_id(target)
        if tid is not None:
            yield tid


def _rhs_reduces_to_engine_call(value: ast.AST) -> bool:
    """True if the expression contains a call to the frozen engine (REUSE, not a defect)."""
    for sub in ast.walk(value):
        if isinstance(sub, ast.Call):
            func = sub.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == ENGINE_FUNC:
                return True
    return False


def _is_decision_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value in DECISION_LITERALS


def analyze_source(code: str, filename: str = "<src>") -> list:
    """Return a list of Finding for a single source string. Pure; no I/O.

    A SyntaxError yields no findings (a non-parsing file is out of scope for a
    warn-only guardrail); the caller may note the skip.
    """
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError:
        return []

    findings = []
    seen = set()  # (lineno, kind) dedupe

    def add(lineno, kind, detail):
        key = (lineno, kind)
        if key not in seen:
            seen.add(key)
            findings.append(Finding(lineno, kind, detail))

    for node in ast.walk(tree):
        # 1. assignment to an authorization-output name (not sourced from the engine)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            ids = set()
            for t in targets:
                ids.update(_iter_target_ids(t))
            hit = ids & AUTH_OUTPUT_NAMES
            value = node.value
            if hit and value is not None and not _rhs_reduces_to_engine_call(value):
                add(node.lineno, "auth_output_assignment",
                    "assigns " + ", ".join(sorted(hit)) + " without evaluate_decision()")
            # 3. bare decision-literal assignment (e.g. Status = "SAFE_STATE")
            if value is not None and _is_decision_literal(value):
                add(node.lineno, "decision_literal_assignment",
                    'assigns bare decision literal "%s"' % value.value)

        # 2. decision-literal selection: X if cond else Y with both branches decision literals
        if isinstance(node, ast.IfExp) and _is_decision_literal(node.body) and _is_decision_literal(node.orelse):
            add(node.lineno, "decision_literal_selection",
                'selects "%s"/"%s" by condition' % (node.body.value, node.orelse.value))

    findings.sort(key=lambda f: (f.lineno, f.kind))
    return findings


# --------------------------------------------------------------------------- #
# Registry + tree scan
# --------------------------------------------------------------------------- #
def load_registry(path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def exempt_paths(registry: dict) -> set:
    return {s["path"] for s in registry.get("sites", []) if s.get("exempt") is True}


def registry_index(registry: dict) -> dict:
    return {s["path"]: s for s in registry.get("sites", [])}


def _is_scannable(rel_parts) -> bool:
    return not any(part in EXCLUDE_PARTS for part in rel_parts)


def scan_tree(root, exempt: set) -> dict:
    """Return {relpath: [Finding, ...]} for scannable, non-exempt .py files under root."""
    root = Path(root).resolve()
    results = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        rel_parts = path.relative_to(root).parts
        if not _is_scannable(rel_parts):
            continue
        if rel in exempt:
            continue
        try:
            code = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        findings = analyze_source(code, filename=rel)
        if findings:
            results[rel] = findings
    return results


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Local warn-only guardrail: detect authorization computed outside the frozen engine."
    )
    p.add_argument("--root", default=str(REPO_ROOT), help="Directory to scan (default: repository root).")
    p.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Path to the authorization registry JSON.")
    p.add_argument("--quiet", action="store_true", help="Print the summary only.")
    p.add_argument(
        "--mode", choices=("warn", "strict"), default="warn",
        help="Operating mode. 'warn' (default): report findings, never block (exit 0). "
        "'strict': exit 1 if any UNREGISTERED file computes authorization outside the frozen "
        "engine (a NEW competing implementation); documented known-pending defects "
        "(C-2/C-3/C-5) remain warn-only until their migration commit. Strict is the single "
        "enforcement mode; its scope may tighten in future commits without adding new flags.",
    )
    p.add_argument(
        "--enforce-unregistered", action="store_true",
        help="DEPRECATED alias for --mode strict (kept for backward compatibility).",
    )
    return p


def _resolve_mode(args) -> str:
    """Effective mode: --mode, with the deprecated --enforce-unregistered alias forcing strict."""
    return "strict" if getattr(args, "enforce_unregistered", False) else args.mode


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    registry = load_registry(args.registry)
    exempt = exempt_paths(registry)
    index = registry_index(registry)

    results = scan_tree(args.root, exempt)

    print("=" * 70)
    print("  single-authorization-engine guardrail  (WARN-ONLY, exit 0)")
    print("  registry v%s (schema %s)" % (
        registry.get("registry_version", "?"), registry.get("schema_version", "?")))
    print("=" * 70)

    known_pending = 0
    unregistered = 0
    total_findings = 0
    for rel in sorted(results):
        findings = results[rel]
        total_findings += len(findings)
        entry = index.get(rel)
        if entry is not None:
            known_pending += 1
            label = "KNOWN [%s / %s]" % (entry.get("classification", "?"), entry.get("status", "?"))
        else:
            unregistered += 1
            label = "UNREGISTERED -- potential NEW competing authorization implementation"
        print("\n  %s  (%s)" % (rel, label))
        if not args.quiet:
            for f in findings:
                print("      %s:%d  %s  -- %s" % (rel, f.lineno, f.kind, f.detail))

    print("\n" + "-" * 70)
    print("  files flagged        : %d  (known-pending %d, unregistered %d)"
          % (len(results), known_pending, unregistered))
    print("  total constructs     : %d" % total_findings)
    if unregistered:
        print("  NOTE: %d UNREGISTERED file(s) compute authorization outside the frozen engine." % unregistered)
        print("        Review each: route through evaluate_decision(), or (if a legitimate")
        print("        separate layer) record it in tools/authorization_registry.json.")
    if _resolve_mode(args) == "strict":
        blocking = unregistered > 0
        print("  mode                 : STRICT (blocks NEW competing engines only; "
              "known-pending stay warn)")
        print("  result               : %s" % ("FAIL — unregistered competing implementation(s) found"
                                               if blocking else "PASS — 0 unregistered"))
        print("=" * 70)
        return 1 if blocking else 0
    print("  mode                 : WARN-ONLY (this guardrail never blocks; exit 0)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
