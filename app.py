"""PharmaGuard: a self-contained medication interaction reference application.

This is an educational prototype, not a medical device or a substitute for a
clinician, pharmacist, or a professionally maintained drug-interaction service.
"""

from __future__ import annotations

import hashlib
import hmac
import itertools
import json
import logging
import os
import re
import secrets
import tempfile
import uuid
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sentence_transformers import SentenceTransformer

LOGGER = logging.getLogger("pharmaguard")
logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="PharmaGuard", page_icon="🩺", layout="wide")

APP_DIR = Path(__file__).resolve().parent
USERS_DB_PATH = APP_DIR / "users_db.json"
DRUG_DB_PATH = APP_DIR / "drug_interactions_db.json"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
PASSWORD_ITERATIONS = 600_000
SEVERITY_LEVELS = ("Low", "Moderate", "High", "Critical")
RECORD_FIELDS = (
    "drug1",
    "drug2",
    "severity",
    "percentile",
    "mechanism",
    "what_happens",
    "why_harmful",
    "symptoms",
    "precautions",
    "empathetic_summary",
    "evidence_source",
)

DISCLAIMER = """
<div style="background:#fff3cd;border:2px solid #b77900;border-left:8px solid #b42318;
border-radius:10px;padding:16px 20px;color:#3f3100;font-weight:650;margin:0 0 18px">
⚠️ MEDICAL DISCLAIMER — PharmaGuard is for educational and clinical-reference
information only. It does not provide diagnosis, treatment, or individualized
medical advice and does not replace a licensed clinician or pharmacist. Do not
start, stop, or change medication based on this app. For severe symptoms, call
your local emergency number immediately.
</div>
"""

