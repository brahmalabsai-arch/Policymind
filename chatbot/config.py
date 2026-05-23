import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# --- PDF source ---
# Local dev path (used when present); cloud deploy fetches via PDF_URL secret.
LOCAL_PDF_PATH = Path(r"D:\PERSONAL_PROJECTS\POLICYMIND\26-06-2023 Dealer Selection Guidelines 2023 - June 2023 final.pdf")
# Cached location after download (under repo, gitignored)
PDF_CACHE_PATH = BASE_DIR / "data" / "policy.pdf"

def get_pdf_path() -> Path:
    """Return the PDF path: local if present (dev), else the downloaded cache (cloud)."""
    if LOCAL_PDF_PATH.exists():
        return LOCAL_PDF_PATH
    return PDF_CACHE_PATH

CHROMA_DB_PATH = str(BASE_DIR / "chroma_db")
BM25_INDEX_PATH = str(BASE_DIR / "bm25_index.pkl")

# --- Free open-source models ---
# bge-base picked over bge-large to fit Streamlit Cloud's 1 GB RAM limit
# with negligible quality loss for policy/legal text.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")   # ~440 MB
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # ~85 MB

# Groq free tier: llama-3.3-70b-versatile, no credit card required
# Get key at https://console.groq.com
GROQ_MODEL = "llama-3.3-70b-versatile"

# Retrieval tuning
N_RETRIEVE = 20   # candidates fetched before reranking
TOP_K = 5         # final chunks sent to LLM

# Chunking
CHILD_CHUNK_WORDS = 400
CHILD_CHUNK_OVERLAP = 50
MAX_CHARS_PER_CHUNK = 4000

# Document boundary pages (1-indexed)
POLICY_END_PAGE = 45
ANNEXURE_END_PAGE = 133

SECTION_TITLES = {
    "0":  "Introduction",
    "1":  "Identification of Locations",
    "2":  "State Retail Marketing Plan (SRMP)",
    "3":  "Reservation",
    "4":  "Rostering of Locations and Type of RO Sites",
    "5":  "Type of Retail Outlet Sites",
    "6":  "Eligibility Criteria for Individual Applicants",
    "7":  "Eligibility Criteria for Non-Individual Applicants",
    "8":  "Eligibility Criteria for Locations Where Land is Not Required",
    "9":  "Direct Award of Dealership",
    "10": "Retail Outlet Management",
    "11": "Spouse as Co-owner",
    "12": "Basic Facilities Required for Operation of RO Dealership",
    "13": "Scheme of Financial Assistance to SC/ST Category Dealership",
    "14": "Disqualification",
    "15": "Affidavit",
    "16": "Non-refundable Application Fee",
    "17": "Non-refundable Fixed Fee / Bidding Amount",
    "18": "Selection Procedure",
    "19": "Procedure for Online Draw of Lots / Opening of Bids",
    "20": "Information Update on Website",
    "21": "Field Verification of Credentials (FVC)",
    "22": "Letter of Intent",
    "23": "Selection Process After Cancellation / Withdrawal of LOI",
    "24": "Grievance Redressal System",
    "25": "Retention of Files / Records",
    "26": "Time Period for Important Activities",
    "27": "Commissioning of Dealership",
    "28": "Security Deposit / Fixed Fee / Bid Amount",
    "29": "Tenure of Dealership",
    "30": "False Information",
    "31": "List of Non-Rectifiable Deficiencies in Applications",
    "32": "Estimated Minimum Working Capital Required",
    "33": "Estimated Minimum Fund Required for Infrastructure Development",
}

ABBREVIATIONS = {
    "RO": "Retail Outlet",
    "OMC": "Oil Marketing Company (IOCL / HPCL / BPCL)",
    "CC": "Corporation Owned (Corporation Owned Dealer Operated)",
    "DC": "Dealer Owned (Dealer Owned Dealer Operated)",
    "SRMP": "State Retail Marketing Plan",
    "MDN": "Multiple Dealership Norm",
    "LOI": "Letter of Intent",
    "FVC": "Field Verification of Credentials",
    "ISD": "Initial Security Deposit",
    "SC/ST": "Scheduled Caste / Scheduled Tribe",
    "OBC": "Other Backward Class",
    "PH": "Physically Handicapped",
    "OSP": "Outstanding Sports Persons",
    "FF": "Freedom Fighters",
    "PACS": "Primary Agricultural Credit Society",
    "NIC": "National Informatics Centre",
    "MSTC": "Metal Scrap Trade Corporation",
    "NH": "National Highway",
    "SH": "State Highway",
    "KLPM": "Kilo Litres Per Month",
    "MS": "Motor Spirit (Petrol)",
    "HSD": "High Speed Diesel",
    "NOC": "No Objection Certificate",
}
