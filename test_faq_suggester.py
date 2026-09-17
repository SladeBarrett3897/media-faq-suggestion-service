from faq_suggester import FaqEntry, suggest_related


class Embedding:
    def __init__(self, values): self.data = [type("D", (), {"embedding": values})()]


class FakeEmbedder:
    class embeddings:
        @staticmethod
        def create(input, model): return Embedding([1.0, 0.0])


class FakeClient:
    def __init__(self): self.calls = []
    def post(self, path, payload):
        self.calls.append((path, payload))
        if path.endswith("query"): return {"matches": [{"metadata": {"question": "Why is my stream buffering?"}}, {"metadata": {"question": "How do I change subtitle language?"}}]}
        if path.endswith("rerank"): return {"results": [{"text": "How do I change subtitle language?"}]}
        return {}


def test_suggestion_follows_rerank_decision():
    entries = [FaqEntry("Why is my stream buffering?", "network", "playback"), FaqEntry("How do I change subtitle language?", "subtitle", "playback")]
    result = suggest_related("subtitle", entries, client=FakeClient(), embedder=FakeEmbedder())
    assert [item.question for item in result] == ["How do I change subtitle language?"]
