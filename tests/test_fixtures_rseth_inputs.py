#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — crossing tests: rsETH 2026-04 case inputs <-> declared sources.

The fixture ``fixtures/agents/rseth-2026-04/run_inputs.json`` follows the
frozen agent-case schema of ``fixtures/agents/usdc-2023-03/run_inputs.json``.
Rule of the repo: **no measured figure is hand-copied without a source** —
every figure row carries ``source_ref`` (``evidence:<file>#<json-path>``,
``fixture:<file>#<json-path>`` or ``doc:<file>#<anchor>`` + ``source_probe``)
and these tests cross fixture against source at runtime, like the ground-truth
crossing of ``tests/test_benchmark_ab.py`` (``bench.verify_ground_truth``).

Coverage:

* every declared ``source_ref`` resolves (file present, JSON path present,
  documentation probe present);
* every figure row equals **exactly** its declared source value;
* every numeric value anywhere in the fixture resolves to a declared source
  (snapshot facts included — a fact without provenance fails);
* every scenario timestamp appears in the sources;
* the document fixture carries no orphan figure (every digit group appears in
  the source texts);
* cross-source agreement on the episode anchors (freeze block, saturation,
  utilisation) across the episode file, the graph fixture and the project
  documentation;
* a forged figure is detected (mutated copy), never silently accepted;
* the derived corpus ``corpus_rseth.csv`` matches the episode series
  (re-derived from the source at runtime, never hard-coded);
* the fixture is consumable by the real fixture tool source (P0-1).

Run: python -m unittest tests.test_fixtures_rseth_inputs
"""

import csv
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

FIXTURE_PATH = os.path.join(ROOT, "fixtures", "agents", "rseth-2026-04",
                            "run_inputs.json")
CORPUS_PATH = os.path.join(ROOT, "fixtures", "agents", "rseth-2026-04",
                           "corpus_rseth.csv")
EPISODE_PATH = os.path.join(ROOT, "evidence", "episode_rseth_2026-04.json")
GRAPH_PATH = os.path.join(ROOT, "fixtures", "graphs", "rseth_2026-04.json")
SOURCE_NOTE_PATH = os.path.join(ROOT, "fixtures", "sources",
                                "RSETH_MEASURE_2.md")

#: The frozen case-input schema of the usdc case (fixture/agents/<case>/).
SCHEMA = "orvyren/agent-case/v1"
TOOL_BUCKETS = ["chain", "documents", "prices", "signals", "snapshot", "supply"]


# ---------------------------------------------------------------------------
# Source resolution helpers
# ---------------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def split_source_ref(ref):
    """``scheme:file#locator`` -> (scheme, file, locator)."""
    scheme, _, rest = str(ref).partition(":")
    name, _, locator = rest.partition("#")
    return scheme.strip(), name.strip(), locator.strip()


def source_path(scheme, name):
    if scheme == "evidence":
        return os.path.join(ROOT, "evidence", name)
    return os.path.join(ROOT, name)


def split_json_path(path):
    """Split a locator on dots **outside** brackets; brackets keep dots.

    Supported segments: ``key`` · ``["key.with.dots"]`` · ``key[field=value]``.
    """
    segments, current, depth = [], "", 0
    for char in str(path):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        if char == "." and depth == 0:
            segments.append(current)
            current = ""
        else:
            current += char
    if current:
        segments.append(current)
    return segments


def resolve_json_path(data, path):
    """Resolve the fixture locator against a parsed JSON document."""
    node = data
    for segment in split_json_path(path):
        segment = segment.strip()
        if segment.startswith("[") and segment.endswith("]"):
            node = _bracket_step(node, segment[1:-1].strip(), segment)
            continue
        key, bracket, rest = segment.partition("[")
        if bracket:
            if key:
                node = node[key]
            node = _bracket_step(node, rest.rstrip("]").strip(), segment)
            continue
        node = node[segment]
    return node


def _bracket_step(node, inner, segment):
    """``["key.with.dots"]`` -> mapping item; ``field=value`` -> list item."""
    if inner.startswith('"') and inner.endswith('"'):
        return node[inner[1:-1]]
    field, _, value = inner.partition("=")
    if not isinstance(node, list):
        raise AssertionError("not a list at %r" % segment)
    matches = [row for row in node
               if isinstance(row, dict) and str(row.get(field)) == value]
    if len(matches) != 1:
        raise AssertionError("selector %r matched %d row(s)"
                             % (segment, len(matches)))
    return matches[0]


def normalize_digit_groups(text):
    """Remove spaces between digits (``1 686`` -> ``1686``), keep the rest."""
    return re.sub(r"(?<=\d)[\s\u00a0\u202f](?=\d)", "", str(text))


def number_renderings(value):
    """Candidate literal renderings of a figure in FR/EN documentation text."""
    renderings = []
    number = float(value)
    if number.is_integer():
        renderings.append(str(int(number)))
    renderings.append(repr(number))
    renderings.append("%.10f" % number)
    renderings.append("%.10g" % number)
    expanded = []
    for rendering in renderings:
        expanded.append(rendering)
        expanded.append(rendering.replace(".", ","))
        if rendering.startswith("-"):
            expanded.append(rendering[1:])
            expanded.append("\u2212" + rendering[1:])
    return [item for item in dict.fromkeys(expanded) if item]


def doc_contains_value(text, probe, value):
    """True iff ``value`` appears near ``probe`` in the documentation."""
    normalized = normalize_digit_groups(text)
    needle = normalize_digit_groups(probe)
    index = normalized.find(needle)
    if index < 0:
        return False
    window = normalized[max(0, index - 300): index + len(needle) + 300]
    for rendering in number_renderings(value):
        if re.search(r"(?<![\d.,])" + re.escape(rendering) + r"(?![\d])",
                     window):
            return True
    return False


def figure_rows(fixture):
    """Every row of the fixture carrying a figure + its source_ref."""
    rows = []
    buckets = fixture.get("tool_fixtures", {})
    for bucket in TOOL_BUCKETS:
        entries = buckets.get(bucket) or {}
        if not isinstance(entries, dict):
            continue
        for key in sorted(entries):
            value = entries[key]
            batch = value if isinstance(value, list) else [value]
            for row in batch:
                if isinstance(row, dict) and "value" in row:
                    rows.append((bucket, key, row))
    return rows


def row_cross_errors(fixture):
    """Every figure row that does NOT match its declared source."""
    errors = []
    for bucket, key, row in figure_rows(fixture):
        ref = row.get("source_ref") or row.get("ref") or row.get("url")
        if not ref:
            errors.append("%s|%s: figure without source_ref" % (bucket, key))
            continue
        scheme, name, locator = split_source_ref(ref)
        path = source_path(scheme, name)
        if not os.path.isfile(path):
            errors.append("%s|%s: source file missing %s" % (bucket, key, path))
            continue
        if scheme == "doc":
            if not doc_contains_value(load_text(path),
                                      row.get("source_probe") or "", row["value"]):
                errors.append("%s|%s: value %r not found at probe %r in %s"
                              % (bucket, key, row["value"],
                                 row.get("source_probe"), name))
            continue
        try:
            resolved = resolve_json_path(load_json(path), locator)
        except (KeyError, IndexError, AssertionError, ValueError) as exc:
            errors.append("%s|%s: unresolvable ref %s (%s)"
                          % (bucket, key, ref, exc))
            continue
        if type(resolved) not in (int, float) or isinstance(resolved, bool):
            errors.append("%s|%s: source %s is not a figure" % (bucket, key, ref))
            continue
        if float(resolved) != float(row["value"]):
            errors.append("%s|%s: %r != source %r (%s)"
                          % (bucket, key, row["value"], resolved, ref))
    return errors


def ref_resolve_errors(fixture):
    """Every declared source_ref of the fixture that does not resolve."""
    errors = []
    refs = []
    for bucket, key, row in figure_rows(fixture):
        refs.append(row.get("source_ref") or row.get("ref") or row.get("url"))
    snapshot = (fixture.get("tool_fixtures", {}) or {}).get("snapshot", {})
    for ref in snapshot.get("refs", []) or []:
        refs.append(ref)
    for ref in sorted({ref for ref in refs if ref}):
        scheme, name, locator = split_source_ref(ref)
        path = source_path(scheme, name)
        if not os.path.isfile(path):
            errors.append("%s: source file missing" % ref)
            continue
        if scheme == "doc":
            if not normalize_digit_groups(locator):
                errors.append("%s: empty anchor" % ref)
            continue
        try:
            resolve_json_path(load_json(path), locator)
        except (KeyError, IndexError, AssertionError, ValueError) as exc:
            errors.append("%s: unresolvable (%s)" % (ref, exc))
    return errors


def numeric_leaves(node, path=""):
    """Every numeric leaf of the fixture with its location."""
    found = []
    if isinstance(node, dict):
        for key in sorted(node):
            found.extend(numeric_leaves(node[key], "%s.%s" % (path, key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(numeric_leaves(item, "%s[%d]" % (path, index)))
    elif isinstance(node, bool):
        return found
    elif isinstance(node, (int, float)):
        found.append((path, float(node)))
    return found


def verified_value_set(fixture):
    """Values proven against a source (figure rows)."""
    values = set()
    for bucket, key, row in figure_rows(fixture):
        values.add(float(row["value"]))
    return values


def timestamp_strings(node, key_name=""):
    """Scenario timestamps (ts / as_of / *_utc / window_label) to be sourced."""
    found = []
    interesting = key_name in ("ts", "as_of", "window_label") \
        or key_name.endswith("_utc")
    if interesting and key_name != "pinned_created_at" and isinstance(node, str):
        found.append(node)
    if isinstance(node, dict):
        for key in sorted(node):
            found.extend(timestamp_strings(node[key], key))
    elif isinstance(node, list):
        for item in node:
            found.extend(timestamp_strings(item, key_name))
    return found


class SourceFilesTest(unittest.TestCase):
    """The declared sources must exist before anything is crossed."""

    def test_declared_source_files_are_present(self):
        for path in (FIXTURE_PATH, EPISODE_PATH, GRAPH_PATH, SOURCE_NOTE_PATH):
            self.assertTrue(os.path.isfile(path), path)


class FixtureSchemaTest(unittest.TestCase):
    """The case input keeps the frozen schema of the usdc case."""

    def setUp(self):
        self.fixture = load_json(FIXTURE_PATH)

    def test_schema_and_top_level_keys(self):
        self.assertEqual(self.fixture["schema"], SCHEMA)
        self.assertEqual(self.fixture["case_id"], "rseth-2026-04")
        for key in ("note", "pinned_created_at", "snapshot", "lacunes",
                    "hypotheses", "tool_fixtures"):
            self.assertIn(key, self.fixture)

    def test_tool_fixture_buckets_are_the_frozen_six(self):
        self.assertEqual(sorted(self.fixture["tool_fixtures"]), TOOL_BUCKETS)

    def test_snapshot_facts_and_refs(self):
        snapshot = self.fixture["snapshot"]
        self.assertEqual(snapshot["as_of"], "2026-04-18T19:03:59Z")
        self.assertIn("facts", snapshot)
        tool_snapshot = self.fixture["tool_fixtures"]["snapshot"]
        self.assertTrue(tool_snapshot["refs"])
        self.assertEqual(snapshot["ref"], tool_snapshot["ref"])


class CrossingTest(unittest.TestCase):
    """Fixture figures <-> declared sources (runtime crossing)."""

    def setUp(self):
        self.fixture = load_json(FIXTURE_PATH)

    def test_every_source_ref_resolves(self):
        self.assertEqual(ref_resolve_errors(self.fixture), [])

    def test_every_figure_equals_its_declared_source(self):
        self.assertEqual(row_cross_errors(self.fixture), [])

    def test_every_numeric_value_of_the_fixture_resolves_to_a_source(self):
        proven = verified_value_set(self.fixture)
        orphans = [(path, value) for path, value in numeric_leaves(self.fixture)
                   if value not in proven]
        self.assertEqual(orphans, [],
                         "fixture figures without a declared source")

    def test_every_scenario_timestamp_appears_in_the_sources(self):
        texts = [load_text(EPISODE_PATH), load_text(SOURCE_NOTE_PATH),
                 load_text(GRAPH_PATH)]
        for stamp in timestamp_strings(self.fixture):
            self.assertTrue(any(stamp in text for text in texts),
                            "timestamp %r absent from the declared sources" % stamp)

    def test_document_fixture_carries_no_orphan_figure(self):
        documents = self.fixture["tool_fixtures"]["documents"]
        sources = normalize_digit_groups(
            load_text(EPISODE_PATH) + load_text(SOURCE_NOTE_PATH) + load_text(GRAPH_PATH))
        for url in sorted(documents):
            body = normalize_digit_groups(documents[url])
            for token in re.findall(r"\d+(?:\.\d+)?(?:e-?\d+)?", body):
                self.assertIn(token, sources,
                              "document %s carries an unsourced figure %r"
                              % (url, token))

    def test_forged_figure_is_detected(self):
        forged = json.loads(json.dumps(self.fixture))
        rows = forged["tool_fixtures"]["prices"]["chainlink|rsETH-USD"]
        rows[0]["value"] = rows[0]["value"] + 1.0
        errors = row_cross_errors(forged)
        self.assertTrue(errors, "a forged figure must be refused")
        self.assertIn("!= source", errors[0])

    def test_forged_snapshot_fact_is_detected(self):
        forged = json.loads(json.dumps(self.fixture))
        forged["snapshot"]["facts"]["freeze_first_frozen_block"] = 24909999
        proven = verified_value_set(forged)
        orphans = [(path, value) for path, value in numeric_leaves(forged)
                   if value not in proven]
        self.assertTrue(orphans, "a forged fact must leave the proven set")


class CrossSourceAgreementTest(unittest.TestCase):
    """The episode anchors agree across the three on-disk sources."""

    def test_freeze_block_agrees_everywhere(self):
        fixture = load_json(FIXTURE_PATH)
        episode = load_json(EPISODE_PATH)
        graph = load_json(GRAPH_PATH)
        block = fixture["snapshot"]["facts"]["freeze_first_frozen_block"]
        self.assertEqual(block,
                         episode["headline"]["rsETH_frozen_transition_block"])
        self.assertEqual(block,
                         episode["freeze_transition"]["first_frozen_block"])
        freeze_records = [row for row in graph["records"]
                          if row["relation_id"] == "rseth-freeze-constrains-market"]
        self.assertEqual(len(freeze_records), 1)
        self.assertEqual(block, freeze_records[0]["payload"]["block"])
        self.assertIn("block 24 908 723", load_text(SOURCE_NOTE_PATH))

    def test_saturation_and_utilisation_agree_with_the_episode(self):
        fixture = load_json(FIXTURE_PATH)
        episode = load_json(EPISODE_PATH)
        facts = fixture["snapshot"]["facts"]
        self.assertEqual(facts["supply_cap_saturation_ratio"],
                         episode["headline"]["cap_ratio_max"])
        self.assertEqual(facts["rseth_utilisation_at_freeze"],
                         episode["series"]["2026-04-18T19:03:59Z"]["rsETH"]
                         ["utilisation"])
        # The counter-intuitive claim of the old briefs is refuted on disk:
        # the rsETH reserve was almost unused (~0.008 %), never at 100 %.
        self.assertLess(facts["rseth_utilisation_at_freeze"], 0.001)
        self.assertIn("0,008 %", load_text(SOURCE_NOTE_PATH))


class HypothesesAndGapsTest(unittest.TestCase):
    """Concurrent hypotheses (one counter-intuitive) + explicit lacunae."""

    def setUp(self):
        self.fixture = load_json(FIXTURE_PATH)

    def test_at_least_three_hypotheses_with_one_counter_intuitive(self):
        hypotheses = self.fixture["hypotheses"]
        self.assertGreaterEqual(len(hypotheses), 3)
        counter = [row for row in hypotheses if row.get("counter_intuitive")]
        self.assertEqual(len(counter), 1, "exactly one counter-intuitive rival")
        for row in hypotheses:
            self.assertLessEqual(len(row["enonce"]), 240,
                                 "crit/v1 enonce limit (240 chars)")
            self.assertTrue(row["criteres"].get("S"))
            self.assertTrue(row["criteres"].get("R"))
            self.assertIn(row["etat"],
                          ("UNDER_TEST", "SUPPORTED", "REFUTED", "INCONCLUSIVE"))
        ids = [row["id"] for row in hypotheses]
        self.assertEqual(len(ids), len(set(ids)))

    def test_lacunes_are_explicit(self):
        lacunes = self.fixture["lacunes"]
        self.assertGreaterEqual(len(lacunes), 3)
        ids = [row["lacune_id"] for row in lacunes]
        self.assertEqual(len(ids), len(set(ids)))
        for row in lacunes:
            self.assertTrue(row["question"].strip())
        joined = " ".join(row["question"] for row in lacunes)
        self.assertIn("market", joined.lower())


class DerivedCorpusTest(unittest.TestCase):
    """The derived corpus matches the episode series (re-derived at runtime)."""

    def test_corpus_matches_the_episode_series(self):
        episode = load_json(EPISODE_PATH)
        expected = []
        for key in sorted(episode["series"]):
            state = episode["series"][key].get("rsETH") or {}
            price = state.get("oracle_price")
            if price is None:
                continue
            expected.append((key, float(price)))
        self.assertTrue(os.path.isfile(CORPUS_PATH),
                        "run scripts/run_scenario_rseth.py --materialize-corpus")
        with open(CORPUS_PATH, "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), len(expected))
        for row, (key, price) in zip(rows, expected):
            self.assertEqual(row["timestamp_utc"], key.replace("Z", "+00:00"))
            self.assertEqual(float(row["value"]), price)
            self.assertEqual(
                row["extra"],
                "source_ref=evidence/episode_rseth_2026-04.json"
                "#series[\"%s\"].rsETH.oracle_price" % key)
            self.assertIn(row["venue"], ("aave_oracle",))
        self.assertEqual(rows[0]["retrieved_at"],
                         episode["meta"]["generated_utc"].replace("Z", "+00:00"))


class ToolSourceCompatibilityTest(unittest.TestCase):
    """The fixture is consumable by the real fixture tool source (P0-1)."""

    def test_fixture_source_serves_the_case_buckets(self):
        from orvyren.agents.tool_sources import FixtureSource
        fixture = load_json(FIXTURE_PATH)
        source = FixtureSource(fixture["tool_fixtures"])
        prices = source.prices("chainlink", "rsETH-USD")
        self.assertTrue(prices.ok)
        self.assertTrue(prices.observations[0]["source_ref"].startswith(
            "evidence:"))
        market = source.prices("market", "rsETH-USD")
        self.assertTrue(market.ok)
        self.assertEqual(market.observations[0]["value"], 1686)
        supply = source.supply("rseth")
        self.assertTrue(supply.ok)
        chain = source.chain(
            "ethereum", "0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7")
        self.assertTrue(chain.ok)
        self.assertTrue(any(row.get("param") == "isFrozen_first_frozen_block"
                            for row in chain.observations))
        signal = source.signal("supply_cap_saturation_ratio")
        self.assertTrue(signal.ok)
        self.assertIn("method_ref", signal.observations[0])
        document = source.document(
            "https://example.org/rseth-kelpdao-apr2026-incident-note")
        self.assertTrue(document.ok)
        snapshot = source.snapshot()
        self.assertTrue(snapshot.ok)
        self.assertEqual(snapshot.observations[0]["ref"],
                         fixture["tool_fixtures"]["snapshot"]["ref"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
