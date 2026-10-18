import hashlib

import pytest

from compression import (
    ALGORITHM_SUFFIXES,
    FileTooLargeError,
    InvalidCompressedData,
    OutputTooLargeError,
    calculate_metrics,
    compress_data,
    decompress_data,
    validate_file_size,
)


@pytest.mark.parametrize("algorithm", ALGORITHM_SUFFIXES)
def test_compression_round_trip_preserves_sha256(algorithm):
    original = (b"compression matters when content repeats; " * 500) + bytes(range(256))
    compressed = compress_data(original, algorithm)
    restored = decompress_data(compressed, algorithm)

    assert hashlib.sha256(restored).digest() == hashlib.sha256(original).digest()


@pytest.mark.parametrize("algorithm", ALGORITHM_SUFFIXES)
def test_empty_file_round_trip(algorithm):
    compressed = compress_data(b"", algorithm)

    assert compressed
    assert decompress_data(compressed, algorithm) == b""


@pytest.mark.parametrize("algorithm", ALGORITHM_SUFFIXES)
def test_invalid_compressed_data_is_reported(algorithm):
    with pytest.raises(InvalidCompressedData):
        decompress_data(b"this is not a valid compressed stream", algorithm)


def test_decompression_output_limit_is_enforced():
    compressed = compress_data(b"A" * 1000, "gzip")

    with pytest.raises(OutputTooLargeError):
        decompress_data(compressed, "gzip", max_output_size=100)


def test_file_size_validation_accepts_limit_and_rejects_oversize():
    validate_file_size(10, max_size=10)

    with pytest.raises(FileTooLargeError):
        validate_file_size(11, max_size=10)


def test_file_size_validation_rejects_negative_size():
    with pytest.raises(ValueError, match="negative"):
        validate_file_size(-1)


def test_metrics_include_expansion_when_compression_output_is_larger():
    metrics = calculate_metrics(10, 12, 1.234)

    assert metrics["compression_ratio"] == 120
    assert metrics["space_saved_bytes"] == -2
    assert metrics["space_saved_percent"] == -20
    assert metrics["processing_time_ms"] == 1.23


def test_metrics_for_empty_input_use_undefined_percentages():
    metrics = calculate_metrics(0, 20, 0.0)

    assert metrics["compression_ratio"] is None
    assert metrics["space_saved_bytes"] == -20
    assert metrics["space_saved_percent"] is None