# These starter examples are reference material, not a clinician-validated
# formulary. Their sources and patient-specific relevance must be checked before
# clinical use. Percentiles are editorial indicators, not probabilities.
DEFAULT_INTERACTIONS: list[dict[str, Any]] = [
    {
        "drug1": "Warfarin",
        "drug2": "Ibuprofen",
        "severity": "High",
        "percentile": 84,
        "mechanism": "Warfarin reduces vitamin K-dependent clotting factors. Ibuprofen can impair platelet function and injure the gastrointestinal lining.",
        "what_happens": "Anticoagulation and impaired platelet activity can combine with gastrointestinal irritation, increasing the chance of bleeding.",
        "why_harmful": "Bleeding may be difficult to stop and can become serious, especially in the gastrointestinal tract or after an injury.",
        "symptoms": "Unusual bruising, persistent nose or gum bleeding, blood in urine, black or bloody stools, vomiting blood, severe headache, or unusual weakness.",
        "precautions": "Contact the prescriber or pharmacist before combining them. Do not stop prescribed warfarin without medical advice. Seek emergency care for severe bleeding, a head injury, or vomiting blood.",
        "empathetic_summary": "This combination can make bleeding more likely. A clinician or pharmacist can help you choose a safer pain-relief plan for your situation.",
        "evidence_source": "Starter reference; verify against current anticoagulant and NSAID product labeling.",
        "review_status": "reference",
    },
    {
        "drug1": "Nitroglycerin",
        "drug2": "Sildenafil",
        "severity": "Critical",
        "percentile": 98,
        "mechanism": "Nitrates increase nitric-oxide/cGMP signaling and sildenafil inhibits PDE5, which slows cGMP breakdown. The combined vasodilatory effects can be profound.",
        "what_happens": "Blood vessels may relax excessively, causing a sudden and potentially dangerous fall in blood pressure.",
        "why_harmful": "Severe hypotension can reduce blood flow to vital organs and cause fainting, shock, heart attack, or other life-threatening complications.",
        "symptoms": "Severe dizziness, fainting, unusual weakness, blurred vision, chest pain, or shortness of breath.",
        "precautions": "Do not use sildenafil with nitroglycerin or other nitrate medicines. If both have been taken, contact emergency services or a poison center for immediate advice and state what was taken and when.",
        "empathetic_summary": "These medicines can lower blood pressure dangerously when taken together. If you may have taken both, get urgent professional advice now.",
        "evidence_source": "Starter reference; verify against current nitrate and PDE5-inhibitor product labeling.",
        "review_status": "reference",
    },
    {
        "drug1": "Lisinopril",
        "drug2": "Potassium Chloride",
        "severity": "High",
        "percentile": 76,
        "mechanism": "ACE inhibition can reduce aldosterone-mediated potassium excretion; potassium supplements add potassium to the body.",
        "what_happens": "Potassium may build up in the blood, particularly with impaired kidney function, dehydration, or other potassium-raising medicines.",
        "why_harmful": "Marked hyperkalemia can disrupt the heart's electrical activity and cause dangerous arrhythmias.",
        "symptoms": "There may be no early symptoms. Muscle weakness, tingling, nausea, palpitations, or an irregular heartbeat can occur.",
        "precautions": "Do not start potassium supplements or potassium-based salt substitutes without clinician guidance. Ask whether blood tests are needed. Seek urgent care for fainting, chest pain, or a sustained irregular heartbeat.",
        "empathetic_summary": "This combination can raise potassium in some people. Your clinician can decide whether it is appropriate and arrange monitoring if needed.",
        "evidence_source": "Starter reference; verify against current ACE-inhibitor and potassium-product labeling.",
        "review_status": "reference",
    },
    {
        "drug1": "Insulin",
        "drug2": "Propranolol",
        "severity": "High",
        "percentile": 74,
        "mechanism": "Insulin lowers blood glucose. Non-selective beta blockade can mask adrenergic warning signs of hypoglycemia, such as tremor and palpitations, and may affect glucose recovery.",
        "what_happens": "A person may not notice an episode of low blood sugar as early, and recovery can be prolonged in some circumstances.",
        "why_harmful": "Unrecognized or prolonged hypoglycemia can impair judgment, cause seizures, or lead to loss of consciousness.",
        "symptoms": "Sweating may remain noticeable; also watch for confusion, unusual behavior, dizziness, weakness, blurred vision, or loss of coordination.",
        "precautions": "Ask the diabetes prescriber or pharmacist about glucose monitoring and an individualized treatment plan. Do not change insulin or propranolol without medical advice. Treat low glucose according to the patient's established plan.",
        "empathetic_summary": "Propranolol can make some early low-blood-sugar warning signs harder to notice. Your care team can help you plan monitoring that works for you.",
        "evidence_source": "Starter reference; verify current insulin and non-selective beta-blocker labeling.",
        "review_status": "reference",
    },
    {
        "drug1": "Sertraline",
        "drug2": "Phenelzine",
        "severity": "Critical",
        "percentile": 96,
        "mechanism": "Sertraline increases serotonin signaling, while phenelzine inhibits monoamine oxidase and reduces serotonin breakdown.",
        "what_happens": "Excess serotonin activity can cause serotonin toxicity, which may progress quickly.",
        "why_harmful": "Severe toxicity can affect temperature regulation, muscle control, mental status, and cardiovascular function and can be life-threatening.",
        "symptoms": "Agitation, confusion, sweating, fever, diarrhea, tremor, muscle stiffness, shivering, or poor coordination; severe cases may involve seizures or loss of consciousness.",
        "precautions": "This combination generally requires a prescriber-directed washout interval. Do not start, stop, or switch either medicine without medical advice. Seek emergency care for fever with agitation, stiffness, or confusion.",
        "empathetic_summary": "These medicines can interact in a serious way. Please check with the prescriber before taking them together or changing either treatment.",
        "evidence_source": "Starter reference; verify current SSRI and MAOI labeling and washout guidance.",
        "review_status": "reference",
    },
    {
        "drug1": "Oxycodone",
        "drug2": "Alprazolam",
        "severity": "Critical",
        "percentile": 93,
        "mechanism": "Opioids suppress respiratory drive and benzodiazepines enhance inhibitory GABA signaling in the central nervous system.",
        "what_happens": "Sedation and suppression of breathing may intensify when these medicines are used together.",
        "why_harmful": "Profound sedation, slowed or stopped breathing, coma, and death are possible, particularly with alcohol or other sedatives.",
        "symptoms": "Extreme sleepiness, inability to wake, slow or shallow breathing, blue or gray lips, confusion, or unresponsiveness.",
        "precautions": "Avoid combining unless a prescriber has assessed and is monitoring the risks. Do not drink alcohol or drive. If breathing is slow or the person cannot be awakened, call emergency services and use naloxone if available.",
        "empathetic_summary": "Together these medicines may slow breathing too much. If someone is difficult to wake or breathing abnormally, call emergency services now.",
        "evidence_source": "Starter reference; verify current opioid and benzodiazepine boxed warnings and labeling.",
        "review_status": "reference",
    },
    {
        "drug1": "Lithium",
        "drug2": "Ibuprofen",
        "severity": "High",
        "percentile": 80,
        "mechanism": "NSAIDs can reduce renal prostaglandin production and decrease kidney clearance of lithium.",
        "what_happens": "Lithium concentration can rise, with the size of the change varying by kidney function, hydration, dose, and duration.",
        "why_harmful": "High lithium concentrations can cause toxicity and neurologic, gastrointestinal, and cardiac complications.",
        "symptoms": "Worsening tremor, nausea, vomiting, diarrhea, unsteady walking, slurred speech, confusion, or unusual drowsiness.",
        "precautions": "Consult the lithium prescriber or pharmacist before using NSAIDs. Do not change lithium dosing on your own. Seek urgent advice if toxicity symptoms occur.",
        "empathetic_summary": "Some anti-inflammatory pain medicines can raise lithium levels. A pharmacist can help identify a safer option and whether monitoring is needed.",
        "evidence_source": "Starter reference; verify current lithium and NSAID labeling and monitoring recommendations.",
        "review_status": "reference",
    },
    {
        "drug1": "Apixaban",
        "drug2": "Ketoconazole",
        "severity": "High",
        "percentile": 82,
        "mechanism": "Ketoconazole strongly inhibits CYP3A4 and P-glycoprotein, pathways involved in apixaban elimination.",
        "what_happens": "Apixaban exposure may increase, which can increase anticoagulant effect.",
        "why_harmful": "An increased anticoagulant effect may raise the chance of serious or prolonged bleeding.",
        "symptoms": "Unusual bruising, persistent bleeding, blood in urine, black stools, vomiting blood, severe headache, or faintness.",
        "precautions": "Have a prescriber or pharmacist check this combination and current product-specific dose guidance. Seek emergency care for severe bleeding. Do not stop apixaban without advice.",
        "empathetic_summary": "This medicine may slow the body's removal of apixaban. Your care team can check whether an alternative or adjustment is needed.",
        "evidence_source": "Starter reference; verify current apixaban product labeling for strong CYP3A4/P-gp inhibitors.",
        "review_status": "reference",
    },
    {
        "drug1": "Simvastatin",
        "drug2": "Clarithromycin",
        "severity": "High",
        "percentile": 85,
        "mechanism": "Clarithromycin inhibits CYP3A4, an important pathway for simvastatin metabolism.",
        "what_happens": "Simvastatin concentration can rise, increasing exposure of muscle tissue to the statin.",
        "why_harmful": "Increased exposure can cause muscle injury, rarely progressing to rhabdomyolysis and kidney injury.",
        "symptoms": "New muscle pain, tenderness, or weakness, especially with fever, dark urine, or reduced urine output.",
        "precautions": "Contact the prescriber or pharmacist before taking these together; a temporary hold or alternative may be appropriate only under their direction. Seek urgent care for severe muscle symptoms or dark urine.",
        "empathetic_summary": "This antibiotic can raise simvastatin levels and increase the risk of muscle injury. Ask your prescriber or pharmacist what to do during treatment.",
        "evidence_source": "Starter reference; verify current simvastatin and clarithromycin product labeling.",
        "review_status": "reference",
    },
    {
        "drug1": "Digoxin",
        "drug2": "Amiodarone",
        "severity": "High",
        "percentile": 79,
        "mechanism": "Amiodarone can inhibit P-glycoprotein and affect digoxin distribution and clearance.",
        "what_happens": "Digoxin concentrations may increase after amiodarone is started or its dose changes.",
        "why_harmful": "Digoxin toxicity can cause dangerous rhythm disturbances and gastrointestinal or neurologic symptoms.",
        "symptoms": "Nausea, vomiting, poor appetite, confusion, visual changes, unusual fatigue, or palpitations.",
        "precautions": "Prescriber oversight and possible digoxin dose review or blood-level monitoring are important when starting, stopping, or changing amiodarone. Seek urgent care for fainting or serious palpitations.",
        "empathetic_summary": "Amiodarone can increase digoxin exposure. Your care team may adjust treatment or arrange monitoring to reduce risk.",
        "evidence_source": "Starter reference; verify current digoxin and amiodarone labeling and monitoring guidance.",
        "review_status": "reference",
    },
    {
        "drug1": "Clopidogrel",
        "drug2": "Omeprazole",
        "severity": "Moderate",
        "percentile": 58,
        "mechanism": "Omeprazole inhibits CYP2C19, an enzyme involved in conversion of clopidogrel to its active metabolite.",
        "what_happens": "Clopidogrel platelet inhibition may be reduced in some patients; the clinical importance depends on the patient and treatment context.",
        "why_harmful": "Reduced antiplatelet effect may increase the risk of clot-related events in patients who need clopidogrel.",
        "symptoms": "A clot may cause sudden chest pain, shortness of breath, face or limb weakness, speech difficulty, or other abrupt neurologic symptoms.",
        "precautions": "Do not stop either medicine. Ask the prescriber or pharmacist whether an alternative acid-reducing medicine is appropriate. Seek emergency care for possible heart attack or stroke symptoms.",
        "empathetic_summary": "This combination may affect how well clopidogrel works in some people. Your prescriber can weigh the evidence and choose the right stomach-protection plan.",
        "evidence_source": "Starter reference; verify current clopidogrel labeling and applicable clinical guidance.",
        "review_status": "reference",
    },
    {
        "drug1": "Carbamazepine",
        "drug2": "Oral Contraceptive",
        "severity": "High",
        "percentile": 78,
        "mechanism": "Carbamazepine induces drug-metabolizing enzymes that can increase metabolism of hormonal contraceptive components.",
        "what_happens": "Hormone exposure may decrease and contraceptive effectiveness may be reduced.",
        "why_harmful": "Reduced contraceptive effectiveness can result in unintended pregnancy; enzyme induction may also affect other medicines.",
        "symptoms": "There may be no warning symptoms before contraceptive failure. Breakthrough bleeding can occur but does not reliably indicate protection.",
        "precautions": "Discuss reliable non-interacting or additional contraception with a clinician or pharmacist. Do not stop carbamazepine or contraception without professional advice.",
        "empathetic_summary": "Carbamazepine can make some hormonal contraceptives less reliable. A clinician can help you choose a method that fits your needs.",
        "evidence_source": "Starter reference; verify contraceptive product labeling and current contraceptive guidance.",
        "review_status": "reference",
    },
    {
        "drug1": "Linezolid",
        "drug2": "Sertraline",
        "severity": "High",
        "percentile": 83,
        "mechanism": "Linezolid has monoamine-oxidase-inhibiting activity; sertraline increases serotonin signaling.",
        "what_happens": "Serotonin activity may become excessive, although the level of risk depends on clinical context and alternatives.",
        "why_harmful": "Serotonin toxicity can cause agitation, autonomic instability, neuromuscular abnormalities, and severe complications.",
        "symptoms": "Agitation, confusion, sweating, fever, diarrhea, tremor, muscle stiffness, shivering, or poor coordination.",
        "precautions": "Ensure the prescriber knows about all serotonergic medicines before linezolid is used. Medication changes and monitoring must be directed by a clinician. Seek emergency help for fever with agitation or stiffness.",
        "empathetic_summary": "Linezolid may interact with medicines that affect serotonin. The treating clinician should review your medication list and explain monitoring or alternatives.",
        "evidence_source": "Starter reference; verify current linezolid and SSRI labeling and treatment guidance.",
        "review_status": "reference",
    },
    {
        "drug1": "Lisinopril",
        "drug2": "Ibuprofen",
        "severity": "Moderate",
        "percentile": 61,
        "mechanism": "NSAIDs can reduce renal prostaglandin-mediated blood flow and may blunt antihypertensive effects of ACE inhibitors.",
        "what_happens": "Blood pressure control may worsen and kidney function may decline, particularly with dehydration, kidney disease, or a diuretic.",
        "why_harmful": "Acute kidney injury, fluid retention, or loss of blood-pressure control can occur in susceptible patients.",
        "symptoms": "Reduced urine output, swelling, sudden weight gain, unusual fatigue, or higher-than-usual blood pressure; kidney changes may have no early symptoms.",
        "precautions": "Ask a clinician or pharmacist before regular NSAID use, especially if taking a diuretic or having kidney or heart disease. Maintain clinician-recommended hydration and monitoring.",
        "empathetic_summary": "Frequent ibuprofen use can affect kidney function or blood pressure for some people taking lisinopril. Ask about safer pain-relief options.",
        "evidence_source": "Starter reference; verify current ACE-inhibitor and NSAID labeling.",
        "review_status": "reference",
    },
]


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON through a temporary file so interrupted writes do not corrupt it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
    except OSError:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def initialize_json_files() -> None:
    """Create starter JSON stores only when absent; never overwrite malformed data."""
    try:
        if not DRUG_DB_PATH.exists():
            _atomic_write_json(DRUG_DB_PATH, {"interactions": DEFAULT_INTERACTIONS})
        if not USERS_DB_PATH.exists():
            _atomic_write_json(USERS_DB_PATH, {"users": {}})
    except OSError as exc:
        raise RuntimeError(f"Could not initialize local JSON files: {exc}") from exc


