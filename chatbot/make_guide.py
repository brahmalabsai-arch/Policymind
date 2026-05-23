"""Generate PolicyMind_User_Guide.pdf using reportlab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, ListFlowable, ListItem,
)

OUT = "PolicyMind_User_Guide.pdf"

# Colours
PRIMARY = HexColor("#0B5394")
ACCENT  = HexColor("#E07B00")
LIGHT   = HexColor("#EFF3F8")
MONO_BG = HexColor("#F4F4F4")
RULE    = HexColor("#C9D2DD")

# Styles
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleX", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=24, leading=28,
    textColor=PRIMARY, spaceAfter=6,
)
subtitle_style = ParagraphStyle(
    "Subtitle", parent=styles["Normal"],
    fontName="Helvetica", fontSize=11, leading=14,
    textColor=HexColor("#555555"), spaceAfter=18,
)
h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontName="Helvetica-Bold", fontSize=15, leading=20,
    textColor=PRIMARY, spaceBefore=14, spaceAfter=8,
)
h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=12, leading=16,
    textColor=black, spaceBefore=10, spaceAfter=6,
)
body = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontName="Helvetica", fontSize=10.5, leading=15,
    alignment=TA_LEFT, spaceAfter=6,
)
small = ParagraphStyle(
    "Small", parent=body, fontSize=9, leading=12,
    textColor=HexColor("#555555"),
)
code = ParagraphStyle(
    "Code", parent=styles["Code"],
    fontName="Courier", fontSize=9.5, leading=13,
    backColor=MONO_BG, borderColor=RULE, borderWidth=0.5,
    borderPadding=(6, 8, 6, 8), spaceBefore=4, spaceAfter=10,
    textColor=HexColor("#222222"),
)
note_style = ParagraphStyle(
    "Note", parent=body, fontSize=10, leading=14,
    backColor=LIGHT, borderColor=PRIMARY, borderWidth=0,
    leftIndent=10, borderPadding=(8, 10, 8, 10), spaceAfter=10,
)

def hr():
    t = Table([[""]], colWidths=[16 * cm], rowHeights=[0.5])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.6, RULE)]))
    return t

def step_header(num: int, text: str):
    """Coloured step badge + heading on one row."""
    badge = Paragraph(f"<font color='white'><b>{num}</b></font>", ParagraphStyle(
        "Badge", parent=body, alignment=1, fontSize=14, leading=18,
    ))
    heading = Paragraph(f"<b>{text}</b>", ParagraphStyle(
        "StepH", parent=h2, spaceBefore=0, spaceAfter=0, fontSize=13, leading=18,
    ))
    t = Table([[badge, heading]], colWidths=[0.9 * cm, 15.1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t

def cmd(text: str):
    return Paragraph(text.replace("\n", "<br/>"), code)

def note(text: str):
    return Paragraph(f"<b>Note &nbsp;</b>{text}", note_style)

def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#888888"))
    canvas.drawString(2 * cm, 1.2 * cm, "PolicyMind — Dealer Selection Chatbot")
    canvas.drawRightString(19 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.5 * cm, 19 * cm, 1.5 * cm)
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        OUT, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title="PolicyMind User Guide",
        author="Internal",
    )

    story = []

    # ----- Cover header -----
    story.append(Paragraph("PolicyMind", title_style))
    story.append(Paragraph(
        "How to run your Dealer Selection Guidelines chatbot &mdash; "
        "a step-by-step guide for restarting the application on your own machine.",
        subtitle_style,
    ))
    story.append(hr())
    story.append(Spacer(1, 10))

    # ----- What you are running -----
    story.append(Paragraph("What you are running", h1))
    story.append(Paragraph(
        "A fully local, free-to-run RAG chatbot over the PSU OMC <i>Dealer Selection "
        "Guidelines (June 2023)</i>. It uses BGE embeddings + ChromaDB + BM25 for retrieval, "
        "a cross-encoder for reranking, and Groq&#39;s free Llama 3.3 endpoint for answers. "
        "Everything except the LLM call runs on your machine; no documents leave your computer.",
        body,
    ))

    # ----- Prerequisites -----
    story.append(Paragraph("Prerequisites (one-time)", h1))
    prereq_items = [
        "<b>Python 3.10 or newer</b> already installed (you have Python 3.13).",
        "<b>Project folder</b> at <font name='Courier'>D:\\PERSONAL_PROJECTS\\POLICYMIND\\RETRIEVAL AND CHUNKING WITH CLAUDE CODE\\chatbot\\</font>.",
        "<b>A free Groq API key</b> &mdash; see Step 1 below.",
        "<b>~3 GB free disk space</b> for the embedding + reranker models (already downloaded if you have run it once).",
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(t, body), leftIndent=6) for t in prereq_items],
        bulletType="bullet", bulletColor=ACCENT, leftIndent=12,
    ))

    story.append(PageBreak())

    # ----- Steps -----
    story.append(Paragraph("Steps to run the chatbot", h1))
    story.append(Spacer(1, 6))

    # Step 1
    story.append(step_header(1, "Get a free Groq API key (one-time only)"))
    story.append(Paragraph(
        "Groq provides a generous free tier for Llama 3.3 70B &mdash; no credit card required.",
        body,
    ))
    story.append(ListFlowable([
        ListItem(Paragraph("Open <b>https://console.groq.com</b> in your browser.", body)),
        ListItem(Paragraph("Sign in with Google or email.", body)),
        ListItem(Paragraph("Go to <b>API Keys</b> &rarr; click <b>Create API Key</b>.", body)),
        ListItem(Paragraph("Copy the key (starts with <font name='Courier'>gsk_&hellip;</font>) and save it somewhere safe.", body)),
    ], bulletType="1", leftIndent=14))
    story.append(note(
        "You only need to do this once. The same key works every time you launch the chatbot."
    ))

    # Step 2
    story.append(step_header(2, "Open PowerShell in the project folder"))
    story.append(Paragraph(
        "Press <b>Win + R</b>, type <b>powershell</b>, press Enter. Then run:",
        body,
    ))
    story.append(cmd('cd "D:\\PERSONAL_PROJECTS\\POLICYMIND\\RETRIEVAL AND CHUNKING WITH CLAUDE CODE\\chatbot"'))

    # Step 3
    story.append(step_header(3, "Launch the chatbot"))
    story.append(Paragraph("Run the Streamlit app via Python:", body))
    story.append(cmd("python -m streamlit run app.py"))
    story.append(Paragraph(
        "Streamlit will print a URL like <font name='Courier'>http://localhost:8501</font> "
        "and your browser should open automatically. If it doesn&#39;t, copy that URL into Chrome / Edge yourself.",
        body,
    ))
    story.append(note(
        "First launch after a reboot may take 30-60 seconds while the embedding and "
        "reranker models load into memory. Subsequent queries are fast."
    ))

    # Step 4
    story.append(step_header(4, "Paste your Groq API key in the sidebar"))
    story.append(Paragraph(
        "In the left sidebar, paste your <font name='Courier'>gsk_&hellip;</font> key into the "
        "<b>Groq API Key</b> box. The key is held in memory only &mdash; it is not saved to disk.",
        body,
    ))
    story.append(note(
        "Want to skip pasting every time? Create a file named "
        "<font name='Courier'>.env</font> in the chatbot folder with one line: "
        "<font name='Courier'>GROQ_API_KEY=gsk_your_key_here</font>. "
        "Streamlit will pick it up automatically on next launch."
    ))

    # Step 5
    story.append(step_header(5, "Ask a question"))
    story.append(Paragraph(
        "Either click one of the <b>Quick Questions</b> buttons in the sidebar, or type your own "
        "question in the chat box at the bottom of the page. Examples:",
        body,
    ))
    examples = [
        "What are the eligibility criteria for an SC/ST individual applicant?",
        "What is the non-refundable application fee for a rural OBC location?",
        "Explain the online draw of lots procedure.",
        "What disqualifies an applicant?",
        "What infrastructure must a CC Rural retail outlet have?",
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(f"<i>{q}</i>", body), leftIndent=6) for q in examples],
        bulletType="bullet", bulletColor=ACCENT, leftIndent=12,
    ))
    story.append(Paragraph(
        "Every answer cites the <b>Section number</b> and <b>page number</b> from the source PDF. "
        "Click <b>View Sources</b> below the answer to see exactly which chunks were used.",
        body,
    ))

    story.append(PageBreak())

    # Step 6
    story.append(step_header(6, "Stop the chatbot when you are done"))
    story.append(Paragraph(
        "Go back to the PowerShell window where Streamlit is running and press "
        "<b>Ctrl + C</b>. The browser tab can simply be closed.",
        body,
    ))
    story.append(note(
        "Closing the browser tab does NOT stop the server. You must press Ctrl+C in PowerShell."
    ))

    # ----- Troubleshooting -----
    story.append(Paragraph("Troubleshooting", h1))

    trouble = [
        ("&#39;streamlit&#39; is not recognized",
         "Always launch via <font name='Courier'>python -m streamlit run app.py</font>. "
         "The bare <font name='Courier'>streamlit</font> command isn&#39;t on your PATH."),
        ("Browser shows &#39;Index not found&#39;",
         "Re-build the search index once: <font name='Courier'>python ingest.py</font>. "
         "Takes 1-2 minutes."),
        ("Groq API error / rate limit",
         "The free tier allows 30 requests/min and 14,400 requests/day. Wait a minute and retry. "
         "If your key is invalid, regenerate it at console.groq.com."),
        ("Port 8501 already in use",
         "Another Streamlit is still running. Either close it via Ctrl+C in its window, or "
         "launch on a different port: <font name='Courier'>python -m streamlit run app.py "
         "--server.port 8502</font>."),
        ("Models re-downloading every launch",
         "The HuggingFace cache lives at <font name='Courier'>C:\\Users\\&lt;you&gt;\\.cache\\huggingface</font>. "
         "Don&#39;t delete it &mdash; that&#39;s where the ~750 MB of models are stored."),
    ]

    rows = [[Paragraph(f"<b>{q}</b>", small), Paragraph(a, small)] for q, a in trouble]
    tbl = Table(rows, colWidths=[5.2 * cm, 10.8 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
        ("BOX", (0, 0), (-1, -1), 0.4, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10))

    # ----- File map -----
    story.append(Paragraph("What lives where", h1))
    file_rows = [
        [Paragraph("<b>File</b>", small), Paragraph("<b>What it does</b>", small)],
        [Paragraph("app.py", small),         Paragraph("The Streamlit user interface.", small)],
        [Paragraph("retrieval.py", small),   Paragraph("Hybrid dense + sparse search, reranking, parent-promotion.", small)],
        [Paragraph("ingest.py", small),      Paragraph("PDF &rarr; chunks &rarr; ChromaDB + BM25. Only re-run if the PDF changes.", small)],
        [Paragraph("config.py", small),      Paragraph("Model names, paths, section titles, abbreviation glossary.", small)],
        [Paragraph("chroma_db/", small),     Paragraph("Persistent vector index (~5 MB).", small)],
        [Paragraph("bm25_index.pkl", small), Paragraph("Persistent BM25 keyword index.", small)],
    ]
    ftbl = Table(file_rows, colWidths=[5.2 * cm, 10.8 * cm])
    ftbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
        ("BOX", (0, 0), (-1, -1), 0.4, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ftbl)

    story.append(Spacer(1, 14))
    story.append(hr())
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<i>Generated for internal use. Policy source: Dealer Selection Guidelines, June 2023, "
        "Version 1.0/10.06.2023.</i>",
        small,
    ))

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(f"Generated: {OUT}")


if __name__ == "__main__":
    build()
