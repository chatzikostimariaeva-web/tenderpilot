import json
import os
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from pypdf import PdfReader

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

st.set_page_config(
    page_title="TenderPilot | Διαχείριση Διαγωνισμών",
    page_icon="📁",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3, h4, p, label { color: #17365d; }
    .header-box {
        background-color: #17365d; padding: 25px; border-radius: 12px;
        color: white; margin-bottom: 20px;
    }
    .header-box h1 { color: white; margin-bottom: 5px; }
    .header-box p { color: #e3ebf5; }
    div[data-testid="stMetric"] {
        background: white; padding: 18px; border-radius: 10px;
        border: 1px solid #e1e6ed;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricValue"],
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        color: #17365d !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Session state ----------
for key, default in {
    "tenders": [],
    "documents": {},
    "analyses": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("""
<div class="header-box">
    <h1>📁 TenderPilot</h1>
    <p>Έξυπνη διαχείριση δημόσιων διαγωνισμών και φακέλων προσφορών</p>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "ΚΕΝΤΡΙΚΟ ΜΕΝΟΥ",
    ["Πίνακας Ελέγχου", "Νέος Διαγωνισμός", "Ανάλυση Διακήρυξης",
     "Διαγωνισμοί", "Δικαιολογητικά", "Ημερολόγιο"],
)
st.sidebar.markdown("---")
st.sidebar.caption("TenderPilot | Πρωτότυπη έκδοση 1.1")
st.sidebar.info("Τα δεδομένα αυτής της έκδοσης αποθηκεύονται προσωρινά στη συνεδρία. Κατέβασε τα αποτελέσματα για να τα κρατήσεις.")

def get_api_key():
    """Read key from Streamlit Secrets or session-only input."""
    try:
        secret_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        secret_key = ""
    return secret_key or st.session_state.get("openai_api_key_input", "")

def extract_pdf_text(uploaded_file):
    """Extract selectable text from a PDF. Scanned PDFs need OCR first."""
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"\\n[Σελίδα {page_number}]\\n{text}")
    return "\\n".join(pages).strip(), len(reader.pages)

def analyze_tender_with_ai(pdf_text, api_key):
    if OpenAI is None:
        raise RuntimeError("Δεν έχει εγκατασταθεί το πακέτο openai. Έλεγξε το requirements.txt και κάνε redeploy.")
    if not api_key:
        raise RuntimeError("Δεν έχει οριστεί API key. Βάλε το OPENAI_API_KEY στα Streamlit Secrets ή στο πεδίο API key.")
    client = OpenAI(api_key=api_key)
    # Keep request bounded; long documents may need chunking in a later version.
    bounded_text = pdf_text[:90000]
    prompt = f"""
Είσαι βοηθός ελέγχου δημόσιων διαγωνισμών. Ανάλυσε το παρακάτω κείμενο διακήρυξης
και επέστρεψε ΜΟΝΟ έγκυρο JSON με την εξής μορφή:
{{
  "title": "τίτλος διαγωνισμού ή κενό",
  "authority": "αναθέτουσα αρχή ή κενό",
  "deadline": "YYYY-MM-DD ή κενό",
  "budget_eur": αριθμός ή null,
  "tasks": [
    {{
      "task": "συγκεκριμένη ενέργεια",
      "category": "Δικαιολογητικά/Τεχνική προσφορά/Οικονομική προσφορά/Προθεσμίες/Άλλο",
      "deadline": "YYYY-MM-DD ή κενό",
      "source": "άρθρο ή αριθμός σελίδας όπως αναφέρεται στο κείμενο",
      "details": "σύντομη εξήγηση",
      "confidence": "Υψηλή/Μεσαία/Χαμηλή"
    }}
  ],
  "warnings": ["σημεία που χρειάζονται ανθρώπινη επιβεβαίωση"]
}}
Οδηγίες:
- Κατέγραψε μόνο απαιτήσεις που υποστηρίζονται από το κείμενο.
- Μην επινοείς προθεσμίες, δικαιολογητικά, άρθρα ή όρους.
- Αν δεν εντοπίζεται τιμή, βάλε κενό ή null.
- Φτιάξε συγκεκριμένες ενέργειες που μπορεί να ολοκληρώσει ένας εργαζόμενος.
- Συμπερίλαβε απαιτήσεις συμμετοχής, υποβολής, τεχνικής/οικονομικής προσφοράς,
  εγγυήσεις, δηλώσεις, πιστοποιητικά, ισχύ προσφοράς και κρίσιμες προθεσμίες.
- Αν υπάρχει ασάφεια ή το PDF φαίνεται ελλιπές, γράψ' το στα warnings.
- Για κάθε ενέργεια, βάλε παραπομπή στη σελίδα/άρθρο μόνο αν προκύπτει από το κείμενο.
ΚΕΙΜΕΝΟ ΔΙΑΚΗΡΥΞΗΣ:
{bounded_text}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Απάντησε μόνο με έγκυρο JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return json.loads(response.choices[0].message.content)

def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None

# ---------- Dashboard ----------
if menu == "Πίνακας Ελέγχου":
    st.title("Πίνακας Ελέγχου")
    st.write("Συνοπτική εικόνα των διαγωνισμών και των εκκρεμοτήτων.")
    tenders = st.session_state.tenders
    today = date.today()
    active = [t for t in tenders if t["Κατάσταση"] != "Ολοκληρώθηκε"]
    upcoming = [t for t in active if t["Προθεσμία"] >= today]
    overdue = [t for t in active if t["Προθεσμία"] < today]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Σύνολο διαγωνισμών", len(tenders))
    c2.metric("Σε εξέλιξη", len(active))
    c3.metric("Μελλοντικές προθεσμίες", len(upcoming))
    c4.metric("Εκπρόθεσμοι", len(overdue))
    st.subheader("Προσεχείς προθεσμίες")
    if tenders:
        rows = sorted(tenders, key=lambda t: t["Προθεσμία"])
        st.dataframe(pd.DataFrame([{
            "Διαγωνισμός": t["Τίτλος"],
            "Αναθέτουσα Αρχή": t["Αρχή"],
            "Προθεσμία": t["Προθεσμία"].strftime("%d/%m/%Y"),
            "Κατάσταση": t["Κατάσταση"],
        } for t in rows]), use_container_width=True, hide_index=True)
    else:
        st.info("Δεν υπάρχουν ακόμη καταχωρισμένοι διαγωνισμοί. Επίλεξε «Νέος Διαγωνισμός» για να ξεκινήσεις.")

# ---------- New tender ----------
elif menu == "Νέος Διαγωνισμός":
    st.title("Καταχώριση Νέου Διαγωνισμού")
    st.write("Μπορείς να καταχωρίσεις τα στοιχεία χειροκίνητα ή να ανεβάσεις το τεύχος στην ενότητα «Ανάλυση Διακήρυξης».")
    with st.form("new_tender_form", clear_on_submit=True):
        title = st.text_input("Τίτλος διαγωνισμού *")
        authority = st.text_input("Αναθέτουσα αρχή *")
        col1, col2 = st.columns(2)
        with col1:
            deadline = st.date_input("Καταληκτική ημερομηνία *", value=date.today())
            budget = st.number_input("Προϋπολογισμός (€)", min_value=0.0, value=0.0, step=1000.0)
        with col2:
            status = st.selectbox("Κατάσταση", ["Νέος", "Σε εξέλιξη", "Αναμονή", "Ολοκληρώθηκε"])
            reference = st.text_input("Αριθμός διακήρυξης / αναφοράς")
        notes = st.text_area("Σημειώσεις")
        submitted = st.form_submit_button("Αποθήκευση Διαγωνισμού", type="primary", use_container_width=True)
    if submitted:
        if not title.strip() or not authority.strip():
            st.error("Συμπλήρωσε τον τίτλο και την αναθέτουσα αρχή.")
        else:
            tender_id = max([t["ID"] for t in st.session_state.tenders], default=0) + 1
            st.session_state.tenders.append({
                "ID": tender_id, "Τίτλος": title.strip(), "Αρχή": authority.strip(),
                "Προθεσμία": deadline, "Προϋπολογισμός": budget, "Κατάσταση": status,
                "Αναφορά": reference.strip(), "Σημειώσεις": notes.strip(),
            })
            st.session_state.documents[tender_id] = []
            st.success(f"Ο διαγωνισμός «{title}» καταχωρίστηκε!")

# ---------- AI PDF analysis ----------
elif menu == "Ανάλυση Διακήρυξης":
    st.title("Ανάλυση Διακήρυξης PDF")
    st.write("Ανέβασε το τεύχος για να δημιουργηθεί λίστα ενεργειών, δικαιολογητικών και προθεσμιών.")
    st.warning("Η ανάλυση είναι βοηθητική. Έλεγξε κάθε αποτέλεσμα στο πρωτότυπο τεύχος πριν βασιστείς σε αυτό.")
    api_key = get_api_key()
    if not api_key:
        st.text_input("OpenAI API key (δεν αποθηκεύεται μόνιμα)", type="password", key="openai_api_key_input",
                      help="Εναλλακτικά, όρισε OPENAI_API_KEY στα Streamlit Secrets.")
        api_key = get_api_key()
    uploaded_pdf = st.file_uploader("Ανέβασε τη διακήρυξη (PDF)", type=["pdf"], key="tender_pdf_uploader")
    if uploaded_pdf is not None:
        st.caption(f"Αρχείο: {uploaded_pdf.name} · {uploaded_pdf.size / 1024:.0f} KB")
        if st.button("🔎 Ανάλυση τεύχους", type="primary"):
            try:
                with st.spinner("Εξαγωγή κειμένου και ανάλυση..."):
                    pdf_text, page_count = extract_pdf_text(uploaded_pdf)
                    if not pdf_text:
                        st.error("Δεν βρέθηκε αναγνώσιμο κείμενο. Το PDF μπορεί να είναι σαρωμένο ως εικόνα και να χρειάζεται OCR.")
                    else:
                        analysis = analyze_tender_with_ai(pdf_text, api_key)
                        analysis["_filename"] = uploaded_pdf.name
                        analysis["_page_count"] = page_count
                        analysis["_pdf_text_chars"] = len(pdf_text)
                        st.session_state.analyses[uploaded_pdf.name] = analysis
                        st.success(f"Η ανάλυση ολοκληρώθηκε. Ελέγχθηκαν {page_count} σελίδες.")
            except Exception as exc:
                st.error(f"Δεν ολοκληρώθηκε η ανάλυση: {exc}")
                st.caption("Αν το πρόβλημα συνεχίζεται, έλεγξε το API key, το όριο χρήσης του API και το requirements.txt.")
    analysis = st.session_state.analyses.get(uploaded_pdf.name) if uploaded_pdf is not None else None
    if analysis:
        st.subheader("Στοιχεία που εντοπίστηκαν")
        a, b, c = st.columns(3)
        a.write("**Τίτλος:** " + str(analysis.get("title") or "Δεν εντοπίστηκε"))
        b.write("**Αναθέτουσα αρχή:** " + str(analysis.get("authority") or "Δεν εντοπίστηκε"))
        b.write("**Προθεσμία:** " + str(analysis.get("deadline") or "Δεν εντοπίστηκε"))
        c.write("**Προϋπολογισμός:** " + (f"{analysis['budget_eur']:,.2f} €" if isinstance(analysis.get("budget_eur"), (int, float)) else "Δεν εντοπίστηκε"))
        tasks = analysis.get("tasks", [])
        if tasks:
            st.subheader(f"Λίστα ενεργειών ({len(tasks)})")
            df_tasks = pd.DataFrame(tasks)
            rename = {"task": "Ενέργεια", "category": "Κατηγορία", "deadline": "Προθεσμία",
                      "source": "Παραπομπή", "details": "Τι πρέπει να γίνει", "confidence": "Βεβαιότητα"}
            df_tasks = df_tasks.rename(columns=rename)
            st.dataframe(df_tasks, use_container_width=True, hide_index=True)
            csv = df_tasks.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Λήψη λίστας ενεργειών (CSV)", csv,
                               file_name="tenderpilot_energies.csv", mime="text/csv")
        else:
            st.info("Δεν εντοπίστηκαν συγκεκριμένες ενέργειες. Έλεγξε αν το PDF περιέχει αναγνώσιμο κείμενο.")
        warnings = analysis.get("warnings", [])
        if warnings:
            st.subheader("Σημεία που χρειάζονται έλεγχο")
            for warning in warnings:
                st.warning(str(warning))
        st.subheader("Αποθήκευση ως διαγωνισμός")
        default_title = str(analysis.get("title") or uploaded_pdf.name)
        default_authority = str(analysis.get("authority") or "")
        default_deadline = parse_date(analysis.get("deadline")) or date.today()
        with st.form("save_analyzed_tender_form"):
            save_title = st.text_input("Τίτλος", value=default_title)
            save_authority = st.text_input("Αναθέτουσα αρχή", value=default_authority)
            save_deadline = st.date_input("Καταληκτική ημερομηνία (επιβεβαίωσέ την)", value=default_deadline)
            save_budget = st.number_input("Προϋπολογισμός (€)", min_value=0.0,
                                          value=float(analysis["budget_eur"]) if isinstance(analysis.get("budget_eur"), (int, float)) else 0.0,
                                          step=1000.0)
            save_button = st.form_submit_button("Αποθήκευση διαγωνισμού και ενεργειών", type="primary")
        if save_button:
            if not save_title.strip() or not save_authority.strip():
                st.error("Συμπλήρωσε τίτλο και αναθέτουσα αρχή.")
            else:
                tender_id = max([t["ID"] for t in st.session_state.tenders], default=0) + 1
                st.session_state.tenders.append({
                    "ID": tender_id, "Τίτλος": save_title.strip(), "Αρχή": save_authority.strip(),
                    "Προθεσμία": save_deadline, "Προϋπολογισμός": save_budget,
                    "Κατάσταση": "Νέος", "Αναφορά": uploaded_pdf.name,
                    "Σημειώσεις": "Δημιουργήθηκε από ανάλυση PDF.",
                })
                st.session_state.documents[tender_id] = [
                    {"Έγγραφο": str(task.get("task", "")), "Κατάσταση": "Εκκρεμεί",
                     "Κατηγορία": str(task.get("category", "")),
                     "Παραπομπή": str(task.get("source", "")),
                     "Προθεσμία": str(task.get("deadline", "")),
                     "Λεπτομέρειες": str(task.get("details", ""))}
                    for task in tasks
                ]
                st.success("Ο διαγωνισμός και οι ενέργειες αποθηκεύτηκαν στη συνεδρία.")

# ---------- Tender list ----------
elif menu == "Διαγωνισμοί":
    st.title("Οι Διαγωνισμοί")
    if not st.session_state.tenders:
        st.info("Δεν έχουν καταχωριστεί διαγωνισμοί ακόμη.")
    else:
        for tender in st.session_state.tenders:
            with st.expander(f"#{tender['ID']} | {tender['Τίτλος']}"):
                st.write("**Αναθέτουσα αρχή:**", tender["Αρχή"])
                st.write("**Προθεσμία:**", tender["Προθεσμία"].strftime("%d/%m/%Y"))
                st.write("**Προϋπολογισμός:**", f"{tender['Προϋπολογισμός']:,.2f} €")
                st.write("**Κατάσταση:**", tender["Κατάσταση"])
                if tender["Αναφορά"]:
                    st.write("**Αριθμός αναφοράς / αρχείο:**", tender["Αναφορά"])
                if tender["Σημειώσεις"]:
                    st.write("**Σημειώσεις:**", tender["Σημειώσεις"])
                docs = st.session_state.documents.get(tender["ID"], [])
                if docs:
                    st.write("**Ενέργειες / δικαιολογητικά:**")
                    st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)

# ---------- Documents ----------
elif menu == "Δικαιολογητικά":
    st.title("Έλεγχος Δικαιολογητικών και Ενεργειών")
    if not st.session_state.tenders:
        st.info("Καταχώρισε πρώτα έναν διαγωνισμό ή ανάλυσε ένα PDF.")
    else:
        tender_options = {f"#{t['ID']} | {t['Τίτλος']}": t["ID"] for t in st.session_state.tenders}
        selected = st.selectbox("Επίλεξε διαγωνισμό", list(tender_options.keys()))
        tender_id = tender_options[selected]
        docs = st.session_state.documents.setdefault(tender_id, [])
        with st.form("add_document_form", clear_on_submit=True):
            document_name = st.text_input("Όνομα δικαιολογητικού / ενέργειας")
            document_status = st.selectbox("Κατάσταση", ["Εκκρεμεί", "Σε προετοιμασία", "Έτοιμο για έλεγχο", "Ελεγμένο"])
            add_document = st.form_submit_button("Προσθήκη")
        if add_document:
            if document_name.strip():
                docs.append({"Έγγραφο": document_name.strip(), "Κατάσταση": document_status})
                st.success("Η ενέργεια προστέθηκε.")
                st.rerun()
            else:
                st.error("Συμπλήρωσε το όνομα του εγγράφου.")
        if docs:
            st.caption("Μπορείς να αλλάξεις την κατάσταση από τον πίνακα και να εφαρμόσεις τις αλλαγές.")
            edited = st.data_editor(pd.DataFrame(docs), use_container_width=True, hide_index=True,
                                    num_rows="dynamic", key=f"docs_editor_{tender_id}")
            if st.button("Αποθήκευση αλλαγών", key=f"save_docs_{tender_id}"):
                st.session_state.documents[tender_id] = edited.fillna("").to_dict("records")
                st.success("Οι αλλαγές αποθηκεύτηκαν στη συνεδρία.")
            current_docs = st.session_state.documents.get(tender_id, [])
            ready = sum(1 for d in current_docs if d.get("Κατάσταση") == "Ελεγμένο")
            if current_docs:
                st.progress(ready / len(current_docs))
                st.caption(f"{ready} από {len(current_docs)} ενέργειες έχουν ελεγχθεί.")
        else:
            st.info("Δεν έχουν προστεθεί δικαιολογητικά ή ενέργειες για αυτόν τον διαγωνισμό.")

# ---------- Calendar ----------
elif menu == "Ημερολόγιο":
    st.title("Ημερολόγιο Προθεσμιών")
    if not st.session_state.tenders:
        st.info("Δεν υπάρχουν καταχωρισμένες προθεσμίες.")
    else:
        calendar_rows = []
        for tender in sorted(st.session_state.tenders, key=lambda t: t["Προθεσμία"]):
            days_left = (tender["Προθεσμία"] - date.today()).days
            if days_left < 0:
                remaining = f"Εκπρόθεσμος κατά {abs(days_left)} ημέρες"
            elif days_left == 0:
                remaining = "Λήγει σήμερα"
            else:
                remaining = f"{days_left} ημέρες απομένουν"
            calendar_rows.append({
                "Διαγωνισμός": tender["Τίτλος"],
                "Προθεσμία": tender["Προθεσμία"].strftime("%d/%m/%Y"),
                "Χρόνος": remaining,
                "Κατάσταση": tender["Κατάσταση"],
            })
        st.dataframe(pd.DataFrame(calendar_rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("TenderPilot | Πρωτότυπο επίδειξης. Τα δεδομένα χάνονται όταν λήξει η συνεδρία ή γίνει επανεκκίνηση.")
