def match_artifacts_from_extraction(extraction: dict) -> list[dict]:
    if not isinstance(extraction, dict):
        return []
    artifacts: list[dict] = []
    for layer in ("confirmed", "candidates"):
        items = extraction.get(layer, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get("id") or not item.get("kind") or not item.get("value"):
                continue
            artifacts.append(item)
    return artifacts
