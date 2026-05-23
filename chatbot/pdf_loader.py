"""
PDF source resolver.

Order of preference:
  1. Local dev path (LOCAL_PDF_PATH from config) — for local runs.
  2. Already-downloaded cache file — for subsequent boots on cloud.
  3. Download from PDF_URL (env var / Streamlit secret) — first cloud boot.

PDF_URL supports:
  - Direct HTTPS link to a .pdf
  - Google Drive share link: https://drive.google.com/file/d/FILE_ID/view  (set sharing to "Anyone with link")
"""

import os
import re
import sys
from pathlib import Path

from config import LOCAL_PDF_PATH, PDF_CACHE_PATH


def _is_gdrive(url: str) -> str | None:
    """Return Google Drive file ID if url is a Drive link, else None."""
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([\w-]{20,})", url)
    return m.group(1) if m else None


def _download_gdrive(file_id: str, dest: Path) -> None:
    try:
        import gdown
    except ImportError:
        print("Installing gdown...", file=sys.stderr)
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown", "-q"])
        import gdown
    dest.parent.mkdir(parents=True, exist_ok=True)
    gdown.download(id=file_id, output=str(dest), quiet=False)


def _download_http(url: str, dest: Path) -> None:
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}", file=sys.stderr)
    urllib.request.urlretrieve(url, dest)


def resolve_pdf() -> Path:
    """Return a Path to the policy PDF on disk, downloading if needed."""
    # 1. Local dev
    if LOCAL_PDF_PATH.exists():
        return LOCAL_PDF_PATH
    # 2. Already cached
    if PDF_CACHE_PATH.exists() and PDF_CACHE_PATH.stat().st_size > 1000:
        return PDF_CACHE_PATH
    # 3. Download
    url = _read_pdf_url()
    if not url:
        raise FileNotFoundError(
            "Policy PDF not found locally and PDF_URL is not configured.\n"
            "Set PDF_URL in .streamlit/secrets.toml (cloud) or as an environment "
            "variable (local)."
        )
    gid = _is_gdrive(url)
    try:
        if gid:
            _download_gdrive(gid, PDF_CACHE_PATH)
        else:
            _download_http(url, PDF_CACHE_PATH)
    except Exception:
        # Never propagate the URL — it would surface in Streamlit's st.error()
        # and leak the secret to end users.
        raise RuntimeError(
            "PDF download failed. Check the PDF_URL secret in Streamlit Cloud "
            "and confirm the source link is reachable."
        ) from None
    if not PDF_CACHE_PATH.exists() or PDF_CACHE_PATH.stat().st_size < 1000:
        raise RuntimeError(
            "PDF download produced an empty or missing file. "
            "Check the PDF_URL secret in Streamlit Cloud."
        )
    return PDF_CACHE_PATH


def _read_pdf_url() -> str | None:
    """Resolve PDF_URL from Streamlit secrets first, then env var."""
    # Streamlit secrets — only available when running inside Streamlit
    try:
        import streamlit as st
        # st.secrets raises if no secrets file; guard with try
        if "PDF_URL" in st.secrets:
            return str(st.secrets["PDF_URL"]).strip()
    except Exception:
        pass
    return os.getenv("PDF_URL", "").strip() or None


if __name__ == "__main__":
    p = resolve_pdf()
    print(f"PDF available at: {p}")
