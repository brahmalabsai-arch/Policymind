"""
PolicyMind — Dealer Selection Guidelines Chatbot
Run: streamlit run app.py
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq, APIError

from config import GROQ_MODEL, CHROMA_DB_PATH, BM25_INDEX_PATH, ABBREVIATIONS

load_dotenv()


# ---------------------------------------------------------------------------
# First-boot bootstrap: build the index if missing (Streamlit Cloud cold start)
# ---------------------------------------------------------------------------

def _index_present() -> bool:
    chroma_ok = Path(CHROMA_DB_PATH).exists() and any(Path(CHROMA_DB_PATH).iterdir())
    bm25_ok = Path(BM25_INDEX_PATH).exists()
    return chroma_ok and bm25_ok


@st.cache_resource(show_spinner=False)
def _bootstrap_index() -> bool:
    """Run once per container. Builds index from the PDF if not already present."""
    if _index_present():
        return True
    from ingest import run_ingest
    run_ingest()
    return True


with st.spinner("First-time setup: downloading models and building search index (1-2 min)…"):
    _bootstrap_index()

from retrieval import search  # noqa: E402  (import after bootstrap so models cache)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are PolicyMind, an expert assistant for PSU Oil Marketing Company's \
Dealer Selection Guidelines (June 2023, Version 1.0).

Your role is to help internal OMC employees understand and apply the dealer selection policy accurately.

RULES:
1. Answer ONLY based on the provided policy context. Never guess or hallucinate policy details.
2. Always cite the Section number and Page number: "As per Section X (Page Y)..."
3. When multiple sections apply, synthesize clearly.
4. For category-specific rules (SC/ST, OBC, Open, Defence, etc.) always specify which category.
5. Note NE state exceptions (Arunachal Pradesh, Meghalaya, Nagaland, Mizoram) when relevant.
6. Quote numerical values (fees, percentages, distances, volumes) exactly as in the policy.
7. If the context doesn't contain the answer, say so and suggest the user refer to the OMC office.
8. Keep answers concise but complete. Use bullet points for lists.

Key abbreviations for reference:
{chr(10).join(f'- {k}: {v}' for k, v in ABBREVIATIONS.items())}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_context(results: list[dict]) -> str:
    parts = []
    for r in results:
        m = r["metadata"]
        header = (
            f"[Section {m.get('section_id', '?')}: {m.get('section_title', '')} "
            f"| Pages {m.get('page_start', '?')}–{m.get('page_end', '?')} "
            f"| {m.get('document_part', '').upper()}]"
        )
        parts.append(f"{header}\n{r['text']}")
    return "\n\n---\n\n".join(parts)


def build_messages(current_question: str, context: str, history: list[dict]) -> list[dict]:
    """Inject fresh context into the current turn; keep clean history."""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Last 6 messages of clean history (3 user/assistant turns)
    for m in history[-6:]:
        msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({
        "role": "user",
        "content": f"Policy Context:\n{context}\n\nQuestion: {current_question}",
    })
    return msgs


def ask(question: str, history: list[dict], api_key: str) -> tuple[str, list[dict]]:
    results = search(question)
    context = format_context(results)
    messages = build_messages(question, context, history)

    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
    )
    answer = resp.choices[0].message.content
    return answer, results


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PolicyMind – Dealer Selection Chatbot",
    page_icon="⛽",
    layout="wide",
)

# --- Sidebar ---
with st.sidebar:
    st.title("⛽ PolicyMind")
    st.caption("PSU OMC Dealer Selection Guidelines\nJune 2023 • Internal Use Only")
    st.divider()

    api_key = st.text_input(
        "Groq API Key",
        type="password",
        value=os.getenv("GROQ_API_KEY", ""),
        help="Free key at console.groq.com — no credit card required",
    )
    if not api_key:
        st.warning("Enter your Groq API key to start.")

    st.divider()
    st.subheader("Quick Questions")

    quick = {
        "Eligibility – Individual":      "What are the eligibility criteria for individual applicants?",
        "Eligibility – Non-Individual":  "What are the eligibility criteria for companies or partnerships?",
        "Application Fees":              "What are the non-refundable application fees for different categories and RO types?",
        "Selection Process":             "Explain the dealer selection process step by step.",
        "Disqualification Criteria":     "What are the disqualification criteria for applicants?",
        "SC/ST Financial Assistance":    "What financial assistance is available under the Corpus Fund Scheme for SC/ST dealers?",
        "Letter of Intent":              "What are the obligations after receiving a Letter of Intent (LOI)?",
        "Grievance Process":             "How can I file a grievance or complaint against the selection process?",
        "Security Deposit":              "What is the security deposit amount and when is it refunded?",
        "NE State Reservations":         "What are the reservation percentages for North Eastern states?",
    }

    for label, question in quick.items():
        if st.button(label, use_container_width=True):
            st.session_state.preset_q = question

    st.divider()
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sources = {}
        st.rerun()

# --- Main area ---
st.title("PolicyMind – Dealer Selection Chatbot")
st.caption("Ask anything about the PSU OMC Dealer Selection Guidelines (June 2023)")

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sources" not in st.session_state:
    st.session_state.sources = {}
if "preset_q" not in st.session_state:
    st.session_state.preset_q = None

# Render chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and i in st.session_state.sources:
            with st.expander("View Sources", expanded=False):
                for src in st.session_state.sources[i]:
                    m = src["metadata"]
                    st.markdown(
                        f"**{m.get('section_title', 'N/A')}**  \n"
                        f"Section {m.get('section_id', '?')} | "
                        f"Pages {m.get('page_start', '?')}–{m.get('page_end', '?')} | "
                        f"{m.get('document_part', '').upper()}"
                    )

# Handle input
preset = st.session_state.pop("preset_q", None)
user_input = st.chat_input("Ask about the dealer selection policy...") or preset

if user_input:
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()

    # Show user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching policy and generating answer…"):
            try:
                clean_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                ]
                answer, sources = ask(user_input, clean_history, api_key)
                st.markdown(answer)

                msg_idx = len(st.session_state.messages)
                st.session_state.sources[msg_idx] = sources

                with st.expander("View Sources", expanded=False):
                    for src in sources:
                        m = src["metadata"]
                        st.markdown(
                            f"**{m.get('section_title', 'N/A')}**  \n"
                            f"Section {m.get('section_id', '?')} | "
                            f"Pages {m.get('page_start', '?')}–{m.get('page_end', '?')} | "
                            f"{m.get('document_part', '').upper()}"
                        )

                st.session_state.messages.append({"role": "assistant", "content": answer})

            except APIError as e:
                st.error(f"Groq API error: {e}")
            except FileNotFoundError:
                st.error("BM25 index missing. Re-run `python ingest.py`.")
            except Exception as e:
                st.error(f"Error: {e}")
