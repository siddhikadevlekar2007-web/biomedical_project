"""SQLite persistence and Streamlit session helpers for PharmaGuard."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import streamlit as st

DB_PATH = Path(__file__).resolve().with_name("pharma_guard.db")
SEVERITIES = ("Low", "Moderate", "High", "Critical")

DEFAULT_INTERACTIONS: tuple[dict[str, Any], ...] = (
    {
        "drug1": "Warfarin",
        "drug2": "Ibuprofen",
        "severity": "High",
        "percentile": 84,
        "mechanism": "Ibuprofen can impair platelet function and irritate the stomach lining; warfarin reduces vitamin K-dependent clotting factors.",
        "what_happens": "Several parts of the clotting process can be affected at once, making bleeding more likely, especially in the gastrointestinal tract.",
        "why_harmful": "Bleeding may be difficult to stop and can become serious or life-threatening. The level of risk varies with dose, duration, health conditions, and other medicines.",
        "symptoms": "Unusual bruising, persistent nose or gum bleeding, blood in urine, black or bloody stools, vomiting blood, severe headache, or weakness.",
        "precautions": "Contact the prescribing clinician or pharmacist before combining them. Do not stop prescribed warfarin without medical advice. Seek emergency care for severe bleeding, head injury, or vomiting blood.",
    },
    {
        "drug1": "Nitroglycerin",
        "drug2": "Sildenafil",
        "severity": "Critical",
        "percentile": 98,
        "mechanism": "Both medicines increase nitric-oxide/cGMP signaling, which relaxes blood vessels and can markedly lower blood pressure.",
        "what_happens": "Their blood-pressure-lowering effects can add together and reduce blood flow to vital organs.",
        "why_harmful": "A sudden, profound fall in blood pressure can cause fainting, shock, heart attack, or other life-threatening complications.",
        "symptoms": "Severe dizziness, fainting, unusual weakness, blurred vision, chest pain, or shortness of breath.",
        "precautions": "Do not use sildenafil with nitroglycerin or other nitrate medicines. If both have been taken, call emergency services or a poison center for immediate advice; tell responders exactly what was taken and when.",
    },
    {
        "drug1": "Lisinopril",
        "drug2": "Potassium Chloride",
        "severity": "High",
        "percentile": 76,
        "mechanism": "Lisinopril can reduce aldosterone-mediated potassium excretion; potassium supplements add more potassium to the body.",
        "what_happens": "Potassium may accumulate in the blood (hyperkalemia), particularly with kidney impairment or dehydration.",
        "why_harmful": "Markedly high potassium can disrupt the heart's electrical activity and cause dangerous arrhythmias.",
        "symptoms": "Often there are no early symptoms. Possible warning signs include muscle weakness, tingling, nausea, palpitations, or an irregular heartbeat.",
        "precautions": "Do not start potassium supplements or potassium-based salt substitutes without clinician guidance. Ask whether blood tests are needed. Seek urgent care for fainting, chest pain, or a sustained irregular heartbeat.",
    },
    {
        "drug1": "Sertraline",
        "drug2": "Phenelzine",
        "severity": "Critical",
        "percentile": 96,
        "mechanism": "Sertraline increases serotonin signaling, while phenelzine (an MAOI) prevents breakdown of serotonin and other monoamines.",
        "what_happens": "The combination can cause excessive serotonin activity (serotonin syndrome), a potentially life-threatening reaction.",
        "why_harmful": "Severe serotonin toxicity can rapidly affect temperature regulation, muscles, mental status, and the cardiovascular system.",
        "symptoms": "Agitation, confusion, sweating, fever, diarrhea, tremor, muscle stiffness, shivering, or poor coordination; severe cases may involve seizures or loss of consciousness.",
        "precautions": "This combination generally requires a clinician-directed washout interval and must not be started or stopped without prescriber guidance. Seek emergency care for fever with agitation, stiffness, or confusion.",
    },
    {
        "drug1": "Oxycodone",
        "drug2": "Alprazolam",
        "severity": "Critical",
        "percentile": 93,
        "mechanism": "Opioids suppress respiratory drive and benzodiazepines enhance inhibitory GABA signaling in the central nervous system.",
        "what_happens": "Sedation and suppression of breathing can intensify when these medicines are used together.",
        "why_harmful": "Profound sedation, slowed or stopped breathing, coma, and death are possible, particularly with alcohol or other sedatives.",
        "symptoms": "Extreme sleepiness, inability to wake, slow or shallow breathing, blue or gray lips, confusion, or unresponsiveness.",
        "precautions": "Avoid combining unless a prescriber has specifically assessed and is monitoring the risks. Do not drink alcohol or drive. If breathing is slow or the person cannot be awakened, call emergency services and use naloxone if available.",
    },
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug1 TEXT NOT NULL,
    drug2 TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('Low', 'Moderate', 'High', 'Critical')),
    percentile INTEGER NOT NULL CHECK (percentile BETWEEN 0 AND 100),
    mechanism TEXT NOT NULL,
    what_happens TEXT NOT NULL,
    why_harmful TEXT NOT NULL,
    symptoms TEXT NOT NULL,
    precautions TEXT NOT NULL,
    UNIQUE(drug1 COLLATE NOCASE, drug2 COLLATE NOCASE)
)
"""


