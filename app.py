import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="TenderPilot | Διαχείριση Διαγωνισμών",
    page_icon="📁",
    layout="wide"
)

# ---------- Εταιρική εμφάνιση ----------
st.markdown("""
<style>
    .stApp {
        background-color: #f4f6f9;
    }
    h1, h2, h3 {
        color: #17365d;
    }
    .header-box {
        background-color: #17365d;
        padding: 25px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
    }
    .header-box h1 {
        color: white;
        margin-bottom: 5px;
    }
    .header-box p {
        color: #e3ebf5;
    }
    div[data-testid="stMetric"] {
        background: white;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #e1e6ed;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Αρχικοποίηση δεδομένων ----------
if "tenders" not in st.session_state:
    st.session_state.tenders = []

if "documents" not in st.session_state:
    st.session_state.documents = {}

# ---------- Επικεφαλίδα ----------
st.markdown("""
<div class="header-box">
    <h1>📁 TenderPilot</h1>
    <p>Έξυπνη διαχείριση δημόσιων διαγωνισμών και φακέλων προσφορών</p>
</div>
""", unsafe_allow_html=True)

# ---------- Πλοήγηση ----------
menu = st.sidebar.radio(
    "ΚΕΝΤΡΙΚΟ ΜΕΝΟΥ",
    [
        "Πίνακας Ελέγχου",
        "Νέος Διαγωνισμός",
        "Διαγωνισμοί",
        "Δικαιολογητικά",
        "Ημερολόγιο"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("TenderPilot | Πρωτότυπη έκδοση 1.0")

# ---------- Πίνακας ελέγχου ----------
if menu == "Πίνακας Ελέγχου":
    st.title("Πίνακας Ελέγχου")
    st.write("Συνοπτική εικόνα των διαγωνισμών και των εκκρεμοτήτων.")

    tenders = st.session_state.tenders
    today = date.today()

    active = [
        t for t in tenders
        if t["Κατάσταση"] != "Ολοκληρώθηκε"
    ]

    upcoming = [
        t for t in active
        if t["Προθεσμία"] >= today
    ]

    overdue = [
        t for t in active
        if t["Προθεσμία"] < today
    ]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Σύνολο διαγωνισμών", len(tenders))
    c2.metric("Σε εξέλιξη", len(active))
    c3.metric("Μελλοντικές προθεσμίες", len(upcoming))
    c4.metric("Εκπρόθεσμοι", len(overdue))

    st.subheader("Προσεχείς προθεσμίες")

    if tenders:
        rows = sorted(
            tenders,
            key=lambda t: t["Προθεσμία"]
        )

        df = pd.DataFrame([
            {
                "Διαγωνισμός": t["Τίτλος"],
                "Αναθέτουσα Αρχή": t["Αρχή"],
                "Προθεσμία": t["Προθεσμία"].strftime("%d/%m/%Y"),
                "Κατάσταση": t["Κατάσταση"]
            }
            for t in rows
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(
            "Δεν υπάρχουν ακόμη καταχωρισμένοι διαγωνισμοί. "
            "Επίλεξε «Νέος Διαγωνισμός» για να ξεκινήσεις."
        )

# ---------- Νέος διαγωνισμός ----------
elif menu == "Νέος Διαγωνισμός":
    st.title("Καταχώριση Νέου Διαγωνισμού")
    st.write("Συμπλήρωσε τα διαθέσιμα στοιχεία.")

    with st.form("new_tender_form", clear_on_submit=True):
        title = st.text_input("Τίτλος διαγωνισμού *")
        authority = st.text_input("Αναθέτουσα αρχή *")

        col1, col2 = st.columns(2)

        with col1:
            deadline = st.date_input(
                "Καταληκτική ημερομηνία *",
                value=date.today()
            )

            budget = st.number_input(
                "Προϋπολογισμός (€)",
                min_value=0.0,
                value=0.0,
                step=1000.0
            )

        with col2:
            status = st.selectbox(
                "Κατάσταση",
                [
                    "Νέος",
                    "Σε εξέλιξη",
                    "Αναμονή",
                    "Ολοκληρώθηκε"
                ]
            )

            reference = st.text_input(
                "Αριθμός διακήρυξης / αναφοράς"
            )

        notes = st.text_area("Σημειώσεις")

        submitted = st.form_submit_button(
            "Αποθήκευση Διαγωνισμού",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not title.strip() or not authority.strip():
                st.error(
                    "Συμπλήρωσε τον τίτλο και την αναθέτουσα αρχή."
                )
            else:
                tender_id = len(st.session_state.tenders) + 1

                tender = {
                    "ID": tender_id,
                    "Τίτλος": title.strip(),
                    "Αρχή": authority.strip(),
                    "Προθεσμία": deadline,
                    "Προϋπολογισμός": budget,
                    "Κατάσταση": status,
                    "Αναφορά": reference.strip(),
                    "Σημειώσεις": notes.strip()
                }

                st.session_state.tenders.append(tender)

                st.session_state.documents[tender_id] = []

                st.success(
                    f"Ο διαγωνισμός «{title}» καταχωρίστηκε!"
                )

# ---------- Λίστα διαγωνισμών ----------
elif menu == "Διαγωνισμοί":
    st.title("Οι Διαγωνισμοί")

    if not st.session_state.tenders:
        st.info("Δεν έχουν καταχωριστεί διαγωνισμοί ακόμη.")
    else:
        for tender in st.session_state.tenders:
            with st.expander(
                f"#{tender['ID']} | {tender['Τίτλος']}"
            ):
                st.write("**Αναθέτουσα αρχή:**", tender["Αρχή"])
                st.write(
                    "**Προθεσμία:**",
                    tender["Προθεσμία"].strftime("%d/%m/%Y")
                )
                st.write(
                    "**Προϋπολογισμός:**",
                    f"{tender['Προϋπολογισμός']:,.2f} €"
                )
                st.write("**Κατάσταση:**", tender["Κατάσταση"])

                if tender["Αναφορά"]:
                    st.write("**Αριθμός αναφοράς:**", tender["Αναφορά"])

                if tender["Σημειώσεις"]:
                    st.write("**Σημειώσεις:**", tender["Σημειώσεις"])

# ---------- Δικαιολογητικά ----------
elif menu == "Δικαιολογητικά":
    st.title("Έλεγχος Δικαιολογητικών")

    if not st.session_state.tenders:
        st.info("Καταχώρισε πρώτα έναν διαγωνισμό.")
    else:
        tender_options = {
            f"#{t['ID']} | {t['Τίτλος']}": t["ID"]
            for t in st.session_state.tenders
        }

        selected = st.selectbox(
            "Επίλεξε διαγωνισμό",
            list(tender_options.keys())
        )

        tender_id = tender_options[selected]

        st.write("### Κατάλογος εγγράφων")

        with st.form("add_document_form", clear_on_submit=True):
            document_name = st.text_input(
                "Όνομα δικαιολογητικού"
            )

            document_status = st.selectbox(
                "Κατάσταση εγγράφου",
                [
                    "Εκκρεμεί",
                    "Σε προετοιμασία",
                    "Έτοιμο για έλεγχο",
                    "Ελεγμένο"
                ]
            )

            add_document = st.form_submit_button(
                "Προσθήκη Δικαιολογητικού"
            )

            if add_document:
                if document_name.strip():
                    st.session_state.documents[tender_id].append({
                        "Έγγραφο": document_name.strip(),
                        "Κατάσταση": document_status
                    })
                    st.success("Το δικαιολογητικό προστέθηκε.")
                else:
                    st.error("Συμπλήρωσε το όνομα του εγγράφου.")

        docs = st.session_state.documents.get(tender_id, [])

        if docs:
            st.dataframe(
                pd.DataFrame(docs),
                use_container_width=True,
                hide_index=True
            )

            ready = sum(
                1 for d in docs
                if d["Κατάσταση"] == "Ελεγμένο"
            )

            st.progress(ready / len(docs))
            st.caption(
                f"{ready} από {len(docs)} δικαιολογητικά έχουν ελεγχθεί."
            )
        else:
            st.info(
                "Δεν έχουν προστεθεί δικαιολογητικά "
                "για αυτόν τον διαγωνισμό."
            )

# ---------- Ημερολόγιο ----------
elif menu == "Ημερολόγιο":
    st.title("Ημερολόγιο Προθεσμιών")

    if not st.session_state.tenders:
        st.info("Δεν υπάρχουν καταχωρισμένες προθεσμίες.")
    else:
        calendar_rows = []

        for tender in sorted(
            st.session_state.tenders,
            key=lambda t: t["Προθεσμία"]
        ):
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
                "Κατάσταση": tender["Κατάσταση"]
            })

        st.dataframe(
            pd.DataFrame(calendar_rows),
            use_container_width=True,
            hide_index=True
        )

st.markdown("---")
st.caption(
    "TenderPilot | Πρωτότυπο επίδειξης. "
    "Τα δεδομένα της παρούσας έκδοσης δεν αποθηκεύονται μόνιμα."
)
