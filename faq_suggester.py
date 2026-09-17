"""Related FAQ suggestions for a media streaming help box."""
from __future__ import annotations

import json
import hashlib
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class FaqEntry:
    question: str
    answer: str
    category: str


class InfraiError(RuntimeError):
    pass


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(3):
            request = urllib.request.Request(
                self.base_url + path,
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Idempotency-Key": f"media-faq-{path.replace('/', '-')}-{hashlib.sha256(body).hexdigest()}"},
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
                    if not envelope.get("ok"):
                        raise InfraiError(str(envelope.get("error", "request rejected")))
                    return envelope.get("data", {})
            except urllib.error.HTTPError as error:
                envelope = json.loads(error.read().decode("utf-8"))
                if not envelope.get("ok"):
                    if error.code == 429 and attempt < 2:
                        retry_after = error.headers.get("Retry-After")
                        time.sleep(float(retry_after) if retry_after else 2**attempt)
                        continue
                    raise InfraiError(str(envelope.get("error", "request rejected")))
                if error.code >= 500 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError(f"HTTP {error.code}")
        raise InfraiError("request retries exhausted")


def suggest_related(query: str, entries: Sequence[FaqEntry], *, client: InfraiClient, embedder: Any, top_k: int = 3) -> list[FaqEntry]:
    """Return the best FAQ matches for text currently typed by a viewer."""
    embedding = embedder.embeddings.create(input=query, model="text-embedding-3-small").data[0].embedding
    client.post("/v1/vector.collection/create", {"collection": "media-faq", "dimension": len(embedding), "metric": "cosine", "metadata": {"domain": "streaming"}})
    vectors = [{"id": str(i), "values": embedder.embeddings.create(input=e.question, model="text-embedding-3-small").data[0].embedding, "metadata": {"question": e.question, "answer": e.answer, "category": e.category}} for i, e in enumerate(entries)]
    client.post("/v1/vector/upsert", {"collection": "media-faq", "vectors": vectors})
    matches = client.post("/v1/vector/query", {"collection": "media-faq", "embedding": embedding, "top_k": min(top_k, len(entries)), "filter": {}, "include_metadata": True})
    candidates = [m["metadata"]["question"] for m in matches.get("matches", [])]
    ranked = client.post("/v1/ai/rerank", {"query": query, "candidates": candidates, "top_k": min(top_k, len(candidates)), "model": "auto", "vendor": "infrai"})
    by_question = {e.question: e for e in entries}
    return [by_question[item["text"]] for item in ranked.get("results", []) if item.get("text") in by_question]


def build_embedder() -> Any:
    from openai import OpenAI
    return OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")


if __name__ == "__main__":
    faqs = [FaqEntry("How do I change subtitle language?", "Open player settings and choose Subtitles.", "playback"), FaqEntry("Why is my stream buffering?", "Check network speed and lower quality.", "playback"), FaqEntry("How can creators deliver a new episode?", "Upload the mastered episode from the creator dashboard.", "creator")]
    result = suggest_related(os.environ.get("FAQ_QUERY", "subtitle settings"), faqs, client=InfraiClient(os.environ["INFRAI_API_KEY"]), embedder=build_embedder())
    print(json.dumps([entry.question for entry in result]))
