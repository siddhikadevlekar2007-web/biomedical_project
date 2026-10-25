import os
import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Medication Interaction Assistant",
    page_icon="💊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. Medical Disclaimer Banner
# -----------------------------------------------------------------------------
st.error(
    "⚠️ **IMPORTANT MEDICAL DISCLAIMER:**\n\n"
    "This application is for **informational and educational purposes only** "
    "and does **not** constitute professional medical advice, diagnosis, or treatment. "
    "Always consult a qualified healthcare provider (such as a physician or pharmacist) "
    "before starting, stopping, or altering any medication schedule or healthcare regimen. "
    "In the event of a medical emergency, immediately contact your local emergency services (e.g., 911)."
)

st.title("💊 Medication Interaction Assistant")
st.markdown(
    "Check for potential drug-to-drug interactions, symptoms to watch for, and recommended precautions."
)

# -----------------------------------------------------------------------------
# 3. Sidebar Setup & API Key Management
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Enter your OpenAI API key here if not set in your environment variables."
    )
    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input

    st.markdown("---")
    st.markdown(
        "### About\n"
        "This tool uses a FAISS vector store containing a curated knowledge base of "
        "known drug interactions and leverages an LLM to explain potential risks in "
        "clear, empathetic language."
    )

# -----------------------------------------------------------------------------
# 4. Curated Knowledge Base & FAISS Vector Store Initialization
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Indexing drug interaction database...")
def build_vector_store():
    """Builds a FAISS vector store populated with sample drug interaction records."""
    sample_knowledge_base = [
        # Warfarin interactions
        "Warfarin + Aspirin: High risk of severe bleeding, stomach ulcers, and internal hemorrhaging. Both medications impair blood clotting via different mechanisms.",
        "Warfarin + Ibuprofen: Increased risk of major gastrointestinal bleeding and kidney impairment. Nonsteroidal anti-inflammatory drugs (NSAIDs) inhibit platelet function.",
        "Warfarin + Acetaminophen (Tylenol): High or chronic doses of acetaminophen can potentiate warfarin's anticoagulant effect, increasing INR levels and bleeding risk.",

        # Statin interactions
        "Atorvastatin + Clarithromycin: Significantly increased risk of severe muscle damage (rhabdomyolysis) and acute renal failure due to CYP3A4 inhibition.",
        "Simvastatin + Amiodarone: High risk of myopathy and rhabdomyolysis. Simvastatin dose should not exceed 10-20 mg daily when co-administered with amiodarone.",
        "Atorvastatin + Grapefruit Extract / Juice: Grapefruit inhibits intestinal CYP3A4 enzyme, leading to elevated statin blood concentrations and increased risk of muscle toxicity.",

        # SSRI / Serotonergic interactions
        "Sertraline + Tramadol: Risk of Serotonin Syndrome, a life-threatening condition characterized by confusion, agitation, high fever, tremor, and seizures. Both drugs elevate brain serotonin levels.",
        "Fluoxetine + Phenelzine (MAOIs): Contraindicated due to severe, potentially fatal Serotonin Syndrome and hypertensive crisis. Requires a 5-week washout period when switching from fluoxetine to an MAOI.",
        "Sertraline + St. John's Wort: Elevated risk of serotonin toxicity and mild-to-moderate Serotonin Syndrome.",

        # Blood Pressure / Cardiac interactions
        "Lisinopril + Spironolactone: High risk of severe hyperkalemia (dangerously high blood potassium levels), which can lead to life-threatening cardiac arrhythmias.",
        "Lisinopril + Ibuprofen: NSAIDs may attenuate the antihypertensive effect of ACE inhibitors and significantly increase the risk of acute renal dysfunction.",
        "Metoprolol + Diltiazem: Risk of severe bradycardia (abnormally slow heart rate), heart block, and worsening heart failure due to additive negative inotropic and chronotropic effects.",

        # Diabetes interactions
        "Metformin + Contrast Media (IV dye): Risk of lactic acidosis. Metformin should be withheld prior to or at the time of radiological studies using intravascular iodinated contrast.",
        "Glipizide + Alcohol: Increased risk of severe hypoglycemia (dangerously low blood sugar) and disulfiram-like reactions (flushing, nausea, rapid heartbeat).",

        # Antibiotic & Antacid interactions
        "Ciprofloxacin + Antacids (Aluminum/Magnesium/Calcium): Chelation occurs, severely reducing ciprofloxacin absorption and clinical effectiveness. Separate administration by at least 2 to 6 hours.",
        "Levofloxacin + Prednisone: Marked increase in the risk of severe tendonitis and tendon rupture, particularly involving the Achilles tendon.",

        # Sedative / Opioid interactions
        "Alprazolam (Xanax) + Oxycodone: Black box warning. Co-prescribing opioids and benzodiazepines results in severe central nervous system depression, profound sedation, respiratory depression, coma, and death."
    ]

    documents = [
        Document(page_content=text, metadata={"id": i})
        for i, text in enumerate(sample_knowledge_base)
    ]
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_documents(documents, embeddings)
    return vector_store

# -----------------------------------------------------------------------------
# 5. Application Logic & User Interface
# -----------------------------------------------------------------------------
med1 = st.text_input("First Medication Name", placeholder="e.g., Warfarin")
med2 = st.text_input("Second Medication Name", placeholder="e.g., Aspirin")
extra_meds = st.text_input("Additional Medications (Optional, comma-separated)", placeholder="e.g., Lisinopril, Ibuprofen")

if st.button("Check Drug Interactions", type="primary"):
    if not os.getenv("OPENAI_API_KEY"):
        st.warning("Please provide your OpenAI API key in the sidebar to proceed.")
    elif not med1.strip() or not med2.strip():
        st.warning("Please enter at least two medication names.")
    else:
        # Assemble medication list
        meds_list = [med1.strip(), med2.strip()]
        if extra_meds.strip():
            meds_list.extend([m.strip() for m in extra_meds.split(",") if m.strip()])

        meds_str = ", ".join(meds_list)

        with st.spinner("Searching knowledge base and analyzing interactions..."):
            try:
                # 1. Initialize Vector Store
                vector_store = build_vector_store()

                # 2. Query FAISS for relevant documents
                query = f"Interactions between {meds_str}"
                retrieved_docs = vector_store.similarity_search(query, k=5)
                retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])

                # 3. Setup LLM and Prompt
                prompt