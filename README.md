# PolicyMind

A free-stack RAG chatbot over the PSU OMC **Dealer Selection Guidelines (June 2023)**.
Built for internal use by oil-marketing-company employees who need to navigate the
183-page policy document quickly.

- **Embeddings:** BAAI/bge-base-en-v1.5 (runs locally, no API cost)
- **Vector store:** ChromaDB (local persistent)
- **Sparse search:** BM25 via rank-bm25
- **Reranker:** cross-encoder/ms-marco-MiniLM-L-6-v2
- **LLM:** Groq's free Llama 3.3 70B endpoint
- **UI:** Streamlit

## How it works

1. The policy PDF is parsed into 181 chunks using a hierarchical parent/child scheme
   — each numbered section (1-33) becomes a parent chunk; sub-sections become children.
   Annexures and appendices are one chunk each.
2. At query time, hybrid retrieval combines BGE dense vectors with BM25 keyword search
   via Reciprocal Rank Fusion, then a cross-encoder reranks the top candidates.
3. The top results are sent to Llama 3.3 via Groq with a strict system prompt that
   forces section + page citations.

## Deploy to Streamlit Community Cloud (free public URL)

1. Push this repo to GitHub (private is fine).
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. Click **New app** and select this repo. Set:
   - **Main file path:** `chatbot/app.py`
   - **Python version:** 3.11 (auto-detected from `runtime.txt`)
4. Click **Advanced settings → Secrets** and paste:
   ```toml
   PDF_URL = "https://drive.google.com/file/d/YOUR_FILE_ID/view"
   ```
   See **PDF hosting** below for how to get a `PDF_URL`.
5. Click **Deploy**. First boot takes ~3-5 minutes (downloads models, builds index).
6. Streamlit gives you a URL like `https://yourapp.streamlit.app` — share it with colleagues.

## PDF hosting (Google Drive, free)

The policy PDF is never committed to the repo. Host it once:

1. Upload `26-06-2023 Dealer Selection Guidelines 2023 - June 2023 final.pdf`
   to your Google Drive.
2. Right-click → **Share** → change "General access" to **Anyone with the link** (Viewer).
3. Copy the share link. It looks like:
   `https://drive.google.com/file/d/1AbC...XYZ/view?usp=sharing`
4. Paste that link as the `PDF_URL` secret in Streamlit Cloud.

The app uses `gdown` to fetch the PDF on first boot and caches it for subsequent restarts.

## Local development

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set PDF location (either local file or PDF_URL env var)
# If you have the PDF locally, edit chatbot/config.py: LOCAL_PDF_PATH
# Otherwise:
$env:PDF_URL = "https://drive.google.com/file/d/YOUR_ID/view"

# 3. Build the index (one-time)
cd chatbot
python ingest.py

# 4. Launch
python -m streamlit run app.py
```

Open http://localhost:8501 and paste your free Groq API key
(get one at https://console.groq.com — no credit card needed).

## Repository layout

```
.
├── chatbot/
│   ├── app.py            # Streamlit UI + LLM call
│   ├── retrieval.py      # Hybrid dense+sparse search + rerank + parent promotion
│   ├── ingest.py         # PDF → chunks → ChromaDB + BM25
│   ├── pdf_loader.py     # Local-or-download PDF resolver
│   ├── config.py         # Models, paths, section titles, abbreviations
│   └── make_guide.py     # Generates the end-user PDF runbook
├── .streamlit/
│   └── secrets.toml.example
├── requirements.txt
├── runtime.txt           # Pins Python 3.11 for Streamlit Cloud
├── .gitignore            # Keeps PDF, secrets, and indexes out of git
└── README.md
```

## Notes

- This chatbot serves a document marked "Restricted for Internal Use Only."
  Do not commit the PDF. Do not deploy the URL publicly outside your org's intended users.
- Each colleague enters their own free Groq API key in the sidebar — there is no
  shared key, so usage costs nothing and rate limits are per-user.
- Switching the repo from private to public later is safe IF you have never committed
  the PDF or any `.env` / `secrets.toml` files. The `.gitignore` here prevents that.
