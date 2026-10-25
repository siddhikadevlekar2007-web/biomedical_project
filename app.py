
# ==========================================
# PHARMAGUARD - MODERN UI DESIGN
# ==========================================

import streamlit as st

st.markdown("""
<style>

/* ---------- MAIN BACKGROUND ---------- */

.stApp {
    background: linear-gradient(
        135deg,
        #f0f4ff 0%,
        #f8faff 50%,
        #e8f5f9 100%
    );
    color: #1e293b;
}

/* ---------- MAIN CONTENT ---------- */

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* ---------- SIDEBAR ---------- */

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #172554 0%,
        #1e3a8a 50%,
        #0f766e 100%
    );
}

section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* Sidebar headings */

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}

/* ---------- MAIN TITLE ---------- */

h1 {
    color: #1e3a8a !important;
    font-weight: 800 !important;
    letter-spacing: -1px;
}

h2 {
    color: #1e40af !important;
    font-weight: 700 !important;
}

h3 {
    color: #0f766e !important;
}

/* ---------- CARDS ---------- */

div[data-testid="stMetric"] {
    background: linear-gradient(
        135deg,
        #ffffff,
        #eff6ff
    );

    border: 1px solid #dbeafe;
    border-radius: 18px;
    padding: 20px;

    box-shadow: 0 6px 18px rgba(30, 58, 138, 0.08);

    transition: all 0.3s ease;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-5px);

    box-shadow: 0 12px 25px rgba(30, 58, 138, 0.15);
}

/* ---------- BUTTONS ---------- */

.stButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(
        135deg,
        #2563eb,
        #0f766e
    );

    color: white !important;
    border: none;
    border-radius: 12px;

    padding: 12px 24px;

    font-weight: 700;

    transition: all 0.3s ease;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: linear-gradient(
        135deg,
        #1d4ed8,
        #115e59
    );

    transform: translateY(-2px);

    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.25);
}

/* ---------- INPUT BOXES ---------- */

.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"],
.stMultiSelect div[data-baseweb="select"] {
    border-radius: 12px !important;
    border-color: #bfdbfe !important;
}

/* ---------- SECTION DIVIDERS ---------- */

hr {
    border-color: #cbd5e1 !important;
}

/* ---------- ALERT BOXES ---------- */

div[data-testid="stAlert"] {
    border-radius: 14px;
    border-left-width: 5px;
}

/* ---------- DATA TABLE ---------- */

div[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;

    border: 1px solid #dbeafe;

    box-shadow: 0 5px 15px rgba(30, 58, 138, 0.08);
}

/* ---------- CHART CONTAINERS ---------- */

div[data-testid="stPlotlyChart"] {
    background: #ffffff;

    border-radius: 18px;

    padding: 10px;

    box-shadow: 0 5px 18px rgba(30, 58, 138, 0.08);
}

/* ---------- ANIMATION ---------- */

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(15px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.block-container {
    animation: fadeIn 0.7s ease-in-out;
}

/* ---------- FOOTER ---------- */

footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)
