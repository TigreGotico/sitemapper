"""Offline tests for LinkGraph construction and serialisation."""
import json
import pytest
from sitemapper.graph import LinkGraph, Node


def _sample_graph() -> LinkGraph:
    g = LinkGraph()
    home = Node(url="https://example.com/", internal=True, depth=0, status=200, title="Home")
    about = Node(url="https://example.com/about", internal=True, depth=1, status=200)
    ext = Node(url="https://external.org/page", internal=False, depth=1)
    g.add_node(home)
    g.add_node(about)
    g.add_node(ext)
    g.add_edge("https://example.com/", "https://example.com/about")
    g.add_edge("https://example.com/", "https://external.org/page")
    g.add_edge("https://example.com/about", "https://external.org/page")
    return g


def test_internal_external_sets():
    g = _sample_graph()
    assert "https://example.com/" in g.internal
    assert "https://example.com/about" in g.internal
    assert "https://external.org/page" in g.external


def test_edges():
    g = _sample_graph()
    edges = list(g.edges())
    assert ("https://example.com/", "https://example.com/about") in edges
    assert ("https://example.com/", "https://external.org/page") in edges


def test_domains():
    g = _sample_graph()
    d = g.domains()
    assert "external.org" in d
    assert d["external.org"] == 2


def test_to_dict():
    g = _sample_graph()
    d = g.to_dict()
    assert "nodes" in d
    assert "edges" in d
    assert "https://example.com/" in d["nodes"]


def test_to_json():
    g = _sample_graph()
    raw = g.to_json()
    parsed = json.loads(raw)
    assert "nodes" in parsed


def test_to_dot():
    g = _sample_graph()
    dot = g.to_dot()
    assert "digraph sitemapper" in dot
    assert "->" in dot


def test_summary():
    g = _sample_graph()
    s = g.summary()
    assert "external.org" in s
    assert "Pages crawled" in s


def test_in_out_degree():
    g = _sample_graph()
    d = g.to_dict()
    home_node = d["nodes"]["https://example.com/"]
    assert home_node["out_degree"] == 2
    ext_node = d["nodes"]["https://external.org/page"]
    assert ext_node["in_degree"] == 2