def load_interactions() -> list[dict[str, Any]]:
    """Load and validate interaction records from the local JSON knowledge base."""
    try:
        with DRUG_DB_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read {DRUG_DB_PATH.name}: {exc}") from exc
    records = payload.get("interactions") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise RuntimeError("The drug database must contain an 'interactions' list.")
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise RuntimeError(f"Interaction record {index + 1} is not an object.")
        missing = [field for field in RECORD_FIELDS if field not in record]
        if missing:
            raise RuntimeError(
                f"Interaction record {index + 1} is missing: {', '.join(missing)}."
            )
        if record["severity"] not in SEVERITY_LEVELS:
            raise RuntimeError(f"Interaction record {index + 1} has an invalid severity.")
        try:
            percentile = int(record["percentile"])
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Interaction record {index + 1} has an invalid risk percentile."
            ) from exc
        if not 0 <= percentile <= 100:
            raise RuntimeError(f"Interaction record {index + 1} has a percentile outside 0–100.")
    return records


def load_users() -> dict[str, Any]:
    """Read the JSON account store, refusing to replace malformed credential data."""
    try:
        with USERS_DB_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read {USERS_DB_PATH.name}: {exc}") from exc
    users = payload.get("users") if isinstance(payload, dict) else None
    if not isinstance(users, dict):
        raise RuntimeError("The user database must contain a 'users' object.")
    return users


