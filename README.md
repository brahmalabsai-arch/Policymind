# PolicyMind

**Live demo:** [https://policymind-bcmuu45m7qfhnvrjiagunr.streamlit.app/](https://policymind-bcmuu45m7qfhnvrjiagunr.streamlit.app/)

A production-style RAG chatbot built over a 183-page government policy document
(the PSU OMC Dealer Selection Guidelines, June 2023). PolicyMind shows how to
take a long, hierarchical, dense PDF and turn it into a citation-backed
question-answering assistant — using a **fully free stack**, no paid APIs, no
managed vector DB, no GPU.

## Architecture

| Layer | Choice | Why |
|---|---|---|
| Embeddings | `BAAI/bge-base-en-v1.5` | Best-in-class open-source dense retriever for policy/legal text. Runs on CPU. |
| Vector store | ChromaDB (persistent) | Local, free, zero-config. |
| Sparse retriever | BM25 (`rank-bm25`) | Catches exact terms (fee amounts, section numbers, abbreviations) that dense search misses. |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cuts top-20 candidates down to a precise top-5. |
| LLM | Llama 3.3 70B via Groq | Free tier, very fast inference, no credit card. |
| UI | Streamlit | Single file, deploys to Streamlit Cloud for free. |

## How retrieval works

1. **Hierarchical chunking.** The PDF splits into three tiers — 33 policy sections (parent/child chunks), annexures (template letters), and appendices (forms). Section detection walks `1 → 33` sequentially to survive trailing colons, en-dashes, curly quotes, and mixed-case headings in the source.
2. **Hybrid retrieval.** Every query hits both a BGE dense index and a BM25 sparse index. Results are fused via Reciprocal Rank Fusion (RRF), then a query router boosts chunks from sections the question is likely about (fees → §16-17, eligibility → §6-8, etc.).
3. **Cross-encoder reranking.** Top 20 fused candidates get re-scored by a cross-encoder, then deduplicated by parent section.
4. **Parent promotion.** Children retrieved at the chunk level get promoted to their full parent section before being sent to the LLM — small-to-big retrieval avoids the classic "right paragraph, wrong context" problem.
5. **Strict prompting.** The system prompt forces section + page citations on every answer.

## Deploy your own copy

1. Fork this repo to your GitHub account.
2. Go to **https://share.streamlit.io**, sign in with GitHub, click **New app**.
3. Select the fork. Set:
   - **Main file path:** `chatbot/app.py`
4. **Advanced settings → Secrets**, paste:
   ```toml
   PDF_URL = "https://drive.google.com/file/d/YOUR_FILE_ID/view"
   ```
5. Click **Deploy**. First boot takes ~5 minutes (model + index build).

### Hosting your own PDF

The policy PDF is intentionally not committed. Upload yours to Google Drive:

1. Drive → upload PDF
2. Right-click → **Share** → "Anyone with the link" (Viewer)
3. Copy the link, paste it as `PDF_URL` in the Streamlit secret above
4. The app uses `gdown` to fetch it on first boot and caches it for restarts

## Local development

```powershell
# 1. Install deps
pip install -r requirements.txt

# 2. Either drop the PDF at the path in chatbot/config.py: LOCAL_PDF_PATH
#    or set the env var:
$env:PDF_URL = "https://drive.google.com/file/d/YOUR_ID/view"

# 3. Build the index (one-time, ~2 min)
cd chatbot
python ingest.py

# 4. Launch
python -m streamlit run app.py
```

Open http://localhost:8501, paste a free Groq API key from https://console.groq.com.

## Repository layout

```
.
├── chatbot/
│   ├── app.py            # Streamlit UI + LLM call
│   ├── retrieval.py      # Hybrid search + rerank + parent promotion
│   ├── ingest.py         # PDF → chunks → ChromaDB + BM25
│   ├── pdf_loader.py     # Local-or-download PDF resolver
│   ├── config.py         # Models, paths, section titles, abbreviation glossary
│   └── make_guide.py     # Generates the end-user PDF runbook
├── .streamlit/
│   └── secrets.toml.example
├── requirements.txt
├── runtime.txt
├── .gitignore
└── README.md
```

## Design notes

- **Why hybrid retrieval, not just dense?** Policy docs have hard-edged terminology — exact fee amounts (`Rs.3000`), section numbers, abbreviations (`SC/ST`, `OMC`, `LOI`). Pure semantic search misses these. BM25 catches them, RRF combines both.
- **Why parent-child chunking?** Long sections (Section 6 spans 11 pages) won't fit in a single embeddable chunk, but their sub-paragraphs are too narrow on their own. Storing both lets retrieval be precise and context be complete.
- **Why a sequential section walker, not regex?** The original "all-caps line" regex missed seven of 33 sections because the source PDF mixes ALL-CAPS, mixed-case, trailing colons, and en-dashes. Walking `1 → 33` and finding each next header after the previous one is robust to all of that.
- **Why Groq?** Fast, free for the personal-key model used here. The app expects each user to bring their own key so there's no shared rate limit or cost.

## License

MIT. See `LICENSE`.
