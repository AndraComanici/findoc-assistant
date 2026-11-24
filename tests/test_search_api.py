import pytest
from fastapi.testclient import TestClient

from app.api_search import embedder_dependency, searcher_dependency
from app.embeddings.fake import FakeEmbedder
from app.main import app
from app.retrieval.semantic import SearchHit

HIT = SearchHit(
    chunk_id=136,
    source_id="h2o-2025",
    company="Hidroelectrica",
    ticker="H2O",
    year=2025,
    page_number=53,
    content="Adunarea Generală a aprobat distribuirea dividendelor...",
    score=0.712345,
)


class RecordingSearcher:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.hits


@pytest.fixture
def searcher():
    recording = RecordingSearcher([HIT])
    app.dependency_overrides[embedder_dependency] = lambda: FakeEmbedder(dimensions=8)
    app.dependency_overrides[searcher_dependency] = lambda: recording
    yield recording
    app.dependency_overrides.clear()


client = TestClient(app)


def test_returns_passages_with_company_year_and_page(searcher):
    response = client.get("/search", params={"q": "Ce dividende a dat Hidroelectrica?"})

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "fake-bag-of-words"
    assert body["results"] == [
        {
            "score": 0.7123,
            "company": "Hidroelectrica",
            "ticker": "H2O",
            "year": 2025,
            "page": 53,
            "source_id": "h2o-2025",
            "chunk_id": 136,
            "text": "Adunarea Generală a aprobat distribuirea dividendelor...",
        }
    ]


def test_passes_filters_and_the_query_vector_to_the_search(searcher):
    client.get("/search", params={"q": "profit net", "k": 3, "ticker": "TLV", "year": 2024})

    call = searcher.calls[0]
    assert (call["k"], call["ticker"], call["year"]) == (3, "TLV", 2024)
    assert call["model"] == "fake-bag-of-words"
    assert len(call["query_vector"]) == 8


@pytest.mark.parametrize(
    "params",
    [
        {"q": "ab"},  # too short
        {"q": "profit", "k": 0},
        {"q": "profit", "k": 50},
        {"q": "profit", "ticker": "tlv; DROP TABLE"},
        {"q": "profit", "year": 1990},
    ],
)
def test_invalid_input_is_rejected_before_any_search(searcher, params):
    assert client.get("/search", params=params).status_code == 422
    assert searcher.calls == []


def test_embedding_failure_is_reported_as_bad_gateway(searcher):
    class Broken(FakeEmbedder):
        def embed_query(self, text):
            raise RuntimeError("quota exceeded")

    app.dependency_overrides[embedder_dependency] = lambda: Broken()

    response = client.get("/search", params={"q": "profit net"})

    assert response.status_code == 502
    assert searcher.calls == []
