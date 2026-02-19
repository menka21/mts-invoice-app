import streamlit as st
import pdfplumber
import re
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import tempfile

USERNAME = "menka"
PASSWORD = "mts123"

COMPANY = "MTS Ventures Pty Ltd"
BSB = "067101"
ACC = "10786573"


def login():
    st.title("MTS Secure Invoice Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == USERNAME and pwd == PASSWORD:
            st.session_state["auth"] = True
        else:
            st.error("Invalid login")


def clean_date(text):
    m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    return m.group(1) if m else text


def extract_details(file):
    items = []
    store = ""
    date = ""
    inv = file.name.split(".")[0]

    with pdfplumber.open(file) as p:
        for pg in p.pages:
            text = pg.extract_text()

            if text:
                m = re.search(r"Delivery Site\s*:?\s*(.*)", text)
                if m:
                    store = m.group(1).strip()

                d = re.search(r"Invoice Date\s*:?\s*(.*)", text)
                if d:
                    date = clean_date(d.group(1).strip())

            table = pg.extract_table()
            if table:
                for r in table:
                    if r and len(r) >= 5 and str(r[0]).isdigit():
                        try:
                            qty = float(r[0])
                            desc = r[1]
                            cost = float(r[2])
                            items.append([desc, qty, cost])
                        except:
                            pass

    return inv, store, date, items


def get_fumigation(store):
    s = store.lower()

    if "st mary" in s or "st helen" in s or "campbell" in s:
        return 400

    if "king island" in s or "foodworks" in s:
        return 300

    return 0


def get_transport(store):
    s = store.lower()

    if "king island" in s or "foodworks" in s:
        return 200

    if "st mary" in s or "campbell" in s:
        return 565

    return 0


def create_invoice(inv, store, date, items, tr, fu):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    path = tmp.name

    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{COMPANY}</b>", styles["Title"]))
    story.append(Paragraph(f"Invoice No: {inv}", styles["Normal"]))
    story.append(Paragraph(f"Invoice Date: {date}", styles["Normal"]))
    story.append(Paragraph(f"Store: {store}", styles["Normal"]))
    story.append(Spacer(1, 12))

    data = [["Qty", "Description", "Unit Price", "Amount"]]

    subtotal = 0

    for desc, qty, cost in items:
        sell = cost * 1.10
        total = qty * sell
        subtotal += total
        data.append([qty, desc, f"{sell:.2f}", f"{total:.2f}"])

    data.append(["", "", "", ""])
    data.append(["", "Transport", "", f"{tr:.2f}"])
    data.append(["", "Fumigation", "", f"{fu:.2f}"])

    grand = subtotal + tr + fu
    data.append(["", "Grand Total", "", f"{grand:.2f}"])

    table = Table(data, colWidths=[60, 250, 100, 100])
    story.append(table)

    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Bank Details</b>", styles["Heading2"]))
    story.append(Paragraph(f"BSB: {BSB}", styles["Normal"]))
    story.append(Paragraph(f"Account Number: {ACC}", styles["Normal"]))

    doc.build(story)

    return path


if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    login()
else:
    st.title("MTS Invoice Generator")

    uploaded = st.file_uploader("Upload Chase Invoice PDF", type="pdf")

    if uploaded:
        inv, store, date, items = extract_details(uploaded)

        fu = get_fumigation(store)
        tr = get_transport(store)

        st.write("Store:", store)
        st.write("Transport:", tr)
        st.write("Fumigation:", fu)

        if st.button("Generate Invoice"):
            pdf_path = create_invoice(inv, store, date, items, tr, fu)

            with open(pdf_path, "rb") as f:
                st.download_button("Download Invoice", f, file_name=f"Invoice_{inv}.pdf")


