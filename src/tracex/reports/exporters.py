"""Machine-readable exports: JSON, CSV, GraphML (Gephi/yEd), GEXF (Gephi), DOT (Graphviz), Cypher (Neo4j)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from ..analysis import Investigation
from ..utils import iso

_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(v):
    """Neutralise spreadsheet formula injection from externally supplied strings."""
    if isinstance(v, str) and v.startswith(_FORMULA):
        return "'" + v
    return v


def _xa(v) -> str:
    return quoteattr(str(v))


def write_json(inv: Investigation, path: Path) -> None:
    path.write_text(json.dumps(inv.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(inv: Investigation, outdir: Path) -> None:
    d = inv.to_dict()
    with (outdir / "nodes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["address", "name", "category", f"received_{inv.symbol}", f"sent_{inv.symbol}", "tx_count",
                    "first_seen", "last_seen", "depth", "cluster", "taint", "is_seed", "tags"])
        for n in d["nodes"]:
            w.writerow([_csv_safe(x) for x in [n["id"], n["name"], n["category"], n["received"], n["sent"],
                                               n["tx_count"], iso(n["first_seen"]), iso(n["last_seen"]), n["depth"],
                                               n["cluster"] or "", n["taint"], n["seed"], ";".join(n["tags"])]])
    with (outdir / "edges.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", f"value_{inv.symbol}", "tx_count", "first", "last", "txids"])
        for e in d["edges"]:
            w.writerow([e["s"], e["t"], e["value"], e["count"], iso(e["first"]), iso(e["last"]), ";".join(e["txids"])])
    with (outdir / "transactions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["txid", "time", "block", "inputs", "outputs", f"total_{inv.symbol}", f"fee_{inv.symbol}", "flags"])
        for t in d["transactions"]:
            w.writerow([t["txid"], iso(t["ts"]), t["height"] or "", t["n_in"], t["n_out"], t["total"], t["fee"],
                        ";".join(t["flags"])])
    with (outdir / "findings.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["severity", "kind", "title", "detail", "txids", "addresses"])
        for x in d["findings"]:
            w.writerow([_csv_safe(v) for v in [x["severity"], x["kind"], x["title"], x["detail"],
                                               ";".join(x["txids"]), ";".join(x["addresses"])]])


def write_graphml(inv: Investigation, path: Path) -> None:
    d = inv.to_dict()
    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    for i, (k, t) in enumerate([("name", "string"), ("category", "string"), ("received", "double"), ("sent", "double"),
                                ("tx_count", "int"), ("depth", "int"), ("cluster", "int"), ("taint", "double"),
                                ("seed", "boolean")]):
        o.append(f'<key id="n_{k}" for="node" attr.name="{k}" attr.type="{t}"/>')
    o += ['<key id="e_value" for="edge" attr.name="value" attr.type="double"/>',
          '<key id="e_count" for="edge" attr.name="tx_count" attr.type="int"/>',
          '<graph id="G" edgedefault="directed">']
    for n in d["nodes"]:
        o.append(f'<node id={_xa(n["id"])}>')
        for k in ("name", "category", "received", "sent", "tx_count", "depth", "taint"):
            o.append(f'<data key="n_{k}">{escape(str(n[k]))}</data>')
        o.append(f'<data key="n_cluster">{n["cluster"] or 0}</data>')
        o.append(f'<data key="n_seed">{str(n["seed"]).lower()}</data></node>')
    for i, e in enumerate(d["edges"]):
        o.append(f'<edge id="e{i}" source={_xa(e["s"])} target={_xa(e["t"])}>'
                 f'<data key="e_value">{e["value"]}</data><data key="e_count">{e["count"]}</data></edge>')
    o += ["</graph>", "</graphml>"]
    path.write_text("\n".join(o), encoding="utf-8")


def write_gexf(inv: Investigation, path: Path) -> None:
    d = inv.to_dict()
    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<gexf xmlns="http://gexf.net/1.3" version="1.3"><graph defaultedgetype="directed">',
         '<attributes class="node"><attribute id="0" title="category" type="string"/>'
         '<attribute id="1" title="taint" type="double"/><attribute id="2" title="cluster" type="integer"/>'
         '<attribute id="3" title="volume" type="double"/></attributes><nodes>']
    for n in d["nodes"]:
        o.append(f'<node id={_xa(n["id"])} label={_xa(n["name"] or n["short"])}><attvalues>'
                 f'<attvalue for="0" value={_xa(n["category"])}/><attvalue for="1" value="{n["taint"]}"/>'
                 f'<attvalue for="2" value="{n["cluster"] or 0}"/><attvalue for="3" value="{n["received"] + n["sent"]}"/>'
                 '</attvalues></node>')
    o.append("</nodes><edges>")
    for i, e in enumerate(d["edges"]):
        o.append(f'<edge id="{i}" source={_xa(e["s"])} target={_xa(e["t"])} weight="{e["value"]}"/>')
    o.append("</edges></graph></gexf>")
    path.write_text("\n".join(o), encoding="utf-8")


def write_dot(inv: Investigation, path: Path) -> None:
    d = inv.to_dict()
    cats = d["categories"]
    o = ["digraph TraceX {", '  rankdir=LR; bgcolor="white"; node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
         '  edge [fontname="Helvetica", fontsize=8, color="#64748b"];']
    for n in d["nodes"]:
        lab = (n["name"] or n["short"]).replace('"', "'")
        shape = "doublecircle" if n["seed"] else "box"
        o.append(f'  "{n["id"]}" [label="{lab}", fillcolor="{cats[n["category"]]["color"]}33", '
                 f'color="{cats[n["category"]]["color"]}", shape={shape}];')
    for e in d["edges"]:
        o.append(f'  "{e["s"]}" -> "{e["t"]}" [label="{e["value"]:.4g} {inv.symbol}", penwidth={min(5, 0.6 + e["value"] ** 0.5):.2f}];')
    o.append("}")
    path.write_text("\n".join(o), encoding="utf-8")


def write_cypher(inv: Investigation, path: Path) -> None:
    d = inv.to_dict()
    q = lambda s: json.dumps(str(s))
    o = ["// Neo4j import generated by TraceX", "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Address) REQUIRE a.id IS UNIQUE;"]
    for n in d["nodes"]:
        o.append(f'MERGE (a:Address {{id:{q(n["id"])}}}) SET a.name={q(n["name"])}, a.category={q(n["category"])}, '
                 f'a.taint={n["taint"]}, a.depth={n["depth"]}, a.cluster={n["cluster"] or 0}, a.seed={str(n["seed"]).lower()};')
    for e in d["edges"]:
        o.append(f'MATCH (s:Address {{id:{q(e["s"])}}}), (t:Address {{id:{q(e["t"])}}}) '
                 f'MERGE (s)-[r:SENT]->(t) SET r.value={e["value"]}, r.tx_count={e["count"]};')
    path.write_text("\n".join(o), encoding="utf-8")