def normalize_email(email: str) -> str:
    """Validate and normalize an account email address."""
    normalized = email.strip().casefold()
    if len(normalized) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def password_digest(password: str, salt: bytes) -> bytes:
    """Derive a salted SHA-256 password hash with an intentionally high work factor."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )


def register_user(email: str, password: str, confirmation: str) -> None:
    """Register a standard user; admin privileges are assigned only by allowlist."""
    normalized = normalize_email(email)
    if len(password) < 12:
        raise ValueError("Use a password with at least 12 characters.")
    if len(password) > 1024:
        raise ValueError("Password must be 1024 characters or fewer.")
    if password != confirmation:
        raise ValueError("The passwords do not match.")
    users = load_users()
    if normalized in users:
        raise ValueError("An account with this email already exists. Please sign in.")
    salt = secrets.token_bytes(16)
    users[normalized] = {
        "salt": salt.hex(),
        "password_hash": password_digest(password, salt).hex(),
        "role": "user",
    }
    try:
        _atomic_write_json(USERS_DB_PATH, {"users": users})
    except OSError as exc:
        raise RuntimeError(f"Could not save the new account: {exc}") from exc


def authenticate_user(email: str, password: str) -> bool:
    """Verify local credentials using constant-time comparison."""
    normalized = normalize_email(email)
    if len(password) > 1024:
        return False
    users = load_users()
    account = users.get(normalized)
    if not isinstance(account, dict):
        return False
    try:
        salt = bytes.fromhex(account["salt"])
        expected = bytes.fromhex(account["password_hash"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Saved account credentials are malformed.") from exc
    if len(salt) != 16 or len(expected) != 32:
        raise RuntimeError("Saved account credentials have an invalid format.")
    if not hmac.compare_digest(password_digest(password, salt), expected):
        return False
    st.session_state["authenticated"] = True
    st.session_state["email"] = normalized
    st.session_state["auth_method"] = "local"
    st.session_state["role"] = "user"
    return True


def configured_admin_emails() -> set[str]:
    """Return admin email allowlist from Streamlit secrets, without trusting signup."""
    if not st.secrets.load_if_toml_exists():
        return set()
    configured = st.secrets.get("pharmaguard", {}).get("admin_emails", [])
    if isinstance(configured, str):
        configured = [configured]
    if not isinstance(configured, (list, tuple, set)):
        raise RuntimeError("pharmaguard.admin_emails must be a list of email addresses.")
    return {str(email).strip().casefold() for email in configured if str(email).strip()}


def interaction_key(first: str, second: str) -> frozenset[str]:
    """Build a case-insensitive, order-independent key for a drug pair."""
    return frozenset((first.strip().casefold(), second.strip().casefold()))


def document_for(record: dict[str, Any]) -> str:
    """Create the searchable clinical-text document for one interaction."""
    fields = (
        "drug1",
        "drug2",
        "severity",
        "mechanism",
        "what_happens",
        "why_harmful",
        "symptoms",
        "precautions",
    )
    return " ".join(str(record.get(field, "")) for field in fields)


@st.cache_resource(show_spinner="Loading the medical language model…")
def load_embedding_model() -> SentenceTransformer:
    """Load the local embedding model once per Streamlit process."""
    return SentenceTransformer(MODEL_NAME, device="cpu")


@st.cache_resource(show_spinner="Building the interaction search index…")
def build_faiss_index(documents: tuple[str, ...]) -> tuple[SentenceTransformer, Any]:
    """Build a normalized sentence-embedding FAISS index from database records."""
    if not documents:
        raise ValueError("The interaction database is empty; the search index cannot be built.")
    model = load_embedding_model()
    vectors = model.encode(
        list(documents),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    vectors = np.ascontiguousarray(vectors, dtype=np.float32)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return model, index


def search_interactions(
    medications: list[str], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Search each selected medication pair and return matching KB records by score."""
    selected: list[str] = []
    seen: set[str] = set()
    for name in medications:
        cleaned = name.strip()
        normalized = cleaned.casefold()
        if cleaned and normalized not in seen:
            seen.add(normalized)
            selected.append(cleaned)
    if len(selected) < 2 or not records:
        return []
    documents = tuple(document_for(record) for record in records)
    model, index = build_faiss_index(documents)
    requested_pairs = list(itertools.combinations(selected, 2))
    queries = [f"interaction between {left} and {right}" for left, right in requested_pairs]
    query_vectors = model.encode(
        queries,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    query_vectors = np.ascontiguousarray(query_vectors, dtype=np.float32)
    scores, indices = index.search(query_vectors, len(records))
    matches: dict[int, float] = {}
    for pair_index, (left, right) in enumerate(requested_pairs):
        requested_key = interaction_key(left, right)
        for score, record_index in zip(scores[pair_index], indices[pair_index]):
            idx = int(record_index)
            if idx < 0:
                continue
            record = records[idx]
            if interaction_key(str(record["drug1"]), str(record["drug2"])) == requested_key:
                matches[idx] = max(matches.get(idx, -1.0), float(score))
                break
    return [
        {**records[idx], "similarity": score}
        for idx, score in sorted(matches.items(), key=lambda item: item[1], reverse=True)
    ]


def add_interaction(record: dict[str, Any], records: list[dict[str, Any]]) -> None:
    """Validate and atomically append an admin-entered reference record."""
    normalized = {field: str(record.get(field, "")).strip() for field in RECORD_FIELDS}
    if not normalized["drug1"] or not normalized["drug2"]:
        raise ValueError("Enter both medication names.")
    if normalized["drug1"].casefold() == normalized["drug2"].casefold():
        raise ValueError("Choose two different medications.")
    if normalized["severity"] not in SEVERITY_LEVELS:
        raise ValueError("Select a valid severity.")
    try:
        percentile = int(record["percentile"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Risk percentile must be a whole number from 0 to 100.") from exc
    if not 0 <= percentile <= 100:
        raise ValueError("Risk percentile must be between 0 and 100.")
    normalized["percentile"] = percentile
    if any(not normalized[field] for field in RECORD_FIELDS if field != "percentile"):
        raise ValueError("Complete all clinical explanation and evidence-source fields.")
    pair = interaction_key(normalized["drug1"], normalized["drug2"])
    if any(interaction_key(row["drug1"], row["drug2"]) == pair for row in records):
        raise ValueError("This medication pair is already in the database.")
    normalized["id"] = uuid.uuid4().hex
    normalized["review_status"] = "admin_attested"
    updated_records = [*records, normalized]
    try:
        _atomic_write_json(DRUG_DB_PATH, {"interactions": updated_records})
    except OSError as exc:
        raise RuntimeError(f"Could not save the interaction: {exc}") from exc
    build_faiss_index.clear()


def render_login() -> bool:
    """Render local sign-in and registration forms."""
    if st.session_state.get("authenticated"):
        return True
    st.session_state["authenticated"] = False
    st.header("Welcome to PharmaGuard")
    st.write("Sign in or create an account to check medication pairs.")
    sign_in, register = st.tabs(["Sign in", "Create account"])
    with sign_in:
        with st.form("sign_in_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            try:
                if authenticate_user(email, password):
                    st.rerun()
                st.error("Email or password is incorrect.")
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
    with register:
        with st.form("register_form"):
            new_email = st.text_input("Email address", key="register_email")
            new_password = st.text_input(
                "Password (at least 12 characters)",
                type="password",
                key="register_password",
            )
            confirmation = st.text_input(
                "Confirm password", type="password", key="register_confirmation"
            )
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            try:
                register_user(new_email, new_password, confirmation)
                st.success("Account created. You can now sign in.")
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
    st.caption("New registrations receive User access. Admin access is provisioned by the site administrator.")
    return False


def render_gauge(record: dict[str, Any]) -> None:
    """Display the editorial relative-risk percentile gauge."""
    value = int(record["percentile"])
    color = {
        "Low": "#20804b",
        "Moderate": "#b77900",
        "High": "#d45b00",
        "Critical": "#b42318",
    }[record["severity"]]
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%"},
            title={"text": "Relative risk percentile*"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 25], "color": "#e8f5e9"},
                    {"range": [25, 50], "color": "#fff8e1"},
                    {"range": [50, 75], "color": "#fff3e0"},
                    {"range": [75, 100], "color": "#ffebee"},
                ],
            },
        )
    )
    figure.update_layout(height=235, margin={"t": 55, "b": 10, "l": 20, "r": 20})
    pair_id = hashlib.sha256(
        f"{record['drug1'].casefold()}|{record['drug2'].casefold()}".encode("utf-8")
    ).hexdigest()[:16]
    st.plotly_chart(figure, use_container_width=True, key=f"risk_gauge_{pair_id}")
    st.caption("*Editorial reference indicator only; not an individual probability or validated clinical score.")


