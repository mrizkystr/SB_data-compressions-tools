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

## Deploy on Render

Create a Render Web Service from this repository and use:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`

Render supplies `PORT`; the command does not depend on a fixed production port. The included `.python-version` requests Python 3.11.10.

## File handling

Uploads are limited to 20 MiB. Decompressed output is capped at 64 MiB to limit memory use. Flask/Werkzeug parses the multipart request and may spool larger uploads to a temporary file; that stream is closed and cleaned up with the request. The app reads the content into memory for processing, and compressed and decompressed results also remain in memory for that request. The app does not retain files after the response. There are no user-specific download IDs because the download is returned directly from the request.

Compression results include the source and output sizes, output-to-source ratio, size saved (which can be negative for incompressible data), and processing time. For an empty source, percentage metrics are undefined and shown as a dash.

## Tests

```bash
pytest
```
