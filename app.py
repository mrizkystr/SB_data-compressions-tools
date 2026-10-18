from __future__ import annotations

import io
import os
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from compression import (
    ALGORITHM_SUFFIXES,
    MEBIBYTE,
    MAX_UPLOAD_SIZE,
    FileTooLargeError,
    InvalidCompressedData,
    OutputTooLargeError,
    calculate_metrics,
    compress_with_metrics,
    decompress_data,
    validate_file_size,
)

MAX_REQUEST_SIZE = MAX_UPLOAD_SIZE + MEBIBYTE

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_SIZE


def read_uploaded_file() -> tuple[bytes, str] | tuple[None, tuple[Response, int]]:
    uploaded = request.files.get("file")
    if uploaded is None:
        return None, (jsonify(error="Choose a file to continue."), 400)

    filename = secure_filename(uploaded.filename or "")[:200]
    if not filename:
        return None, (jsonify(error="The uploaded file needs a valid filename."), 400)

    contents = uploaded.stream.read(MAX_UPLOAD_SIZE + 1)
    try:
        validate_file_size(len(contents))
    except FileTooLargeError as error:
        return None, (jsonify(error=str(error)), 413)

    return contents, filename


def response_for_download(
    contents: bytes,
    filename: str,
    headers: dict[str, str],
) -> Response:
    response = send_file(
        io.BytesIO(contents),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )
    response.headers["X-Download-Name"] = filename
    for key, value in headers.items():
        response.headers[key] = value
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/compress")
def compress_file():
    uploaded_data, filename_or_error = read_uploaded_file()
    if uploaded_data is None:
        return filename_or_error

    algorithm = request.form.get("algorithm", "")
    if algorithm not in ALGORITHM_SUFFIXES:
        return jsonify(error="Choose a supported compression algorithm."), 400

    try:
        compressed, metrics = compress_with_metrics(uploaded_data, algorithm)
    except ValueError as error:
        return jsonify(error=str(error)), 400

    output_name = f"{filename_or_error}{ALGORITHM_SUFFIXES[algorithm]}"
    headers = {
        "X-Original-Size": str(metrics["original_size"]),
        "X-Output-Size": str(metrics["compressed_size"]),
        "X-Processing-Time-Ms": str(metrics["processing_time_ms"]),
        "X-Space-Saved-Bytes": str(metrics["space_saved_bytes"]),
    }
    if metrics["compression_ratio"] is not None:
        headers["X-Compression-Ratio"] = str(metrics["compression_ratio"])
    if metrics["space_saved_percent"] is not None:
        headers["X-Space-Saved-Percent"] = str(metrics["space_saved_percent"])

    return response_for_download(compressed, output_name, headers)


@app.post("/api/decompress")
def decompress_file():
    uploaded_data, filename_or_error = read_uploaded_file()
    if uploaded_data is None:
        return filename_or_error

    algorithm = request.form.get("algorithm", "")
    if algorithm not in ALGORITHM_SUFFIXES:
        return jsonify(error="Choose a supported compression algorithm."), 400

    started = time.perf_counter()
    try:
        decompressed = decompress_data(uploaded_data, algorithm)
    except OutputTooLargeError as error:
        return jsonify(error=str(error)), 413
    except InvalidCompressedData as error:
        return jsonify(error=str(error)), 400
    elapsed_ms = (time.perf_counter() - started) * 1000

    suffix = ALGORITHM_SUFFIXES[algorithm]
    safe_path = Path(filename_or_error)
    output_name = (
        safe_path.name[: -len(suffix)]
        if safe_path.name.lower().endswith(suffix)
        else f"{safe_path.name}.decompressed"
    )
    output_name = output_name or "decompressed-file"
    headers = {
        "X-Original-Size": str(len(uploaded_data)),
        "X-Output-Size": str(len(decompressed)),
        "X-Processing-Time-Ms": str(round(elapsed_ms, 2)),
    }
    return response_for_download(decompressed, output_name, headers)


@app.post("/api/compare")
def compare_algorithms():
    uploaded_data, filename_or_error = read_uploaded_file()
    if uploaded_data is None:
        return filename_or_error

    results = []
    for algorithm in ALGORITHM_SUFFIXES:
        _, metrics = compress_with_metrics(uploaded_data, algorithm)
        results.append({"algorithm": algorithm, **metrics})

    best_by_size = min(results, key=lambda result: result["compressed_size"])
    fastest = min(results, key=lambda result: result["processing_time_ms"])
    return jsonify(
        filename=filename_or_error,
        results=results,
        best_by_size=best_by_size["algorithm"],
        fastest=fastest["algorithm"],
    )


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(_error):
    message = (
        "Upload is too large. The maximum file size is "
        f"{MAX_UPLOAD_SIZE // MEBIBYTE} MiB."
    )
    return jsonify(error=message), 413


if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("PORT", "5000")))
