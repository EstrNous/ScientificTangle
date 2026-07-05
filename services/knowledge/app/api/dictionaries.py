import json
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel

from shared.contracts import (
    DictionaryFilePayload,
    DictionaryPackagePayload,
    DictionaryVersionPayload,
    DictionaryVersionStatus,
    QueryIR,
)
from shared.web import ServiceError

router = APIRouter(prefix="/v1/dictionaries", tags=["dictionaries"])

DICTIONARY_FILE_KINDS = frozenset({"entities", "aliases", "units", "geographies"})


class CreateDictionaryVersionRequest(BaseModel):
    package: DictionaryPackagePayload
    uploaded_by: UUID


class EnrichQueryIRRequest(BaseModel):
    query_ir: QueryIR


@router.post("", response_model=DictionaryVersionPayload)
async def create_dictionary_version(
    payload: CreateDictionaryVersionRequest,
    request: Request,
) -> DictionaryVersionPayload:
    validation_errors = _validate_entries(payload.package)
    if validation_errors:
        raise ServiceError(422, "dictionary_validation_failed", "; ".join(validation_errors))
    driver = request.app.state.neo4j_driver
    version_id = uuid4()
    created_at = datetime.now(UTC)
    files_json = json.dumps([item.model_dump(mode="json") for item in payload.package.files], ensure_ascii=False)
    async with driver.session() as session:
        existing = await session.run(
            "MATCH (v:DictionaryVersion {version: $version}) RETURN v LIMIT 1",
            version=payload.package.version,
        )
        if await existing.single() is not None:
            raise ServiceError(409, "dictionary_version_exists", "Dictionary version already exists")
        await session.run(
            """
            CREATE (v:DictionaryVersion {
                dictionary_version_id: $version_id,
                version: $version,
                package_sha256: $package_sha256,
                source_object_key: $source_object_key,
                source_filename: $source_filename,
                status: $status,
                files_json: $files_json,
                uploaded_by: $uploaded_by,
                created_at: datetime($created_at)
            })
            """,
            version_id=str(version_id),
            version=payload.package.version,
            package_sha256=payload.package.package_sha256,
            source_object_key=payload.package.source.object_key,
            source_filename=payload.package.source.original_filename,
            files_json=files_json,
            uploaded_by=str(payload.uploaded_by),
            created_at=created_at.isoformat(),
            status=DictionaryVersionStatus.VALIDATED.value,
        )
        for file in payload.package.files:
            for entry in file.entries:
                entry_id = uuid4()
                await session.run(
                    """
                    MATCH (v:DictionaryVersion {dictionary_version_id: $version_id})
                    CREATE (e:DictionaryEntry {
                        dictionary_entry_id: $entry_id,
                        kind: $kind,
                        canonical: $canonical,
                        payload_json: $payload_json
                    })
                    MERGE (v)-[:CONTAINS]->(e)
                    """,
                    version_id=str(version_id),
                    entry_id=str(entry_id),
                    kind=file.kind,
                    canonical=str(entry.get("canonical") or entry.get("name") or ""),
                    payload_json=json.dumps(entry, ensure_ascii=False),
                )
    return DictionaryVersionPayload(
        id=version_id,
        version=payload.package.version,
        package_sha256=payload.package.package_sha256,
        status=DictionaryVersionStatus.VALIDATED,
        files=payload.package.files,
        uploaded_by=payload.uploaded_by,
        created_at=created_at,
    )


@router.get("", response_model=list[DictionaryVersionPayload])
async def list_dictionary_versions(request: Request) -> list[DictionaryVersionPayload]:
    driver = request.app.state.neo4j_driver
    async with driver.session() as session:
        result = await session.run(
            "MATCH (v:DictionaryVersion) RETURN properties(v) AS version ORDER BY v.created_at DESC"
        )
        rows = [record async for record in result]
    return [_version_payload(dict(record["version"])) for record in rows]


@router.get("/active", response_model=DictionaryVersionPayload)
async def get_active_dictionary(request: Request) -> DictionaryVersionPayload:
    driver = request.app.state.neo4j_driver
    async with driver.session() as session:
        result = await session.run(
            "MATCH (v:DictionaryVersion {status: 'active'}) RETURN properties(v) AS version LIMIT 1"
        )
        record = await result.single()
    if record is None:
        raise ServiceError(404, "active_dictionary_not_found", "Active dictionary was not found")
    return _version_payload(dict(record["version"]))


