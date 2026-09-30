from pathlib import Path

import pytest
from nps_core.codegraph.indexer import build_codegraph


def write_module(tmp_path):
    src_pkg = tmp_path / 'src' / 'pkg'
    src_pkg.mkdir(parents=True, exist_ok=True)
    (src_pkg / '__init__.py').touch()
    module_py = src_pkg / 'module.py'
    with open(module_py, 'w', encoding='utf-8') as f:
        f.write("""
import os
from json import dumps

class Outer:
    def method(self):
        def nested():
            pass

def top():
    pass

async def async_top():
    pass
""")


@pytest.fixture
def codegraph(monkeypatch, tmp_path):
    from nps_core.codegraph import indexer

    monkeypatch.setattr(indexer, "_git_head", lambda _root: None)
    write_module(tmp_path)
    return indexer.build_codegraph(tmp_path)


def test_build_codegraph_twice(codegraph, tmp_path):
    graph2 = build_codegraph(tmp_path)
    assert codegraph == graph2
    assert codegraph['status'] == 'UNVERSIONED'
    assert codegraph['repository_head'] is None
    assert codegraph['codegraph_commit'] is None
    assert codegraph['errors'] == []


def test_node_ids(codegraph):
    node_ids = sorted(node["id"] for node in codegraph["nodes"])
    expected_node_ids = [
        'module:pkg',
        'module:pkg.module',
        'symbol:pkg.module:Outer',
        'symbol:pkg.module:Outer.method',
        'symbol:pkg.module:Outer.method.nested',
        'symbol:pkg.module:top',
        'symbol:pkg.module:async_top'
    ]
    assert set(node_ids) >= set(expected_node_ids)
    assert node_ids == sorted(node_ids)


def test_module_paths(codegraph):
    path_dict = {node['id']: node['path'] for node in codegraph['nodes']}
    assert path_dict['module:pkg'] == 'src/pkg/__init__.py'
    assert path_dict['module:pkg.module'] == 'src/pkg/module.py'
    assert all(Path(path).as_posix() == path for path in path_dict.values())


def test_nested_symbol_edge(codegraph):
    nested_edge = {"source": "module:pkg.module", "target": "symbol:pkg.module:Outer.method.nested", "kind": "contains"}
    assert nested_edge in codegraph['edges']


def test_import_targets(codegraph):
    import_edges = [edge for edge in codegraph['edges'] if edge['kind'].startswith('import')]
    assert 'import:os' in {edge['target'] for edge in import_edges}
    assert 'import:json' in {edge['target'] for edge in import_edges}


def test_edges_sorted(codegraph):
    sorted_edges = sorted(codegraph['edges'], key=lambda x: (x['kind'], x['source'], x['target']))
    assert codegraph['edges'] == sorted_edges
