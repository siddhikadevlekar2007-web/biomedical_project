# PharmaGuard

## Deploy on Streamlit Community Cloud

`app.py` is self-contained. In Streamlit Community Cloud, select the GitHub
repository and set the app file path to `app.py` (or its relative path if it is
in a subdirectory).

Keep `requirements.txt` beside `app.py`. Commit and push both files before
deploying. If the app was already deployed, use **Manage app → Reboot app**
after pushing the changes.

Run locally with:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Configure admin access in Streamlit Cloud **App settings → Secrets**:

```toml
[pharmaguard]
admin_emails = ["admin@example.com"]
```

Register using one of the listed email addresses to access the admin panel.
New accounts not on the allowlist are regular Users. Never grant admin access
to an email address you do not control.

## Local accounts and JSON data

The app creates `users_db.json` and `drug_interactions_db.json` beside `app.py`
when they do not exist. Account passwords are stored as salted PBKDF2-HMAC
SHA-256 hashes; plaintext passwords are not written to disk. The starter
interaction entries are reference examples and are not independently
clinician-validated. Review all records and their sources before any clinical
use. Local files may be ephemeral or instance-specific on hosted platforms;
use persistent, access-controlled storage for deployment.

The first search downloads the `all-MiniLM-L6-v2` model. The model and FAISS
index are cached in the Streamlit process. Saving a new admin entry invalidates
and rebuilds the index. The app uses local JSON files; hosted platforms may
discard changes or run multiple instances with separate files. Use persistent,
access-controlled storage for deployment.

## Deployment notes

Streamlit Cloud deploys from the selected GitHub branch; uploading a ZIP
elsewhere does not install its contents. Commit `app.py` and `requirements.txt`
to the same directory in that branch and set the app's main file path to the
correct relative path.

The starter interactions are reference examples, not independent clinical
validation. This prototype is not HIPAA-compliant and must not be used as a
substitute for a clinician or as a production clinical decision system.
