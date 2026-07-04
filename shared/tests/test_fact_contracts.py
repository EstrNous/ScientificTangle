import pytest
from pydantic import ValidationError

from shared.contracts import (
    AliasRef,
    GeoContext,
    NormalizedDocument,
    Quantity,
    SourceSpan,
    TableEvidenceRef,
    TimeConstraint,
)


def test_quantity_accepts_optional_source_span_id() -> None:
    quantity = Quantity(value=82.0, unit="%", source_span_id="span-1")
    restored = Quantity.model_validate(quantity.model_dump())
    assert restored.source_span_id == "span-1"


def test_quantity_backward_compatible_without_source_span_id() -> None:
    payload = {"value": 1.2, "unit": "m/s", "operator": "eq"}
    quantity = Quantity.model_validate(payload)
    assert quantity.source_span_id is None


def test_geo_context_accepts_optional_source_span_id() -> None:
    geo = GeoContext(location_name="Россия", source_span_id="span-geo")
    assert geo.source_span_id == "span-geo"


def test_normalized_document_accepts_fact_extensions() -> None:
    span = SourceSpan(
        document_id="d1",
        page=1,
        start_offset=0,
        end_offset=5,
        text="hello",
        source_type="text",
    )
    document = NormalizedDocument(
        id="d1",
        source_type="article",
        title="T",
        content="hello",
        source_spans=[span],
        quantities=[Quantity(value=82.0, unit="%", source_span_id=span.id)],
        geo_contexts=[GeoContext(location_name="Россия", source_span_id=span.id)],
        time_contexts=[TimeConstraint(relative_years=5)],
        alias_refs=[AliasRef(alias="Ni", canonical_hint="никель", source_span_id=span.id)],
    )
    assert document.quantities[0].source_span_id == span.id
    assert document.time_contexts[0].relative_years == 5
    assert document.alias_refs[0].canonical_hint == "никель"


def test_time_constraint_supports_query_ir_filter_keys() -> None:
    constraint = TimeConstraint.model_validate({"relative_years": 5})
    assert constraint.to_filter_dict() == {"relative_years": 5}

    absolute = TimeConstraint.model_validate({"start_year": 2022, "end_year": 2025})
    assert absolute.start_year == 2022
    assert absolute.end_year == 2025

    published = TimeConstraint.model_validate({"from": "2020-01-01", "to": "2024-12-31"})
    assert published.from_ == "2020-01-01"
    assert published.to == "2024-12-31"


def test_time_constraint_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        TimeConstraint.model_validate({})


def test_time_constraint_from_filter_dict_returns_none_for_empty() -> None:
    assert TimeConstraint.from_filter_dict({}) is None


def test_alias_ref_roundtrip_for_query_ir_filters() -> None:
    ref = AliasRef(alias="Ni", canonical_hint="никель")
    restored = AliasRef.from_filter_dict(ref.to_filter_dict())
    assert restored is not None
    assert restored.alias == "Ni"
    assert restored.canonical_hint == "никель"


def test_table_evidence_ref_links_table_block_and_span() -> None:
    ref = TableEvidenceRef(
        table_block_id="table-1",
        source_span_id="span-table-1",
        row_index=2,
        column_index=1,
    )
    assert ref.table_block_id == "table-1"
    assert ref.row_index == 2