@router.post("/{version_id}/activate", response_model=DictionaryVersionPayload)
async def activate_dictionary(version_id: UUID, request: Request) -> DictionaryVersionPayload:
    driver = request.app.state.neo4j_driver
    activated_at = datetime.now(UTC)
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (target:DictionaryVersion {dictionary_version_id: $version_id})
            WHERE target.status IN ['validated', 'inactive', 'active']
            OPTIONAL MATCH (current:DictionaryVersion {status: 'active'})
            WITH target, collect(current) AS active_versions
            FOREACH (current IN [item IN active_versions WHERE item <> target] |
                SET current.status = 'inactive'
            )
            SET target.status = 'active',
                target.activated_at = datetime($activated_at)
            RETURN properties(target) AS version
            """,
            version_id=str(version_id),
            activated_at=activated_at.isoformat(),
        )
        record = await result.single()
    if record is None:
        raise ServiceError(404, "dictionary_version_not_found", "Dictionary version was not found")
    return _version_payload(dict(record["version"]))


@router.post("/{version_id}/enrich-query-ir", response_model=QueryIR)
async def enrich_query_ir(
    version_id: UUID,
    payload: EnrichQueryIRRequest,
    request: Request,
) -> QueryIR:
    version = await _load_version(request, version_id)
    query_ir = payload.query_ir.model_copy(deep=True)
    lowered = query_ir.raw_query.casefold()
    canonical_entities = list(query_ir.entities)
    aliases: dict[str, str] = {}
    units: dict[str, str] = {}
    geographies: dict[str, str] = {}
    for file in version.files:
        for entry in file.entries:
            canonical = str(entry.get("canonical") or entry.get("name") or "").strip()
            values = [canonical, *[str(value) for value in entry.get("aliases", [])]]
            target = aliases if file.kind in {"aliases", "entities"} else units if file.kind == "units" else geographies
            for value in values:
                if value:
                    target[value.casefold()] = canonical or value
            if file.kind in {"aliases", "entities"} and canonical and any(value.casefold() in lowered for value in values if value):
                canonical_entities.append(canonical)
    query_ir.entities = list(dict.fromkeys(canonical_entities))
    numeric = query_ir.filters.get("numeric_constraints", [])
    for constraint in numeric:
        if isinstance(constraint, dict):
            unit = str(constraint.get("unit", "")).casefold()
            if unit in units:
                constraint["unit"] = units[unit]
    geo = query_ir.filters.get("geo_constraints", [])
    query_ir.filters["geo_constraints"] = [geographies.get(str(value).casefold(), value) for value in geo]
    query_ir.filters["dictionary_version_id"] = str(version_id)
    return query_ir


async def _load_version(request: Request, version_id: UUID) -> DictionaryVersionPayload:
    driver = request.app.state.neo4j_driver
    async with driver.session() as session:
        result = await session.run(
            "MATCH (v:DictionaryVersion {dictionary_version_id: $version_id}) RETURN properties(v) AS version LIMIT 1",
            version_id=str(version_id),
        )
        record = await result.single()
    if record is None:
        raise ServiceError(404, "dictionary_version_not_found", "Dictionary version was not found")
    return _version_payload(dict(record["version"]))


def _version_payload(value: dict) -> DictionaryVersionPayload:
    files_raw = json.loads(str(value.get("files_json") or "[]"))
    files = [DictionaryFilePayload.model_validate(item) for item in files_raw]
    return DictionaryVersionPayload(
        id=UUID(str(value["dictionary_version_id"])),
        version=str(value["version"]),
        package_sha256=str(value["package_sha256"]),
        status=DictionaryVersionStatus(str(value["status"])),
        files=files,
        uploaded_by=UUID(str(value["uploaded_by"])),
        created_at=_native_datetime(value["created_at"]),
        activated_at=_native_datetime(value.get("activated_at")),
    )


def _native_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    if hasattr(value, "to_native"):
        return value.to_native()
    return value


def _validate_entries(package: DictionaryPackagePayload) -> list[str]:
    errors = []
    seen_paths: set[str] = set()
    for file in package.files:
        path_error = _validate_file_path(file.path)
        if path_error:
            errors.append(path_error)
            continue
        if file.path in seen_paths:
            errors.append(f"{file.path}:duplicate_path")
            continue
        seen_paths.add(file.path)
        if file.kind not in DICTIONARY_FILE_KINDS:
            errors.append(f"{file.path}:kind_invalid")
        if len(file.sha256) != 64:
            errors.append(f"{file.path}:sha256_invalid")
        if not file.entries:
            errors.append(f"{file.path}:entries_required")
        for index, entry in enumerate(file.entries):
            canonical = str(entry.get("canonical") or entry.get("name") or "").strip()
            if not canonical:
                errors.append(f"{file.path}:{index}:canonical_required")
            aliases = entry.get("aliases", [])
            if not isinstance(aliases, list) or not all(isinstance(value, str) for value in aliases):
                errors.append(f"{file.path}:{index}:aliases_invalid")
    return errors


def _validate_file_path(path: str) -> str | None:
    normalized = str(path or "").replace("\\", "/").strip()
    if not normalized:
        return "dictionary_file:path_required"
    posix = PurePosixPath(normalized)
    if posix.is_absolute() or ".." in posix.parts:
        return f"{normalized}:path_unsafe"
    return None
