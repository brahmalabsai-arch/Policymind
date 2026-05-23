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
APP_URL = "https://policymind-bcmuu45m7qfhnvrjiagunr.streamlit.app/"

# Colours
PRIMARY = HexColor("#0B5394")
ACCENT  = HexColor("#E07B00")
LIGHT   = HexColor("#EFF3F8")
MONO_BG = HexColor("#F4F4F4")
RULE    = HexColor("#C9D2DD")

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
url_style = ParagraphStyle(
    "URL", parent=body, fontName="Courier-Bold", fontSize=11, leading=14,
    textColor=PRIMARY, spaceAfter=10,
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
        author="Rakesh Brahma",
    )

    story = []

    # ----- Cover -----
    story.append(Paragraph("PolicyMind", title_style))
    story.append(Paragraph(
        "How to use your Dealer Selection Guidelines chatbot &mdash; a quick guide "
        "for any colleague who wants to look something up.",
        subtitle_style,
    ))
    story.append(hr())
    story.append(Spacer(1, 12))

    # ----- Open the app -----
    story.append(Paragraph("Open the app", h1))
    story.append(Paragraph("PolicyMind lives at:", body))
    story.append(Paragraph(f'<a href="{APP_URL}"><u>{APP_URL}</u></a>', url_style))
    story.append(Paragraph(
        "No download, no install. Just open the link in Chrome, Edge, or any modern browser. "
        "Bookmark it &mdash; you&rsquo;ll be back.",
        body,
    ))

    # ----- What you can ask -----
    story.append(Paragraph("What you can ask", h1))
    story.append(Paragraph(
        "PolicyMind answers questions about the PSU OMC <i>Dealer Selection Guidelines "
        "(June 2023)</i>. It reads the full 183-page document and always cites the section "
        "and page number it&rsquo;s quoting. Try things like:",
        body,
    ))
    examples = [
        "What are the eligibility criteria for an SC/ST individual applicant?",
        "What is the non-refundable application fee for a rural OBC location?",
        "Explain the online draw of lots procedure step by step.",
        "What disqualifies an applicant?",
        "What infrastructure must a CC Rural retail outlet have?",
        "How can I file a grievance about the selection process?",
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(f"<i>{q}</i>", body), leftIndent=6) for q in examples],
        bulletType="bullet", bulletColor=ACCENT, leftIndent=12,
    ))

    story.append(PageBreak())

    # ----- Steps -----
    story.append(Paragraph("Three-step setup (one time)", h1))
    story.append(Spacer(1, 6))

    # Step 1
    story.append(step_header(1, "Get a free Groq API key"))
    story.append(Paragraph(
        "Groq runs the language model behind PolicyMind. The free tier covers far more "
        "queries than a single user can make in a day, and no credit card is required.",
        body,
    ))
    story.append(ListFlowable([
        ListItem(Paragraph("Open <b>https://console.groq.com</b> in your browser.", body)),
        ListItem(Paragraph("Sign in with Google or email.", body)),
        ListItem(Paragraph("Go to <b>API Keys</b> &rarr; click <b>Create API Key</b>.", body)),
        ListItem(Paragraph("Copy the key (starts with <font name='Courier'>gsk_&hellip;</font>) and save it somewhere safe.", body)),
    ], bulletType="1", leftIndent=14))
    story.append(note(
        "You only need to do this once. The same key works every visit."
    ))

    # Step 2
    story.append(step_header(2, "Open the chatbot and paste your key"))
    story.append(Paragraph(
        f'Open <a href="{APP_URL}"><u>{APP_URL}</u></a> and paste your '
        '<font name="Courier">gsk_&hellip;</font> key into the <b>Groq API Key</b> box '
        'on the left sidebar. The key is held in your browser session only &mdash; it '
        'never reaches the chatbot&rsquo;s server.',
        body,
    ))

    # Step 3
    story.append(step_header(3, "Ask a question"))
    story.append(Paragraph(
        "Either click one of the <b>Quick Questions</b> buttons in the sidebar, or type "
        "your own question in the chat box at the bottom of the page.",
        body,
    ))
    story.append(Paragraph(
        "Every answer cites the Section number and page number from the source PDF. "
        "Click <b>View Sources</b> below the answer to see exactly which chunks of the "
        "policy were used.",
        body,
    ))

    # ----- Tips -----
    story.append(Paragraph("Tips for better answers", h1))
    tips = [
        "<b>Be specific about category.</b> &ldquo;What is the application fee for an OBC rural location?&rdquo; works far better than &ldquo;What is the fee?&rdquo;",
        "<b>Name what you&rsquo;re looking for.</b> Asking &ldquo;What documents do I need for the affidavit?&rdquo; routes the search to the right appendix; &ldquo;What about the affidavit?&rdquo; is too vague.",
        "<b>Ask follow-ups.</b> The chatbot remembers the last few turns. You can refine without restating context.",
        "<b>Check the sources.</b> When the answer matters, expand <i>View Sources</i> and confirm the cited section and page in the original PDF.",
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(t, body), leftIndent=6) for t in tips],
        bulletType="bullet", bulletColor=ACCENT, leftIndent=12,
    ))

    # ----- Troubleshooting -----
    story.append(Paragraph("Troubleshooting", h1))

    trouble = [
        ("The page is loading slowly the first time",
         "If no one has used PolicyMind in the last ~12 hours, the hosting service puts "
         "the app to sleep. The first visit wakes it up and can take 30&ndash;60 seconds. "
         "Just wait &mdash; subsequent visits are instant."),
        ('"Please enter your Groq API key"',
         "You need to paste your <font name='Courier'>gsk_&hellip;</font> key in the "
         "sidebar before asking a question. See Step 1 if you don&rsquo;t have one."),
        ("Groq rate-limit error",
         "The free tier allows 30 requests/min. If you&rsquo;re sending questions back-to-back, "
         "wait a minute and try again."),
        ("The answer says &lsquo;refer to the OMC office&rsquo;",
         "That means PolicyMind didn&rsquo;t find a confident match in the policy text. "
         "Try rephrasing the question, or add specifics (category, RO type, market class)."),
        ("The cited page doesn&rsquo;t match",
         "Page numbers refer to the source PDF&rsquo;s internal page numbers. If you have a "
         "differently-paginated copy, the section number is the reliable reference."),
    ]
    rows = [[Paragraph(f"<b>{q}</b>", small), Paragraph(a, small)] for q, a in trouble]
    tbl = Table(rows, colWidths=[5.6 * cm, 10.4 * cm])
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

    story.append(Spacer(1, 14))
    story.append(hr())
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'<i>App URL: <a href="{APP_URL}"><u>{APP_URL}</u></a>'
        '<br/>Policy source: PSU OMC Dealer Selection Guidelines, June 2023, Version 1.0.</i>',
        small,
    ))

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(f"Generated: {OUT}")


if __name__ == "__main__":
    build()