def render_interaction(record: dict[str, Any]) -> None:
    """Present a matched record with its evidence and patient-friendly summary."""
    severity = record["severity"]
    st.markdown(f"### {record['drug1']} + {record['drug2']} — **{severity}**")
    if record.get("review_status") == "admin_attested":
        st.caption(f"Admin-entered source · Evidence source: {record['evidence_source']}")
    else:
        st.warning(
            "Starter reference record — not independently clinician-validated. "
            f"Suggested source to verify: {record['evidence_source']}"
        )
    left, right = st.columns([1, 2])
    with left:
        render_gauge(record)
    with right:
        st.markdown(f"**Biochemical mechanism**  \n{record['mechanism']}")
        st.markdown(f"**What may happen in the body**  \n{record['what_happens']}")
        st.markdown(f"**Why it may be harmful**  \n{record['why_harmful']}")
        st.markdown(f"**Symptoms to monitor**  \n{record['symptoms']}")
    st.info(f"**Immediate precautions:** {record['precautions']}")
    st.success(f"**In plain language:** {record['empathetic_summary']}")
    st.divider()


def render_checker(records: list[dict[str, Any]]) -> None:
    """Collect medication names and run the pairwise FAISS search."""
    st.header("Medication interaction checker")
    medications = sorted(
        {str(row[field]).strip() for row in records for field in ("drug1", "drug2")},
        key=str.casefold,
    )
    chosen = st.multiselect(
        "Select two or more medicines",
        medications,
        help="This prototype checks pairs represented in its local knowledge base.",
    )
    additional = st.text_input(
        "Other medicine names (optional; separate with commas)",
        help="Unlisted names can be entered, but the knowledge base only reports documented pairs.",
    )
    selected: list[str] = []
    seen: set[str] = set()
    for name in chosen + additional.split(","):
        cleaned = name.strip()
        normalized = cleaned.casefold()
        if cleaned and normalized not in seen:
            seen.add(normalized)
            selected.append(cleaned)
    if len(selected) < 2:
        st.info("Choose or enter at least two medication names.")
        return
    st.caption("Checking each unique medication pair against the local reference database…")
    try:
        with st.spinner("Searching interaction references…"):
            matches = search_interactions(selected, records)
    except (OSError, RuntimeError, ValueError) as exc:
        LOGGER.exception("FAISS interaction search failed")
        st.error(f"Interaction search could not be completed: {exc}")
        return
    if not matches:
        st.info("No exact pair match was found in this local knowledge base.")
        st.warning(
            "This does not mean the medicines are safe to combine. The database is limited; "
            "ask a pharmacist or clinician to review your complete medication list."
        )
        return
    st.warning(
        f"{len(matches)} database pair(s) matched. Results are reference information, "
        "not a patient-specific risk assessment."
    )
    for match in matches:
        render_interaction(match)


