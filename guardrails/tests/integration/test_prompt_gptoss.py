import requests
import sys
import pytest


@pytest.mark.skip(reason="Requires running server on localhost:8080")
def test_smoke_generate():
    """Smoke test for /api/generate endpoint - requires running server."""
    url = 'http://127.0.0.1:8080/api/generate'
    payload = {'model':'gpt-oss','prompt':'Hello from smoke test — please respond briefly.','stream':False}
    try:
        r = requests.post(url, json=payload, timeout=30)
        print('STATUS', r.status_code)
        print('BODY', r.text)
        assert r.status_code == 200
    except Exception as e:
        pytest.fail(f'ERROR: {e}')