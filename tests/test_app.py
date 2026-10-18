import io

import pytest

from app import app
from compression import ALGORITHM_SUFFIXES, compress_data, decompress_data


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_homepage_and_frontend_assets_load(client):
    page = client.get("/")

    assert page.status_code == 200
    assert b"Data Compression Tools" in page.data
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200


def test_compress_endpoint_returns_download_and_metrics(client):
    original = b"sample text " * 100
    response = client.post(
        "/api/compress",
        data={"algorithm": "gzip", "file": (io.BytesIO(original), "../sample.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.headers["X-Download-Name"] == "sample.txt.gz"
    assert int(response.headers["X-Original-Size"]) == len(original)
    assert decompress_data(response.data, "gzip") == original


def test_decompress_endpoint_returns_original_file(client):
    original = b"round trip through the HTTP route"
    compressed = compress_data(original, "bz2")
    response = client.post(
        "/api/decompress",
        data={"algorithm": "bz2", "file": (io.BytesIO(compressed), "notes.txt.bz2")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.headers["X-Download-Name"] == "notes.txt"
    assert response.data == original


def test_compare_endpoint_returns_all_formats(client):
    response = client.post(
        "/api/compare",
        data={"file": (io.BytesIO(b"compare me " * 50), "notes.txt")},
        content_type="multipart/form-data",
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert {item["algorithm"] for item in payload["results"]} == set(ALGORITHM_SUFFIXES)
    assert payload["best_by_size"] in ALGORITHM_SUFFIXES
    assert payload["fastest"] in ALGORITHM_SUFFIXES


def test_decompress_endpoint_reports_corrupted_input(client):
    response = client.post(
        "/api/decompress",
        data={"algorithm": "gzip", "file": (io.BytesIO(b"not gzip"), "broken.gz")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "corrupted" in response.get_json()["error"]
