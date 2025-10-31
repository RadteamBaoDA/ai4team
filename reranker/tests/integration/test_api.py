"""Integration tests for the reranker API."""

import pytest
from fastapi.testclient import TestClient

from reranker.api.app import app


class TestRerankerAPI:
    """Integration tests for the reranker API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "model" in data
        assert "device" in data
        assert "max_parallel" in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint.""" 
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "controller" in data
        assert "model" in data
        assert "metrics" in data

    def test_rerank_endpoint(self, client, sample_query, sample_documents):
        """Test native rerank endpoint."""
        payload = {
            "query": sample_query,
            "documents": sample_documents,
            "top_k": 3
        }
        
        response = client.post("/rerank", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "took_ms" in data
        assert len(data["results"]) <= 3

    def test_cohere_compatible_endpoint(self, client, sample_query, sample_documents):
        """Test Cohere-compatible v1 rerank endpoint."""
        payload = {
            "query": sample_query,
            "documents": sample_documents,
            "top_n": 2,
            "model": "rerank-english-v2.0"
        }
        
        response = client.post("/v1/rerank", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "id" in data
        assert "meta" in data
        assert len(data["results"]) <= 2