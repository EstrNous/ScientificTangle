import json
import sys

import httpx


EVAL_SERVICE_URL = "http://localhost:8000/api/query"
GOLD_QUESTIONS_PATH = "eval/gold_questions.json"


async def run_evaluation() -> None:
    with open(GOLD_QUESTIONS_PATH) as f:
        gold = json.load(f)

    results = []
    for question in gold["questions"]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                EVAL_SERVICE_URL,
                json={"query": question["text"]},
            )
        result = {
            "question_id": question["id"],
            "status_code": response.status_code,
            "tags": question.get("tags", []),
        }
        if response.status_code == 200:
            data = response.json()
            result["has_evidence"] = bool(data.get("evidence_bundle", {}).get("evidence_items"))
            result["confidence"] = data.get("confidence", 0.0)
        results.append(result)

    total = len(results)
    answered = sum(1 for r in results if r["status_code"] == 200)
    with_evidence = sum(1 for r in results if r.get("has_evidence"))

    print(f"Total questions: {total}")
    print(f"Answered (200): {answered}")
    print(f"With evidence: {with_evidence}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_evaluation())