def _connect() -> sqlite3.Connection:
    """Open a row-aware database connection."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the interaction table and seed it once with educational examples."""
    try:
        with _connect() as connection:
            connection.execute(_SCHEMA)
            count = connection.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
            if count == 0:
                connection.executemany(
                    """INSERT INTO interactions
                    (drug1, drug2, severity, percentile, mechanism, what_happens,
                     why_harmful, symptoms, precautions)
                    VALUES (:drug1, :drug2, :severity, :percentile, :mechanism,
                            :what_happens, :why_harmful, :symptoms, :precautions)""",
                    DEFAULT_INTERACTIONS,
                )
    except sqlite3.Error as exc:
        raise RuntimeError(f"Could not initialize the PharmaGuard database: {exc}") from exc


def get_interactions() -> list[dict[str, Any]]:
    """Return all known interactions as ordinary dictionaries."""
    try:
        with _connect() as connection:
            rows = connection.execute(
                """SELECT id, drug1, drug2, severity, percentile, mechanism,
                          what_happens, why_harmful, symptoms, precautions
                   FROM interactions ORDER BY drug1 COLLATE NOCASE, drug2 COLLATE NOCASE"""
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise RuntimeError(f"Could not read the PharmaGuard knowledge base: {exc}") from exc


def add_interaction(interaction: dict[str, Any]) -> None:
    """Validate and persist a new drug pair, reporting duplicate pairs explicitly."""
    drug1 = str(interaction.get("drug1", "")).strip()
    drug2 = str(interaction.get("drug2", "")).strip()
    severity = str(interaction.get("severity", "")).strip()
    if not drug1 or not drug2:
        raise ValueError("Both medication names are required.")
    if drug1.casefold() == drug2.casefold():
        raise ValueError("Choose two different medications.")
    if severity not in SEVERITIES:
        raise ValueError("Select a valid severity level.")
    try:
        percentile = int(interaction.get("percentile"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Percentile must be a whole number from 0 to 100.") from exc
    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100.")
    fields = ("mechanism", "what_happens", "why_harmful", "symptoms", "precautions")
    normalized = {field: str(interaction.get(field, "")).strip() for field in fields}
    if any(not value for value in normalized.values()):
        raise ValueError("Complete every clinical information field before saving.")

    try:
        with _connect() as connection:
            connection.execute(
                """INSERT INTO interactions
                (drug1, drug2, severity, percentile, mechanism, what_happens,
                 why_harmful, symptoms, precautions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    drug1,
                    drug2,
                    severity,
                    percentile,
                    normalized["mechanism"],
                    normalized["what_happens"],
                    normalized["why_harmful"],
                    normalized["symptoms"],
                    normalized["precautions"],
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("This medication pair is already in the knowledge base.") from exc
    except sqlite3.Error as exc:
        raise RuntimeError(f"Could not save the interaction: {exc}") from exc


def initialize_session_state() -> None:
    """Set safe defaults for application state that must survive Streamlit reruns."""
    defaults = {
        "authenticated": False,
        "username": None,
        "role": None,
        "selected_medications": [],
        "faiss_engine": None,
        "faiss_signature": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
