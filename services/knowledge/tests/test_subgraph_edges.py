from adapters.operations import add_edge, records_to_subgraph


def test_records_to_subgraph_uses_structural_edges() -> None:
    class FakeNode:
        def __init__(self, labels: list[str], props: dict):
            self._labels = labels
            self._props = props
            self.element_id = props.get("element_id", "internal")

        @property
        def labels(self):
            return self._labels

        def __getitem__(self, key):
            return self._props[key]

        def __iter__(self):
            return iter(self._props.items())

        def get(self, key, default=None):
            return self._props.get(key, default)

        def keys(self):
            return self._props.keys()

        def values(self):
            return self._props.values()

        def items(self):
            return self._props.items()

    record = {
        "e": FakeNode(["Entity"], {"entity_id": "e1", "canonical_name": "nickel"}),
        "c": FakeNode(["Claim"], {"claim_id": "c1", "statement": "Ni 92 %"}),
        "s": FakeNode(["SourceSpan"], {"source_span_id": "s1", "raw_text": "Ni 92 %"}),
        "d": FakeNode(["Document"], {"document_id": "d1", "title": "doc"}),
    }
    subgraph = records_to_subgraph([record])
    edge_types = {edge.edge_type for edge in subgraph.edges}
    assert "CO_OCCURS" not in edge_types
    assert "DESCRIBED_IN" in edge_types
    assert "PART_OF" in edge_types
    assert "VALIDATED_BY" in edge_types


def test_add_edge_deduplicates() -> None:
    bucket: dict = {}
    add_edge(bucket, "a", "b", "DESCRIBED_IN")
    add_edge(bucket, "a", "b", "DESCRIBED_IN")
    assert len(bucket) == 1