def render_analytics(records: list[dict[str, Any]]) -> None:
    """Render knowledge-base severity and percentile comparison charts."""
    st.header("Database analytics")
    if not records:
        st.info("The interaction database is empty.")
        return
    frame = pd.DataFrame(records)
    first, second, third = st.columns(3)
    first.metric("Drug pairs", len(frame))
    second.metric(
        "High / Critical pairs",
        int(frame["severity"].isin(["High", "Critical"]).sum()),
    )
    all_drugs = set(frame["drug1"].str.casefold()) | set(frame["drug2"].str.casefold())
    third.metric("Distinct medications", len(all_drugs))
    left, right = st.columns(2)
    severity_counts = (
        frame["severity"]
        .value_counts()
        .reindex(SEVERITY_LEVELS, fill_value=0)
        .rename_axis("Severity")
        .reset_index(name="Pairs")
    )
    palette = {
        "Low": "#20804b",
        "Moderate": "#b77900",
        "High": "#d45b00",
        "Critical": "#b42318",
    }
    with left:
        chart = px.bar(
            severity_counts,
            x="Severity",
            y="Pairs",
            color="Severity",
            color_discrete_map=palette,
            title="Interaction pairs by severity",
        )
        st.plotly_chart(chart, use_container_width=True)
    with right:
        pie = px.pie(
            severity_counts,
            names="Severity",
            values="Pairs",
            color="Severity",
            color_discrete_map=palette,
            title="Severity distribution",
        )
        st.plotly_chart(pie, use_container_width=True)
    comparison = frame.copy()
    comparison["Drug pair"] = comparison["drug1"] + " + " + comparison["drug2"]
    comparison = comparison.sort_values("percentile", ascending=False)
    risk_chart = px.bar(
        comparison,
        x="Drug pair",
        y="percentile",
        color="severity",
        color_discrete_map=palette,
        labels={"percentile": "Editorial relative-risk percentile", "severity": "Severity"},
        title="Editorial risk indicator by pair",
    )
    risk_chart.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(risk_chart, use_container_width=True)
    st.caption("Analytics describe this local reference database, not clinical outcomes or patient-specific risk.")


