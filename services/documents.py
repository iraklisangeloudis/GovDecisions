"""Bounded PDF retrieval for inline previews; no permanent document storage."""

import re
from tempfile import SpooledTemporaryFile

import requests

from config import DIAVGEIA_TIMEOUT
from services.diavgeia import document_url

MAX_PDF_BYTES = 25 * 1024 * 1024


class DocumentError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def fetch_pdf(ada):
    if not re.fullmatch(r"[A-Za-z0-9\u0370-\u03ff\u1f00-\u1fff-]{1,80}", ada):
        raise DocumentError("Invalid decision identifier.", 400)
    pdf = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
    try:
        # The destination is fixed; redirects cannot turn this into an arbitrary URL fetch.
        with requests.get(document_url(ada), stream=True, allow_redirects=False,
                          timeout=DIAVGEIA_TIMEOUT) as response:
            if response.status_code == 404:
                raise DocumentError("Document not found.", 404)
            if response.status_code != 200:
                raise DocumentError("The PDF is temporarily unavailable.")
            if response.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/pdf":
                raise DocumentError("Diavgeia did not return a PDF.")
            declared = response.headers.get("Content-Length", "")
            if declared.isdigit() and int(declared) > MAX_PDF_BYTES:
                raise DocumentError("The PDF is too large to preview. Download it directly.", 413)
            length = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                length += len(chunk)
                if length > MAX_PDF_BYTES:
                    raise DocumentError("The PDF is too large to preview. Download it directly.", 413)
                pdf.write(chunk)
            pdf.seek(0)
            if pdf.read(5) != b"%PDF-":
                raise DocumentError("Diavgeia did not return a valid PDF.")
            pdf.seek(0)
            return pdf, length
    except requests.RequestException as exc:
        pdf.close()
        raise DocumentError("The PDF is temporarily unavailable.", 503) from exc
    except Exception:
        pdf.close()
        raise
