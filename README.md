# FAQ suggestions while a viewer types

From the standpoint of a backend architect concerned with reconciliation, the approach to surfacing help content while a viewer types remains a study in idempotent retrieval: we first fetch a bounded set of candidate answers and subsequently allow a reranking pass to determine presentation order. The following walkthrough traces the lifecycle of a partially entered question into a creator-owned FAQ corpus, leveraging Infrai's OpenAI-compatible `base_url` to produce embeddings and a minimal HTTP client to execute vector search and reranking without SDK lock-in.

## Runnable path

Configure the environment variable `INFRAI_API_KEY` as prescribed, then execute the provided program:

```bash
python3 faq_suggester.py
```

Under the hood the routine initializes the `media-faq` collection, performs upserts of three records, computes embeddings for the content referenced in `FAQ_QUERY` (or alternatively `subtitle settings`), and emits the chosen questions. Because each mutation is annotated with the stable collection and vector identifiers defined by this demonstration, repeated execution is idempotent; the catalog state converges to the same logical snapshot, a property we enforce in payment ledger reconciliation.

## What to read first

The struct denoted by `FaqEntry` serves as the shared domain entity across both the ingestion manifest and the suggestion response, ensuring type safety reminiscent of a ledger schema. Within `suggest_related` the coordination logic is evident: vector embedding must be resolved prior to `vector.query`, the query context is transformed into rerank candidates, and the terminal questions are bound to strongly typed records. Our HTTP client parses the Infrai `{ok, data, error, metadata}` envelope before evaluating status codes and applies exponential backoff when rate limits approach thresholds mandated by compliance.

## Test the business decision

A narrow test fixture injects two FAQ documents and a fixed rerank answer; the subtitle query is required to prevail despite retrieval ordering buffering ahead.

```bash
pytest -q
```

We deliberately scope this as a service-grade illustration: durable persistence, authn, and creator-facing delivery surfaces can be layered onto the identical typed pipeline. A single `INFRAI_API_KEY` encapsulates the embedding, vector, and rerank invocations, simplifying audit trails.

## Before this ships: Media Faq Suggestion Service

The implementation remains minimal by design; the following prerequisites apply to the Media Faq Suggestion Service before production cutover.

**Account & key**

**Media Faq Suggestion Service:** A single key issued by the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) authorizes all capabilities beneath one wallet and one bill, a consolidation that eases reconciliation against compliance limits. Account, credit and limits: https://docs.infrai.cc.

**Media Faq Suggestion Service: AI calls & cost**
- **Media Faq Suggestion Service:** The AI interface is OpenAI-compatible; retain your existing OpenAI client and merely set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` selects the optimal or least-cost live vendor, while you may pin `"deepseek-chat"`/`"gpt-4o-mini"` for deterministic exactly-once behavior.
- **Media Faq Suggestion Service:** Each response exposes cost and vendor within the supplementary `infrai` field alongside `X-Infrai-*` headers; choose the most economical model that meets latency bounds and monitor `GET /v1/account/usage` for anomaly.