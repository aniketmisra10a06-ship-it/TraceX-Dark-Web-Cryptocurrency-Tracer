import json
import xml.etree.ElementTree as ET

import pytest

from tracex.analysis import investigate
from tracex.graph import TxGraph
from tracex.heuristics import detect_coinjoin, likely_change
from tracex.labels import LabelDB, Label, load_labels
from tracex.models import Leg, Tx
from tracex.providers.demo import DemoProvider, SEED_ADDRESS, a
from tracex.reports import write_all, html_report, mermaid
from tracex.taint import propagate_taint
from tracex.tracer import TraceConfig, Tracer
from tracex.cli import main


def mk(txid, ins, outs, ts=1000, chain="btc"):
    return Tx(txid, chain, ts, 1, [Leg(*i) for i in ins], [Leg(*o) for o in outs])


@pytest.fixture(scope="module")
def demo_inv():
    labels = load_labels([], include_demo=True)
    tr = Tracer(DemoProvider(), labels, TraceConfig(depth=8))
    g = tr.trace([SEED_ADDRESS])
    return investigate(g, labels, [SEED_ADDRESS])


def test_edges_are_proportional():
    g = TxGraph()
    g.add_tx(mk("t", [("A", 100), ("B", 300)], [("C", 200), ("D", 190)]))
    assert round(g.edges[("A", "C")].value) == 50
    assert round(g.edges[("B", "D")].value) == 142 or round(g.edges[("B", "D")].value) == 143
    assert ("A", "A") not in g.edges


def test_coinjoin_detection():
    cj = mk("cj", [(f"i{i}", 100) for i in range(5)], [(f"o{i}", 99) for i in range(5)] + [("chg", 7)])
    assert detect_coinjoin(cj)["participants"] == 5
    normal = mk("n", [("a", 100), ("b", 50)], [("c", 120), ("d", 20)])
    assert detect_coinjoin(normal) is None


def test_change_detection_prefers_fresh_non_round():
    tx = mk("x", [("in1", 5 * 10 ** 8)], [("pay", 10 ** 8), ("chg", 399_990_000)])
    res = likely_change(tx, {"pay": "other", "chg": "x"})
    assert res and res[0] == "chg"


def test_taint_haircut_vs_poison():
    g = TxGraph()
    g.add_tx(mk("1", [("bad", 100)], [("m", 100)], ts=1))
    g.add_tx(mk("2", [("m", 100), ("clean", 100)], [("out", 200)], ts=2))
    h = propagate_taint(g, {"bad": 1.0}, "haircut")
    p = propagate_taint(g, {"bad": 1.0}, "poison")
    assert h["out"] == pytest.approx(0.5)
    assert p["out"] == 1.0
    with pytest.raises(ValueError):
        propagate_taint(g, {}, "nope")


def test_demo_end_to_end(demo_inv):
    inv = demo_inv
    kinds = {f.kind for f in inv.heur.findings}
    assert {"coinjoin", "peel_chain", "cluster", "labeled_entity"} <= kinds
    assert len(inv.heur.peel_chains) == 1 and len(inv.heur.peel_chains[0].txids) == 4
    # the two ransom wallets were co-spent -> one cluster
    assert {a("ransom_1"), a("ransom_2")} <= set(inv.heur.clusters[0].members)
    r = inv.risk[SEED_ADDRESS]
    assert r.score >= 90 and r.level == "severe"
    # coinjoin inputs must NOT have been merged into a cluster
    assert all(a("user_1") not in c.members for c in inv.heur.clusters)
    # taint is diluted by the CoinJoin but still present downstream
    assert 0 < inv.taint[a("exch_nokyc")] < 1


def test_no_depth_defaults_to_seed_column(demo_inv):
    # incidental coinjoin participants must not sit in the seed column
    assert demo_inv.graph.nodes[a("user_1")].depth != 0


def test_reports_written_and_valid(demo_inv, tmp_path):
    files = write_all(demo_inv, str(tmp_path))
    names = {f.name for f in files}
    assert {"report.html", "report.md", "graph.json", "graph.graphml", "graph.gexf", "graph.dot",
            "nodes.csv", "edges.csv", "manifest.json", "flow.mmd", "neo4j.cypher"} <= names
    ET.parse(tmp_path / "graph.graphml")
    ET.parse(tmp_path / "graph.gexf")
    man = json.loads((tmp_path / "manifest.json").read_text())
    assert len(man["files"]["report.html"]) == 64
    assert "```mermaid" in (tmp_path / "report.md").read_text()


def test_html_embeds_safely():
    labels = LabelDB()
    labels.add(Label("evil", "</script><img src=x onerror=alert(1)>", "scam"))
    g = TxGraph()
    g.add_tx(mk("t", [("evil", 10)], [("b", 9)]))
    inv = investigate(g, labels, ["evil"])
    html = html_report.build(inv)
    assert "</script><img" not in html
    assert "Content-Security-Policy" in html


def test_csv_formula_injection(tmp_path):
    labels = LabelDB()
    labels.add(Label("x", "=HYPERLINK(\"http://e\")", "scam"))
    g = TxGraph()
    g.add_tx(mk("t", [("x", 10)], [("y", 9)]))
    inv = investigate(g, labels, ["x"])
    write_all(inv, str(tmp_path), ["csv"])
    assert "'=HYPERLINK" in (tmp_path / "nodes.csv").read_text()


def test_label_loader_validation(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("address,name,category,confidence\nabc,Foo,mixer,0.7\n,NoAddr,mixer,1\nxyz,Bad,notacat,2\n")
    db = load_labels([str(p)])
    assert len(db) == 2
    assert db.primary("xyz").category == "unlabeled" and db.primary("xyz").confidence == 1.0
    assert len(db.warnings) == 2


def test_mermaid_sankey_acyclic(demo_inv):
    sk = mermaid.sankey(demo_inv)
    assert sk.startswith("sankey-beta")


def test_cli_demo(tmp_path, capsys):
    rc = main(["demo", "-o", str(tmp_path / "o"), "-f", "json", "md"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "By Aniket Misra" in err
    assert (tmp_path / "o" / "graph.json").exists()


def test_non_https_provider_refused():
    from tracex.providers.http import HttpClient, ProviderError
    with pytest.raises(ProviderError):
        HttpClient("http://example.com")