def render_admin(records: list[dict[str, Any]]) -> None:
    """Render administrator-only interaction entry and database management."""
    st.header("Administrator: manage interaction references")
    st.warning(
        "Add a pair only after checking reliable, current clinical references. "
        "An admin-entered reference is not a substitute for independent clinical governance."
    )
    with st.form("new_interaction_form", clear_on_submit=True):
        left, right = st.columns(2)
        with left:
            drug1 = st.text_input("Medication 1")
            severity = st.selectbox("Severity", SEVERITY_LEVELS)
            mechanism = st.text_area("Biochemical mechanism")
            why_harmful = st.text_area("Why it is harmful")
            precautions = st.text_area("Immediate precautions")
            evidence_source = st.text_input("Evidence source / citation")
        with right:
            drug2 = st.text_input("Medication 2")
            percentile = st.number_input(
                "Editorial relative-risk percentile",
                min_value=0,
                max_value=100,
                value=50,
                step=1,
            )
            what_happens = st.text_area("What happens biologically")
            symptoms = st.text_area("Symptoms to monitor")
            empathetic_summary = st.text_area("Patient-friendly summary")
        submitted = st.form_submit_button("Save pair and rebuild FAISS index")
    if submitted:
        entry = {
            "drug1": drug1,
            "drug2": drug2,
            "severity": severity,
            "percentile": percentile,
            "mechanism": mechanism,
            "what_happens": what_happens,
            "why_harmful": why_harmful,
            "symptoms": symptoms,
            "precautions": precautions,
            "empathetic_summary": empathetic_summary,
            "evidence_source": evidence_source,
        }
        try:
            add_interaction(entry, records)
            updated = load_interactions()
            documents = tuple(document_for(record) for record in updated)
            with st.spinner("Rebuilding the semantic search index…"):
                build_faiss_index(documents)
            st.success("Interaction saved and the FAISS index rebuilt.")
            st.rerun()
        except (OSError, RuntimeError, ValueError) as exc:
            LOGGER.exception("Could not add an interaction record")
            st.error(f"Could not add interaction: {exc}")

    st.subheader("Current interaction records")
    table = pd.DataFrame(
        [
            {
                "Medication 1": row["drug1"],
                "Medication 2": row["drug2"],
                "Severity": row["severity"],
                "Percentile": row["percentile"],
                "Review status": row.get("review_status", "reference"),
                "Evidence source": row["evidence_source"],
            }
            for row in records
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(
        "Database files are local to the running app instance. Streamlit Cloud may not "
        "preserve local-file changes across rebuilds or instances."
    )


st.markdown(
    """
    <style>
    .block-container {max-width: 1440px; padding-top: 1.5rem;}
    [data-testid="stMetric"] {background: #f5f8fc; padding: 12px; border-radius: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(DISCLAIMER, unsafe_allow_html=True)
st.title("🩺 PharmaGuard")
st.caption("Medical information assistant · Medication interaction reference")

try:
    initialize_json_files()
    interaction_records = load_interactions()
    admin_emails = configured_admin_emails()
except (OSError, RuntimeError) as exc:
    LOGGER.exception("PharmaGuard could not initialize")
    st.error(f"PharmaGuard could not start: {exc}")
    st.stop()

if not render_login():
    st.stop()

current_email = str(st.session_state.get("email", "")).strip().casefold()
role = "admin" if current_email in admin_emails else "user"
st.session_state["role"] = role
st.session_state["email"] = current_email
with st.sidebar:
    st.markdown(f"Signed in: **{current_email}**")
    st.markdown(f"Role: **{role.title()}**")
    page_options = ["Interaction checker", "Database analytics"]
    if role == "admin":
        page_options.append("Admin panel")
    selected_page = st.radio("Navigation", page_options)
    if st.button("Sign out", use_container_width=True):
        for key in ("authenticated", "email", "auth_method", "role"):
            st.session_state.pop(key, None)
        st.rerun()

if selected_page == "Interaction checker":
    render_checker(interaction_records)
elif selected_page == "Database analytics":
    render_analytics(interaction_records)
elif selected_page == "Admin panel" and role == "admin":
    render_admin(interaction_records)
