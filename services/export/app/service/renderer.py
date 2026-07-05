import json


def render_markdown(document: dict) -> str:
    lines = [
        f"# Export for query run {document['query_run_id']}",
        "",
        f"- Question: {document['question']}",
        f"- Role: {document['role']}",
        f"- Access scope: {', '.join(document['access_scope'])}",
        f"- Dictionary version: {document['dictionary_version_id'] or ''}",
        f"- Generated at: {document['generated_at']}",
        f"- Status: {document['status']}",
        f"- Latency ms: {document['latency_ms'] if document['latency_ms'] is not None else ''}",
        "",
        "## Answer",
        "",
        str(document["answer"]),
        "",
        "## Query IR",
        "",
        "```json",
        json.dumps(document["query_ir"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Evidence",
        "",
    ]
    for item in document["evidence"]:
        lines.extend(
            [
                f"- {item['source_span_id']} (page {item['page']}, score {item['relevance_score']})",
                f"  {item['text']}",
            ]
        )
    lines.extend(["", "## Sources", ""])
    for source in document["sources"]:
        lines.extend(
            [
                f"- {source['document_title']} [{source['source_span_id']}]({source['link']})",
                f"  {source['text']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Graph",
            "",
            "```json",
            json.dumps(document["graph"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Gaps",
            "",
            *([f"- {item}" for item in document["gaps"]] or ["- none"]),
            "",
            "## Conflicts",
            "",
            *([f"- {item}" for item in document["conflicts"]] or ["- none"]),
            "",
            "## Retrieval Trace",
            "",
            "```json",
            json.dumps(document["retrieval_trace"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Warnings",
            "",
            *([f"- {item}" for item in document["warnings"]] or ["- none"]),
        ]
    )
    return "\n".join(lines)


def content_type_for_format(export_format: str) -> str:
    if export_format == "markdown":
        return "text/markdown"
    if export_format == "jsonld":
        return "application/ld+json"
    return "application/json"
