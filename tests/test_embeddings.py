import io
import json
import urllib.error

import pytest

from app.config import Settings
from app.embeddings import cosine_similarity, get_embedder
from app.embeddings.base import batched
from app.embeddings.fake import FakeEmbedder
from app.embeddings.voyage import VoyageEmbedder, VoyageError


def test_cosine_similarity_basics():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)
    with pytest.raises(ValueError):
        cosine_similarity([1, 0], [1, 0, 0])


def test_batched_splits_in_order():
    assert [list(b) for b in batched(["a", "b", "c", "d", "e"], 2)] == [
        ["a", "b"],
        ["c", "d"],
        ["e"],
    ]


class TestFakeEmbedder:
    def test_is_deterministic_and_normalised(self):
        embedder = FakeEmbedder(dimensions=64)
        first = embedder.embed_query("profitul net al băncii")
        assert first == embedder.embed_query("profitul net al băncii")
        assert len(first) == 64
        assert cosine_similarity(first, first) == pytest.approx(1.0)

    def test_shared_words_mean_higher_similarity(self):
        embedder = FakeEmbedder()
        query = embedder.embed_query("profitul net al băncii")
        related, unrelated = embedder.embed_documents(
            ["Profitul net al băncii a crescut.", "Producția de energie a scăzut."]
        )
        assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def voyage_response(n: int, dims: int, reverse: bool = False) -> FakeResponse:
    data = [{"object": "embedding", "index": i, "embedding": [float(i)] * dims} for i in range(n)]
    if reverse:
        data.reverse()
    body = {"object": "list", "data": data, "usage": {"total_tokens": 7 * n}}
    return FakeResponse(json.dumps(body).encode())


def http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError("url", code, "error", headers, io.BytesIO(b"{}"))


class TestVoyageEmbedder:
    def make(self, **kwargs) -> VoyageEmbedder:
        return VoyageEmbedder(api_key="test-key", dimensions=4, sleep=lambda s: None, **kwargs)

    def test_sends_model_input_type_dimension_and_key(self, monkeypatch):
        sent = []

        def fake_urlopen(request, timeout):
            sent.append(request)
            return voyage_response(1, 4)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        self.make().embed_query("Cât profit?")

        payload = json.loads(sent[0].data)
        assert payload == {
            "input": ["Cât profit?"],
            "model": "voyage-4",
            "input_type": "query",
            "output_dimension": 4,
        }
        assert sent[0].get_header("Authorization") == "Bearer test-key"

    def test_documents_are_batched_and_returned_in_input_order(self, monkeypatch):
        calls = []

        def fake_urlopen(request, timeout):
            batch = json.loads(request.data)["input"]
            calls.append(batch)
            assert json.loads(request.data)["input_type"] == "document"
            return voyage_response(len(batch), 4, reverse=True)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        embedder = self.make(batch_size=2)
        vectors = embedder.embed_documents(["a", "b", "c"])

        assert calls == [["a", "b"], ["c"]]
        # The API reports an index per item; vectors come back sorted by it.
        assert [v[0] for v in vectors] == [0.0, 1.0, 0.0]
        assert embedder.tokens_used == 21

    def test_retries_on_rate_limit_then_succeeds(self, monkeypatch):
        responses = [http_error(429, retry_after="2"), voyage_response(1, 4)]
        delays = []

        def fake_urlopen(request, timeout):
            result = responses.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        embedder = VoyageEmbedder(api_key="k", dimensions=4, sleep=delays.append)

        assert embedder.embed_query("x") == [0.0] * 4
        assert delays == [2.0]

    def test_gives_up_after_max_retries(self, monkeypatch):
        def always_unavailable(request, timeout):
            raise http_error(503)

        monkeypatch.setattr("urllib.request.urlopen", always_unavailable)
        with pytest.raises(VoyageError, match="HTTP 503"):
            self.make(max_retries=2).embed_query("x")

    def test_bad_key_fails_immediately_with_a_clear_message(self, monkeypatch):
        calls = 0

        def unauthorised(request, timeout):
            nonlocal calls
            calls += 1
            raise http_error(401)

        monkeypatch.setattr("urllib.request.urlopen", unauthorised)
        with pytest.raises(VoyageError, match="API key"):
            self.make().embed_query("x")
        assert calls == 1

    def test_wrong_vector_length_is_rejected(self, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", lambda r, timeout: voyage_response(1, 3))
        with pytest.raises(VoyageError, match="length 4"):
            self.make().embed_query("x")

    def test_missing_key_is_reported_before_any_request(self):
        with pytest.raises(VoyageError, match="VOYAGE_API_KEY"):
            VoyageEmbedder(api_key="")


def test_factory_selects_the_provider():
    fake = get_embedder(Settings(embedding_provider="fake", embedding_dimensions=32))
    assert isinstance(fake, FakeEmbedder) and fake.dimensions == 32

    voyage = get_embedder(Settings(embedding_provider="voyage", voyage_api_key="k"))
    assert isinstance(voyage, VoyageEmbedder) and voyage.model == "voyage-4"


def test_the_api_key_is_not_shown_when_settings_are_printed():
    settings = Settings(voyage_api_key="secret-value")
    assert "secret-value" not in repr(settings)
