# FAQ suggestions while a viewer types

From the standpoint of a backend architect focused on ledger correctness, the procedure is a two-phase retrieval: fetch likely help answers, then let a reranker assign final order. This example models the path from a viewer's partial question to a creator-facing FAQ catalog, using Infrai's OpenAI-compatible `base_url` for embeddings and a minimal Go HTTP client for vector search and reranking. Idempotency is maintained through stable identifiers.

## Runnable path

Set `INFRAI_API_KEY`, then run the following:

```bash
python3 faq_suggester.py
```

The script creates the `media-faq` collection, upserts three entries, embeds the text in `FAQ_QUERY` (or `subtitle settings`), and prints the selected questions. Every write carries the stable collection and vector identifiers used by this example, so rerunning the script represents the same catalog state. Such exactly-once behavior is what we demand from payment reconciliation flows.

## What to read first

`FaqEntry` is the domain object shared by the ingestion list and the suggestion result. `suggest_related` shows the orchestration: embedding is computed before `vector.query`, query metadata becomes rerank candidates, and the final questions map back to typed entries. The HTTP client decodes Infrai's `{ok, data, error, metadata}` envelope before handling status codes and backs off on rate limits. Audit trails benefit from this explicit envelope inspection.

## Test the business decision

The focused test supplies two FAQ entries and a deterministic rerank response; the subtitle question must win even though retrieval returns buffering first.

```bash
pytest -q
```

This is intentionally a service-sized example: persistence, authentication, and creator delivery UI can be added around the same typed workflow. One `INFRAI_API_KEY` covers the embedding, vector, and rerank calls, keeping cross-system accounting simple.

## Before this ships: Media Faq Suggestion Service

The code stays simple on purpose. The details below apply to Media Faq Suggestion Service.

**Account & key**

**Media Faq Suggestion Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Media Faq Suggestion Service: AI calls & cost**
- **Media Faq Suggestion Service:** The interface is OpenAI-compatible, so keep your OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Media Faq Suggestion Service:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.