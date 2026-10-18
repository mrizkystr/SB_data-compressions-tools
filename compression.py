"""Compression helpers for the supported file formats."""

from __future__ import annotations

import bz2
import gzip
import io
import lzma
import time
import zlib
from typing import Any

MEBIBYTE = 1024 * 1024
MAX_UPLOAD_SIZE = 4 * MEBIBYTE  # Vercel Hobby plan caps request body at 4.5 MB
MAX_DECOMPRESSED_SIZE = 64 * MEBIBYTE

ALGORITHM_SUFFIXES = {
    "gzip": ".gz",
    "bz2": ".bz2",
    "lzma": ".xz",
    "zlib": ".zlib",
}


class FileTooLargeError(ValueError):
    """Raised when a file exceeds its allowed input size."""


class InvalidCompressedData(ValueError):
    """Raised when compressed input cannot be decoded."""


class OutputTooLargeError(ValueError):
    """Raised when decompressed output exceeds the configured limit."""


def validate_file_size(size: int, max_size: int = MAX_UPLOAD_SIZE) -> None:
    if size < 0:
        raise ValueError("File size cannot be negative.")
    if size > max_size:
        raise FileTooLargeError(f"File exceeds the {max_size // MEBIBYTE} MiB limit.")


def compress_data(data: bytes, algorithm: str) -> bytes:
    if algorithm == "gzip":
        return gzip.compress(data, mtime=0)
    if algorithm == "bz2":
        return bz2.compress(data)
    if algorithm == "lzma":
        return lzma.compress(data)
    if algorithm == "zlib":
        return zlib.compress(data)
    raise ValueError("Choose a supported compression algorithm.")


def decompress_data(
    data: bytes,
    algorithm: str,
    max_output_size: int = MAX_DECOMPRESSED_SIZE,
) -> bytes:
    if max_output_size < 0:
        raise ValueError("Maximum output size cannot be negative.")

    try:
        if algorithm == "gzip":
            with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as stream:
                output = stream.read(max_output_size + 1)
        elif algorithm == "bz2":
            with bz2.BZ2File(io.BytesIO(data), mode="rb") as stream:
                output = stream.read(max_output_size + 1)
        elif algorithm == "lzma":
            with lzma.LZMAFile(io.BytesIO(data), mode="rb") as stream:
                output = stream.read(max_output_size + 1)
        elif algorithm == "zlib":
            decoder = zlib.decompressobj()
            output = decoder.decompress(data, max_output_size + 1)
            if len(output) <= max_output_size:
                output += decoder.flush(max_output_size + 1 - len(output))
            if not decoder.eof or decoder.unused_data:
                raise InvalidCompressedData(
                    "The zlib file is incomplete or contains trailing data."
                )
        else:
            raise ValueError("Choose a supported compression algorithm.")
    except (OSError, EOFError, lzma.LZMAError, zlib.error) as error:
        raise InvalidCompressedData(
            "The file is corrupted or does not match the selected format."
        ) from error

    if len(output) > max_output_size:
        raise OutputTooLargeError(
            f"Decompressed output exceeds the {max_output_size // MEBIBYTE} MiB limit."
        )
    return output


def calculate_metrics(
    original_size: int,
    compressed_size: int,
    processing_time_ms: float,
) -> dict[str, Any]:
    if original_size < 0 or compressed_size < 0:
        raise ValueError("File sizes cannot be negative.")

    return {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_ratio": (
            compressed_size / original_size * 100 if original_size else None
        ),
        "space_saved_bytes": original_size - compressed_size,
        "space_saved_percent": (
            (original_size - compressed_size) / original_size * 100
            if original_size
            else None
        ),
        "processing_time_ms": round(max(0.0, processing_time_ms), 2),
    }


def compress_with_metrics(data: bytes, algorithm: str) -> tuple[bytes, dict[str, Any]]:
    started = time.perf_counter()
    compressed = compress_data(data, algorithm)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return compressed, calculate_metrics(len(data), len(compressed), elapsed_ms)
