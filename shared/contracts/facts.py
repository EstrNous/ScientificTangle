from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TimeConstraint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    relative_years: int | None = Field(default=None, ge=1)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    end_year: int | None = Field(default=None, ge=1900, le=2100)
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None

    @model_validator(mode="after")
    def ensure_non_empty(self) -> "TimeConstraint":
        if not any(
            value is not None
            for value in (
                self.relative_years,
                self.start_year,
                self.end_year,
                self.from_,
                self.to,
            )
        ):
            raise ValueError("time constraint requires at least one bound")
        return self

    @classmethod
    def from_filter_dict(cls, payload: dict[str, Any]) -> "TimeConstraint | None":
        if not isinstance(payload, dict) or not payload:
            return None
        return cls.model_validate(payload)

    def to_filter_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


class AliasRef(BaseModel):
    alias: str = Field(min_length=1)
    canonical_hint: str = ""
    source_span_id: str | None = None
    entity_id: str | None = None

    @classmethod
    def from_filter_dict(cls, payload: dict[str, Any]) -> "AliasRef | None":
        if not isinstance(payload, dict):
            return None
        alias = str(payload.get("alias", "")).strip()
        if not alias:
            return None
        return cls(
            alias=alias,
            canonical_hint=str(payload.get("canonical_hint", "")),
            source_span_id=payload.get("source_span_id"),
            entity_id=payload.get("entity_id"),
        )

    def to_filter_dict(self) -> dict[str, str]:
        result: dict[str, str] = {"alias": self.alias}
        if self.canonical_hint:
            result["canonical_hint"] = self.canonical_hint
        if self.source_span_id:
            result["source_span_id"] = self.source_span_id
        if self.entity_id:
            result["entity_id"] = self.entity_id
        return result


class TableEvidenceRef(BaseModel):
    table_block_id: str = Field(min_length=1)
    source_span_id: str = Field(min_length=1)
    row_index: int | None = Field(default=None, ge=0)
    column_index: int | None = Field(default=None, ge=0)
