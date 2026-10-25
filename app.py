        with first:
            drug1 = st.text_input("Medication 1")
            severity = st.selectbox("Severity", database.SEVERITIES)
            mechanism = st.text_area("Pharmacological mechanism")
            why_harmful = st.text_area("Why it may be harmful")
            precautions = st.text_area("Precautions / mitigation")
        with second:
            drug2 = st.text_input("Medication 2")
            percentile = st.number_input("Editorial risk percentile", min_value=0, max_value=100, value=50)
            what_happens = st.text_area("What happens biologically")
            symptoms = st.text_area("Symptoms to watch for")
        submitted = st.form_submit_button("Save interaction and rebuild search index")
    if submitted:
        try:
            database.add_interaction(
                {
                    "drug1": drug1,
                    "drug2": drug2,
                    "severity": severity,
                    "percentile": percentile,
                    "mechanism": mechanism,
                    "what_happens": what_happens,
                    "why_harmful": why_harmful,
                    "symptoms": symptoms,
                    "precautions": precautions,
                }
            )
            refreshed = database.get_interactions()
            st.session_state["faiss_engine"] = DrugInteractionSearch(refreshed)
            st.session_state["faiss_signature"] = tuple(
                (row.get("id"), row["drug1"].casefold(), row["drug2"].casefold())
                for row in refreshed
            )
            st.success("Interaction saved; the search index has been rebuilt.")
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
    st.subheader("Current knowledge base")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Medication 1": row["drug1"],
                    "Medication 2": row["drug2"],
                    "Severity": row["severity"],
                    "Risk percentile*": row["percentile"],
                }
                for row in records
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("*Editorial indicator only; not an individualized probability.")


try:
    database.initialize_database()
    database.initialize_session_state()
except RuntimeError as exc:
    logger.exception("Database initialization failed")
    st.error(str(exc))
    st.stop()

if not _render_login():
    st.info("Sign in to access PharmaGuard.")
    st.stop()

with st.sidebar:
    st.write(f"Signed in: **{st.session_state['username']}** ({st.session_state['role']})")
    if st.button("Log out", use_container_width=True):
        auth.logout()
        st.rerun()
    pages = ["Interaction checker", "Analytics"]
    if st.session_state["role"] == "Admin":
        pages.append("Admin dashboard")
    page = st.radio("Navigate", pages)

try:
    interaction_records = database.get_interactions()
except RuntimeError as exc:
    logger.exception("Could not load interactions")
    st.error(str(exc))
    st.stop()

if page == "Interaction checker":
    _render_checker(interaction_records)
elif page == "Analytics":
    _render_analytics(interaction_records)
elif page == "Admin dashboard" and st.session_state["role"] == "Admin":
    _render_admin(interaction_records)

# ---------- Footer ----------
st.markdown("""
<div style="margin-top:28px;padding:18px;text-align:center;
            background:linear-gradient(120deg,#EDE9FE,#E3F0FF,#DDF5EC);
            border:1px solid #E5E0F5;border-radius:16px;">
  <div style="font-weight:800;color:#51477A;">🩺 PharmaGuard</div>
  <div style="font-size:12px;color:#667085;margin-top:4px;">
    Educational information only • Consult a qualified clinician or pharmacist
  </div>
</div>
""", unsafe_allow_html=True)
