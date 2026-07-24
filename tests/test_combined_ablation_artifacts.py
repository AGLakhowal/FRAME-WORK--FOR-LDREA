#!/usr/bin/env python3
"""Regression guard for the E5b (Combined Component Ablation) publication artifacts.

These tests FAIL LOUDLY if a publication artifact disappears or goes structurally invalid.
They are deliberately assertions about the EXECUTED evidence, not about the code that produces
it: if someone deletes combined_ablation.json, breaks the statistics writer, or lets a NaN into
a table, the paper silently loses its evidence — these tests make that impossible to miss.

    python3 -m unittest discover -s tests -p "test_combined_ablation*" -v
    python3 tests/test_combined_ablation_artifacts.py

REQUIRED artifacts (missing => hard failure):
    component discovery, combined_ablation.json, combined_statistics.json,
    threshold_sensitivity.json, cross_dataset_ablation.json, paper_tables/table_combined_ablation_*,
    metadata/*, reviewer_mapping.md, dashboard/combined_runtime_ablation.html
OPTIONAL artifacts (missing => skipTest, never a failure):
    paper_figures/*.pdf  (rasterised/typeset outputs are not always regenerated)

The cross-dataset physics invariant in test 5 caught a REAL state-leak bug (an online adapter
persisting calibration between configurations). Do not delete it.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CA = ROOT / "experiments" / "combined_ablation"
ABLATION = CA / "combined_ablation.json"
STATS = CA / "combined_statistics.json"
THRESH = CA / "threshold_sensitivity.json"
CROSS = CA / "cross_dataset_ablation.json"
FIGDIR = CA / "figures"
TABLES = ROOT / "paper_tables"
PAPER_FIGS = ROOT / "paper_figures"
META = ROOT / "metadata"
DASHBOARD = ROOT / "dashboard" / "combined_runtime_ablation.html"
SCI_DASHBOARD = ROOT / "SCIENTIFIC_DASHBOARD.html"
REVIEWER_MAP = ROOT / "reviewer_mapping.md"

# The five components that are actually ablated (the governance/timing stages are excluded from
# the matrix by design; see COMPONENT_REGISTRY.json `in_ablation_matrix`).
ABLATED = {"PE", "RV", "EQ", "LG", "HC"}
# The audit plane: evidence -> ledger -> hash chain. Strictly DOWNSTREAM of the decision.
AUDIT_PLANE = {"EQ", "LG", "HC"}

# Every configuration must carry all of these. A silently dropped metric is a publication defect.
REQUIRED_CONFIG_KEYS = {
    "config", "disabled_components", "disabled_codes", "n_disabled",
    "confusion_matrix", "blind_decision_accuracy",
    "undetected_risk_rate", "benign_flag_rate",
    "blind_risk_detection_recall", "evidence_completeness",
    "ledger_integrity", "hash_chain_integrity",
    "replay_determinism_rate", "replay_integrity", "revocation_compliance",
    "runtime_integrity_score", "overall_runtime_verdict",
    "latency_mean_ms", "throughput_decisions_per_s",
}


def _load(path: Path):
    with path.open() as fh:
        return json.load(fh)


def _require(tc: unittest.TestCase, path: Path):
    tc.assertTrue(path.exists(), f"REQUIRED publication artifact is missing: {path.relative_to(ROOT)}")


def _walk_nans(node, trail="$"):
    """Yield the JSON path of every NaN / Infinity in a decoded document."""
    if isinstance(node, float):
        if math.isnan(node) or math.isinf(node):
            yield trail, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_nans(v, f"{trail}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_nans(v, f"{trail}[{i}]")


class Test1ComponentDiscovery(unittest.TestCase):
    """1. Component discovery succeeds, files exist on disk, dependency graph is a DAG."""

    def setUp(self):
        try:
            import combined_ablation_discovery
        except ImportError as e:                                    # pragma: no cover
            self.fail(f"combined_ablation_discovery is not importable: {e}")
        self.registry = combined_ablation_discovery.discover()

    def test_discover_returns_at_least_five_components(self):
        comps = self.registry["components"]
        self.assertGreaterEqual(
            len(comps), 5,
            f"discover() found only {len(comps)} components; the ablation matrix needs >= 5")
        self.assertEqual(len(comps), self.registry["n_components"])
        shorts = {c["short"] for c in comps}
        self.assertTrue(ABLATED <= shorts,
                        f"ablated components {ABLATED - shorts} were not discovered")

    def test_every_implementation_file_exists_on_disk(self):
        for c in self.registry["components"]:
            p = ROOT / c["implementation_file"]
            self.assertTrue(p.exists(),
                            f"component {c['short']} points at a non-existent implementation_file: "
                            f"{c['implementation_file']}")
            self.assertGreater(p.stat().st_size, 0, f"{p} is empty")

    def test_dependency_graph_is_a_dag(self):
        deps = {c["short"]: list(c["dependencies"]) for c in self.registry["components"]}
        for s, ds in deps.items():
            for d in ds:
                self.assertIn(d, deps, f"component {s} depends on unknown component {d}")

        # iterative DFS with colouring; report the actual cycle if one exists
        WHITE, GREY, BLACK = 0, 1, 2
        colour = dict.fromkeys(deps, WHITE)

        def visit(node, stack):
            if colour[node] == GREY:
                cyc = stack[stack.index(node):] + [node]
                self.fail(f"dependency graph is NOT a DAG — cycle: {' -> '.join(cyc)}")
            if colour[node] == BLACK:
                return
            colour[node] = GREY
            for d in deps[node]:
                visit(d, stack + [node])
            colour[node] = BLACK

        for n in deps:
            visit(n, [])

        # a DAG must admit a topological order, and the registry publishes one
        order = self.registry["execution_order"]
        pos = {s: i for i, s in enumerate(order)}
        for s, ds in deps.items():
            for d in ds:
                self.assertLess(pos[d], pos[s],
                                f"execution_order violates dependency {d} -> {s}: "
                                f"{d} must precede {s}")


class Test2AllConfigurationsExecuted(unittest.TestCase):
    """2. 19 configurations executed, full metric key set, no NaN anywhere."""

    @classmethod
    def setUpClass(cls):
        if not ABLATION.exists():
            cls.doc = None
            return
        cls.doc = _load(ABLATION)

    def setUp(self):
        _require(self, ABLATION)

    def test_nineteen_configurations_baseline_singles_pairs(self):
        cfgs = self.doc["configs"]
        self.assertEqual(len(cfgs), 19, f"expected 19 executed configurations, found {len(cfgs)}")
        self.assertEqual(self.doc["n_configurations"], len(cfgs),
                         "n_configurations disagrees with the number of executed configs")

        by_order = {}
        for c in cfgs:
            by_order.setdefault(c["n_disabled"], []).append(frozenset(c["disabled_codes"]))

        self.assertEqual(len(by_order.get(0, [])), 1, "the intact baseline configuration is missing")
        self.assertEqual(set(by_order.get(0, [None])[0]), set(), "the baseline must disable nothing")

        singles = by_order.get(1, [])
        self.assertEqual(len(singles), 5, f"expected 5 single-component removals, found {len(singles)}")
        self.assertEqual({next(iter(s)) for s in singles}, ABLATED,
                         "the 5 singles must be exactly PE, RV, EQ, LG, HC")

        pairs = by_order.get(2, [])
        self.assertEqual(len(pairs), 10, f"expected all 10 pairs (C(5,2)), found {len(pairs)}")
        self.assertEqual(len(set(pairs)), 10, "duplicate pair configurations were executed")
        expected_pairs = {frozenset(p) for p in
                          [(a, b) for i, a in enumerate(sorted(ABLATED))
                           for b in sorted(ABLATED)[i + 1:]]}
        self.assertEqual(set(pairs), expected_pairs, "the pair set is not the complete C(5,2) matrix")

    def test_every_config_carries_the_full_metric_key_set(self):
        for c in self.doc["configs"]:
            missing = REQUIRED_CONFIG_KEYS - set(c)
            self.assertFalse(missing,
                             f"configuration {c.get('config')!r} is missing metric keys: "
                             f"{sorted(missing)}")

    def test_no_nan_or_infinity_anywhere_in_the_json(self):
        bad = list(_walk_nans(self.doc))
        self.assertFalse(bad, f"combined_ablation.json contains NaN/Infinity at: {bad[:10]}")
        # json.load happily accepts the literals NaN/Infinity; the file must not contain them
        raw = ABLATION.read_text()
        for token in ("NaN", "Infinity", "-Infinity"):
            self.assertNotIn(f": {token}", raw,
                             f"raw JSON contains the non-standard literal {token}")

    def test_interactions_and_registry_are_present(self):
        self.assertGreater(len(self.doc["interactions"]), 0, "no interaction effects were computed")
        for it in self.doc["interactions"]:
            for k in ("interaction_effect", "interaction_class", "observed_degradation",
                      "additive_prediction"):
                self.assertIn(k, it, f"interaction {it.get('combination')!r} lacks {k}")
        self.assertIn("component_registry", self.doc)
        self.assertEqual(self.doc["evidence_level"], "Synthetic Runtime",
                         "the evidence level of the synthetic ablation matrix must stay labelled")


class Test3StatisticsProduced(unittest.TestCase):
    """3. Every config has stats; every metric has a p_value/significance OR an explicit reason."""

    def setUp(self):
        _require(self, ABLATION)
        _require(self, STATS)
        self.ablation = _load(ABLATION)
        self.stats = _load(STATS)

    def test_an_entry_for_every_executed_configuration(self):
        executed = {c["config"] for c in self.ablation["configs"]}
        analysed = set(self.stats["configs"])
        self.assertEqual(executed, analysed,
                         f"statistics missing for {sorted(executed - analysed)}; "
                         f"unexpected extra entries {sorted(analysed - executed)}")

    def test_no_silently_missing_metric(self):
        """A metric is acceptable only if it carries a p_value, OR says why it cannot."""
        baseline = self.stats["configs"]["baseline_full_LDREA"]
        metric_names = set(baseline)
        self.assertGreater(len(metric_names), 0, "the baseline has no metrics at all")

        for cname, metrics in self.stats["configs"].items():
            absent = metric_names - set(metrics)
            self.assertFalse(absent, f"{cname} silently drops metrics {sorted(absent)}")
            for m, v in metrics.items():
                self.assertIsInstance(v, dict, f"{cname}/{m} is not a statistics block")
                has_p = "p_value" in v and "significant" in v
                has_reason = bool(v.get("undefined_reason")) or bool(v.get("not_sampled_reason"))
                self.assertTrue(
                    has_p or has_reason,
                    f"{cname}/{m} carries neither a p_value/significance nor an explicit "
                    f"undefined_reason/not_sampled_reason — a metric may never go silently missing "
                    f"(keys present: {sorted(v)})")

    def test_ledger_integrity_is_declared_deterministic_not_silently_unreported(self):
        led = self.stats["configs"]["baseline_full_LDREA"]["ledger_integrity"]
        self.assertTrue(led.get("deterministic"),
                        "ledger_integrity must be flagged deterministic")
        self.assertTrue(led.get("not_sampled_reason"),
                        "ledger_integrity has no CI/p-value; it MUST carry not_sampled_reason")

    def test_bootstrap_parameters_are_recorded(self):
        for k in ("alpha", "n_bootstrap", "bootstrap_seed", "method"):
            self.assertIn(k, self.stats, f"statistics do not record {k}")
        self.assertGreater(self.stats["n_bootstrap"], 0)

    def test_no_nan_in_statistics(self):
        bad = list(_walk_nans(self.stats))
        self.assertFalse(bad, f"combined_statistics.json contains NaN/Infinity at: {bad[:10]}")


class Test4ThresholdSensitivity(unittest.TestCase):
    """4. threshold_sensitivity.json: 5 scales + a stability block."""

    def setUp(self):
        _require(self, THRESH)
        self.doc = _load(THRESH)

    def test_five_scales(self):
        scales = self.doc["scales"]
        self.assertEqual(len(scales), 5, f"expected 5 threshold scales, found {scales}")
        self.assertIn(1.0, scales, "the unperturbed operating point (scale 1.0) must be included")

    def test_stability_block_present_and_decided(self):
        stab = self.doc.get("stability")
        self.assertIsInstance(stab, dict, "threshold_sensitivity.json has no `stability` block")
        self.assertIn("all_conclusions_stable", stab)
        self.assertIsInstance(stab["all_conclusions_stable"], bool)
        checks = stab.get("checks")
        self.assertTrue(checks, "the stability block records no per-conclusion checks")
        n_scales = len(self.doc["scales"])
        for name, chk in checks.items():
            self.assertIn("holds_at_every_scale", chk, f"check {name} reaches no verdict")
            # a check records its per-scale evidence either as a list (`per_scale`) or, for the
            # ranking check, as a scale-keyed mapping (`ranking_per_scale`). Either way, every
            # scale must be covered — a verdict without per-scale evidence is not admissible.
            per = chk.get("per_scale")
            if per is None:
                per = chk.get("ranking_per_scale")
            self.assertIsNotNone(per, f"check {name} records a verdict with no per-scale evidence")
            self.assertEqual(len(per), n_scales,
                             f"check {name} was not evaluated at every scale "
                             f"({len(per)} of {n_scales})")

    def test_no_nan(self):
        bad = list(_walk_nans(self.doc))
        self.assertFalse(bad, f"threshold_sensitivity.json contains NaN/Infinity at: {bad[:10]}")


class Test5CrossDataset(unittest.TestCase):
    """5. Cross-dataset present + the PHYSICS invariant on the audit plane.

    The ledger (EQ -> LG -> HC) is strictly DOWNSTREAM of the authorization decision. Removing it
    destroys provenance but cannot change who was permitted. Therefore, on EVERY dataset, ablating
    any subset of the audit plane must leave undetected_risk_rate EXACTLY at the baseline value.

    This assertion caught a real state-leak bug (a stateful online adapter carrying calibration
    across configurations, which perturbed decisions in audit-only ablations). KEEP IT.
    """

    def setUp(self):
        _require(self, CROSS)
        self.doc = _load(CROSS)

    def test_at_least_one_dataset(self):
        self.assertGreaterEqual(len(self.doc["datasets"]), 1,
                                "cross_dataset_ablation.json contains no datasets")
        for ds in self.doc["datasets"]:
            self.assertGreater(ds["rows_loaded"], 0, f"{ds['dataset']} loaded 0 rows")
            self.assertTrue(ds.get("configs"), f"{ds['dataset']} executed no configurations")

    def test_audit_plane_ablation_cannot_change_authorization(self):
        for ds in self.doc["datasets"]:
            name = ds["dataset"]
            base = next((c for c in ds["configs"] if c["n_disabled"] == 0), None)
            self.assertIsNotNone(base, f"{name} has no baseline configuration")
            b_fpr = base["undetected_risk_rate"]

            audit_only = [c for c in ds["configs"]
                          if c["disabled_codes"] and set(c["disabled_codes"]) <= AUDIT_PLANE]
            self.assertTrue(audit_only,
                            f"{name} ran no audit-plane-only ablation, so the invariant is untested")

            for c in audit_only:
                self.assertEqual(
                    c["undetected_risk_rate"], b_fpr,
                    f"PHYSICS INVARIANT VIOLATED on {name}: config {c['config']!r} ablates only the "
                    f"audit plane {sorted(c['disabled_codes'])} yet undetected_risk_rate moved "
                    f"{b_fpr} -> {c['undetected_risk_rate']}. The ledger is downstream of the decision "
                    f"and CANNOT change authorization — this is a state leak between configurations.")

    def test_conclusions_block_present(self):
        concl = self.doc.get("cross_dataset_conclusions")
        self.assertIsInstance(concl, dict, "no cross_dataset_conclusions block")
        self.assertIn("all_conclusions_replicate", concl)
        self.assertIsInstance(concl["all_conclusions_replicate"], bool)

    def test_no_nan(self):
        bad = list(_walk_nans(self.doc))
        self.assertFalse(bad, f"cross_dataset_ablation.json contains NaN/Infinity at: {bad[:10]}")


class Test6Tables(unittest.TestCase):
    """6. paper_tables/table_combined_ablation_{A,B,C}.{md,csv,tex} exist; LaTeX is balanced."""

    LETTERS = ("A", "B", "C")
    EXTS = ("md", "csv", "tex")

    def test_all_nine_table_files_exist_and_are_non_empty(self):
        for letter in self.LETTERS:
            for ext in self.EXTS:
                p = TABLES / f"table_combined_ablation_{letter}.{ext}"
                _require(self, p)
                self.assertGreater(p.stat().st_size, 0, f"{p.relative_to(ROOT)} is empty")

    def test_latex_environments_are_balanced(self):
        for letter in self.LETTERS:
            p = TABLES / f"table_combined_ablation_{letter}.tex"
            _require(self, p)
            tex = p.read_text()
            self.assertTrue(tex.strip(), f"{p.relative_to(ROOT)} is blank")
            for env in ("table*", "tabular"):
                nb = tex.count(r"\begin{%s}" % env)
                ne = tex.count(r"\end{%s}" % env)
                self.assertGreater(nb, 0,
                                   f"{p.relative_to(ROOT)} has no \\begin{{{env}}}")
                self.assertEqual(nb, ne,
                                 f"{p.relative_to(ROOT)}: {nb} \\begin{{{env}}} vs "
                                 f"{ne} \\end{{{env}}} — unbalanced LaTeX will not compile")

    def test_csv_tables_have_a_header_and_at_least_one_row(self):
        import csv
        for letter in self.LETTERS:
            p = TABLES / f"table_combined_ablation_{letter}.csv"
            _require(self, p)
            with p.open(newline="") as fh:
                rows = list(csv.reader(fh))
            self.assertGreaterEqual(len(rows), 2,
                                    f"{p.relative_to(ROOT)} has no data rows")


class Test7Figures(unittest.TestCase):
    """7. SVG figures parse as XML; any paper_figures PDF is a well-formed PDF."""

    def test_svg_figures_exist_and_parse_as_xml(self):
        _require(self, FIGDIR)
        svgs = sorted(FIGDIR.glob("*.svg"))
        self.assertTrue(svgs, f"no SVG figures under {FIGDIR.relative_to(ROOT)}")
        for svg in svgs:
            self.assertGreater(svg.stat().st_size, 0, f"{svg.name} is empty")
            try:
                root = ET.parse(svg).getroot()
            except ET.ParseError as e:
                self.fail(f"{svg.relative_to(ROOT)} is not well-formed XML: {e}")
            self.assertTrue(root.tag.endswith("svg"),
                            f"{svg.relative_to(ROOT)} root element is <{root.tag}>, not <svg>")

    def test_paper_figure_pdfs_are_well_formed(self):
        if not PAPER_FIGS.exists():
            self.skipTest("paper_figures/ has not been generated (optional artifact)")
        pdfs = sorted(PAPER_FIGS.glob("*.pdf"))
        if not pdfs:
            self.skipTest("no PDF figures generated yet (optional artifact; SVGs are the source)")
        for pdf in pdfs:
            head = pdf.read_bytes()
            self.assertTrue(head.startswith(b"%PDF-"),
                            f"{pdf.relative_to(ROOT)} does not start with %PDF-")
            self.assertTrue(head.rstrip().endswith(b"%%EOF"),
                            f"{pdf.relative_to(ROOT)} does not end with %%EOF (truncated PDF)")


class Test8Dashboard(unittest.TestCase):
    """8. The combined-ablation dashboard renders and is wired into SCIENTIFIC_DASHBOARD.html."""

    def test_combined_runtime_ablation_dashboard_is_non_trivial(self):
        _require(self, DASHBOARD)
        html = DASHBOARD.read_text(errors="replace")
        self.assertGreater(len(html), 2000,
                           f"{DASHBOARD.relative_to(ROOT)} is only {len(html)} bytes — it did not render")
        low = html.lower()
        self.assertIn("<html", low[:400] + low, "dashboard is not an HTML document")
        self.assertIn("ablation", low, "dashboard does not mention the ablation it is meant to show")

    def test_scientific_dashboard_contains_the_combined_runtime_ablation_section(self):
        _require(self, SCI_DASHBOARD)
        html = SCI_DASHBOARD.read_text(errors="replace")
        self.assertIn("Combined Runtime Ablation", html,
                      "SCIENTIFIC_DASHBOARD.html has lost its 'Combined Runtime Ablation' section")


class Test9Metadata(unittest.TestCase):
    """9. metadata/COMPONENT_REGISTRY.json and metadata/combined_ablation_run_metadata.json parse."""

    def test_component_registry_parses(self):
        p = META / "COMPONENT_REGISTRY.json"
        _require(self, p)
        reg = _load(p)
        self.assertGreaterEqual(reg["n_components"], 5)
        self.assertEqual(len(reg["components"]), reg["n_components"])

    def test_run_metadata_parses_and_records_provenance(self):
        p = META / "combined_ablation_run_metadata.json"
        _require(self, p)
        meta = _load(p)
        for k in ("experiment", "seed", "workload_n", "n_configurations", "host", "artifacts"):
            self.assertIn(k, meta, f"run metadata does not record {k}")
        self.assertEqual(meta["n_configurations"], 19)


class Test10ReviewerMapping(unittest.TestCase):
    """10. reviewer_mapping.md still closes the R6-ext reviewer request."""

    def test_r6_ext_is_mapped(self):
        _require(self, REVIEWER_MAP)
        text = REVIEWER_MAP.read_text(errors="replace")
        self.assertIn("R6-ext", text,
                      "reviewer_mapping.md no longer contains R6-ext — the combined-ablation "
                      "reviewer request is unclosed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
