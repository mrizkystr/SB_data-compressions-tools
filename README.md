# Data Compression Tools

A small Flask utility for compressing, decompressing, and comparing files with Python's standard-library `gzip`, `bz2`, `lzma`, and `zlib` formats.

## Run locally

Requires Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

Open `http://127.0.0.1:5000` in a browser. The Flask development server is for local use only; production should use Gunicorn.

## Tests

```bash
pytest
```
