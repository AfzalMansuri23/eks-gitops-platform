import pytest

from app.retrieval import EmbeddingRetriever, HybridRetriever, KeywordRetriever


@pytest.fixture(scope="session")
def keyword():
    return KeywordRetriever()


@pytest.fixture(scope="session")
def embedding():
    return EmbeddingRetriever()


@pytest.fixture(scope="session")
def hybrid(keyword, embedding):
    return HybridRetriever(keyword, embedding)
