import streamlit as st
import requests
import time
from io import BytesIO
from fpdf import FPDF

# ---------------- CONFIG ----------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyvV_U-i9UmwKQbhh7gW5Aw5KD8dx0BKZR-9QubZ1VBcVS_6_4F0Y8YW3AjR6Vw-kza/exec"

st.set_page_config(
    page_title="KEF Audio Analysis Portal",
    layout="wide",
)

# --------------- CSS (UI LOOK) ----------------
CUSTOM_CSS = """
<style>
/* Page base */
html, body, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg,#F5F5F5,#ffffff);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial;
  color:#0b2540;
}

/* Narrow the central column a bit */
.block-container {
  max-width: 1100px;
}

/* Header */
.kef-header{
  background:#003874;
  color:#ffffff;
  padding:18px 20px;
  border-radius:0 0 16px 16px;
  display:flex;
  align-items:center;
  gap:16px;
  margin:-1rem -1rem 1.2rem -1rem;
  box-shadow:0 10px 30px rgba(2,6,23,0.25);
}
.kef-logo{
  width:130px;
  height:auto;
  border-radius:0;
  object-fit:contain;
}
.kef-brand{
  font-size:20px;
  font-weight:700;
}
.kef-subtitle{
  font-size:13px;
  opacity:0.95;
}

/* Cards */
.kef-card{
  background:#ffffff;
  border-radius:12px;
  box-shadow:0 10px 30px rgba(2,6,23,0.08);
  padding:16px 18px 14px 18px;
  margin-bottom:14px;
}
.kef-card h3, .kef-card h4{
  margin-top:0;
  margin-bottom:6px;
  font-weight:700;
  color:#233f5a;
}
.kef-muted{
  color:#506072;
  font-size:13px;
}

/* Upload drop-like wrapper around Streamlit file_uploader */
.kef-drop-wrapper{
  border:2px dashed #dfe7f2;
  border-radius:12px;
  padding:18px 16px 10px 16px;
  background:linear-gradient(180deg,rgba(0,0,0,0.02),transparent);
}

/* Buttons */
.stButton>button {
  border-radius:10px;
  padding:0.45rem 0.95rem;
  font-weight:700;
  border:0;
}
.stButton>button.kef-primary{
  background:#003874;
  color:#ffffff;
}
.stButton>button.kef-ghost{
  background:transparent;
  color:#003874;
  border:1px solid #e6eefb;
}
.stButton>button.kef-full{
  width:100%;
}

/* Records list cards */
.kef-record{
  border-radius:10px;
  padding:10px 12px;
  background:linear-gradient(180deg,#ffffff,#fbfdff);
  border:1px solid #eef6ff;
  margin-bottom:10px;
  cursor:pointer;
}
.kef-record-title{
  font-weight:700;
  color:#003874;
  font-size:14px;
}
.kef-record-sub{
  font-size:12px;
  color:#506072;
}
.kef-record-summary{
  margin-top:6px;
  font-size:12px;
  color:#6d7d89;
}

/* Fields grid (right panel) */
.kef-fields-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:8px;
}
@media (max-width: 900px){
  .kef-fields-grid{grid-template-columns:1fr;}
}
.kef-field{
  background:#f8fbff;
  padding:8px;
  border-radius:8px;
  border:1px solid #eef6ff;
}
.kef-field-label{
  font-weight:700;
  color:#1f496b;
  font-size:11px;
}
.kef-field-val{
  font-size:12px;
  color:#123;
}

/* Text input */
.stTextInput>div>div>input{
  border-radius:8px;
  border:1px solid #e8f1fb;
  font-size:13px;
}

/* Progress text size */
.kef-tiny{
  font-size:12px;
  color:#6d7d89;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------- STATE INIT --------------
if "records" not in st.session_state:
    st.session_state.records = []
if "filtered_records" not in st.session_state:
    st.session_state.filtered_records = []
if "selected_index" not in st.session_state:
    st.session_state.selected_index = None


# -------------- HELPERS --------------
def fetch_results():
    """GET all analysis rows from Apps Script."""
    try:
        resp = requests.get(APPS_SCRIPT_URL, timeout=20)
        data = resp.json()
        if isinstance(data, list):
            # keep only rows that look valid
            rows = [r for r in data if r and (r.get("studentId") or r.get("audioFile"))]
        else:
            rows = []
        st.session_state.records = rows
        return rows
    except Exception as e:
        st.error(f"Error fetching results: {e}")
        return st.session_state.records


def short(text, n=200):
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"


def build_txt(rec: dict) -> str:
    lines = []
    fields_order = [
        "sn", "mentor", "studentId", "audioFile", "summary",
        "voiceModulation", "supportiveEnvironment", "positiveApproach",
        "politeIntroduction", "languageComfort", "activeListening",
        "positiveLanguage", "probingQuestions", "openQuestions",
        "studentComfort", "explorationAreas", "academicProgress",
        "careerGoals", "challengesIdentified", "guidanceProvided",
        "scholarshipDiscussion", "nextSteps", "studentAgreed",
        "mentorListened", "providesGuidance", "overallImpact",
    ]
    for key in fields_order:
        lines.append(f"{key}: {rec.get(key,'')}")
    return "\n".join(lines)


def build_pdf(rec: dict) -> BytesIO:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 50, 120)
    pdf.cell(0, 10, "KEF Audio Analysis Result", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(0, 0, 0)

    def add_line(label, value):
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, f"{label}:")
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, value or "—")
        pdf.ln(2)

    add_line("Student ID", rec.get("studentId", ""))
    add_line("Mentor", rec.get("mentor", ""))
    add_line("Audio File", rec.get("audioFile", ""))

    pdf.ln(2)
    add_line("Overall Summary", rec.get("summary", ""))

    mapping = [
        ("Voice Modulation", "voiceModulation"),
        ("Supportive Environment", "supportiveEnvironment"),
        ("Positive Approach", "positiveApproach"),
        ("Polite Introduction", "politeIntroduction"),
        ("Language Comfort", "languageComfort"),
        ("Active Listening", "activeListening"),
        ("Positive Language", "positiveLanguage"),
        ("Probing Questions", "probingQuestions"),
        ("Open-Ended Questions", "openQuestions"),
        ("Student Comfort", "studentComfort"),
        ("Exploration of Areas", "explorationAreas"),
        ("Academic Progress", "academicProgress"),
        ("Career Goals", "careerGoals"),
        ("Challenges Identified", "challengesIdentified"),
        ("Guidance Provided", "guidanceProvided"),
        ("Scholarship Discussion", "scholarshipDiscussion"),
        ("Next Steps", "nextSteps"),
        ("Student Agreed", "studentAgreed"),
        ("Mentor Listened", "mentorListened"),
        ("Provides Guidance", "providesGuidance"),
        ("Overall Impact", "overallImpact"),
    ]

    for label, key in mapping:
        add_line(label, str(rec.get(key, "")))

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf


def poll_until_result(file_name: str, placeholder, progress_bar):
    """Poll Apps Script until a record containing file_name appears."""
    for attempt in range(1, 61):  # up to ~4 min (attempts * 4s)
        time.sleep(4)
        progress_bar.progress(min(100, attempt * 2))
        placeholder.info(f"Waiting for analysis result… attempt {attempt}")

        rows = fetch_results()
        match_index = None
        for idx, r in enumerate(rows):
            if file_name and file_name in str(r.get("audioFile", "")):
                match_index = idx
                break

        if match_index is not None:
            st.success("Analysis complete! Record loaded.")
            st.session_state.selected_index = match_index
            return True

    st.error("Timed out: no matching record found yet. Please try Refresh later.")
    return False


# -------------- HEADER --------------
st.markdown(
    """
<div class="kef-header">
  <img class="kef-logo"
       src="https://raw.githubusercontent.com/Venkatarathnam175/kef-audio-portal2/main/assets/ke_logo.jpeg"
       alt="Kotak Education Foundation">
  <div>
    <div class="kef-brand">KEF Audio Analysis Portal</div>
    <div class="kef-subtitle">Kotak Education Foundation — Voice-based learning insights</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# -------------- MAIN LAYOUT --------------
left_col, right_col = st.columns([1.7, 1.3])

# ----- LEFT: Upload + Records -----
with left_col:
    # Upload card
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("### Upload audio")
    st.markdown(
        '<p class="kef-muted">Drag & drop or select an audio file. File is uploaded to your Drive folder and processed by the KEF n8n pipeline. Results will appear below as cards.</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="kef-drop-wrapper">', unsafe_allow_html=True)
    audio_file = st.file_uploader(
        "Drag & drop audio here",
        type=["mp3", "wav", "m4a"],
        label_visibility="visible",
        key="audio_uploader",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    status_placeholder = st.empty()
    progress_bar = st.progress(0, text="")

    col_up1, col_up2 = st.columns([0.4, 0.6])
    with col_up1:
        start_upload = st.button("Start Upload", key="start_upload_btn")
    with col_up2:
        st.markdown(
            '<div class="kef-tiny" style="text-align:right;margin-top:6px;">Secure · KEF</div>',
            unsafe_allow_html=True,
        )

    if start_upload:
        if audio_file is None:
            st.warning("Please select an audio file first.")
        else:
            # POST to Apps Script
            try:
                status_placeholder.info("Uploading file…")
                progress_bar.progress(10)
                files = {
                    "file": (
                        audio_file.name,
                        audio_file,
                        audio_file.type or "application/octet-stream",
                    )
                }
                resp = requests.post(APPS_SCRIPT_URL, files=files, timeout=60)
                data = resp.json()
            except Exception as e:
                st.error(f"Error uploading file: {e}")
                data = None

            if data and data.get("status") == "success":
                status_placeholder.success("Upload successful. Processing started.")
                progress_bar.progress(40)
                file_name = data.get("fileName") or audio_file.name
                # Poll for result
                poll_until_result(file_name, status_placeholder, progress_bar)
            else:
                st.error(f"Upload failed: {data}")

    st.markdown("</div>", unsafe_allow_html=True)  # close upload kef-card

    # Records card
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("### Uploaded records")
    st.markdown(
        '<p class="kef-muted">Latest processed conversations appear here. Tap a card to expand and view all 26 fields.</p>',
        unsafe_allow_html=True,
    )

    # Refresh button for records
    if st.button("Refresh records"):
        fetch_results()

    records = st.session_state.records

    # List of record cards
    for idx, rec in enumerate(reversed(records)):
        real_index = len(records) - 1 - idx  # map back to original
        student = rec.get("studentId") or rec.get("sn") or "Unnamed"
        mentor = rec.get("mentor", "—")
        audio_name = rec.get("audioFile", "—")
        summary = short(rec.get("summary", ""), 180)

        # clickable card using markdown + button
        key_btn = f"rec_btn_{real_index}"
        st.markdown(
            f"""
<div class="kef-record">
  <div class="kef-record-title">{student}</div>
  <div class="kef-record-sub">Mentor: {mentor} · File: {audio_name}</div>
  <div class="kef-record-summary">{summary}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Open", key=key_btn):
            st.session_state.selected_index = real_index
        st.markdown("<div style='margin-top:-12px;'></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # close records kef-card

# ----- RIGHT: Quick view + Filter -----
with right_col:
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("#### Quick view")

    selected_idx = st.session_state.selected_index
    records = st.session_state.records

    if selected_idx is not None and 0 <= selected_idx < len(records):
        rec = records[selected_idx]
        st.markdown(
            f"**{rec.get('studentId', rec.get('sn','Unnamed'))}**  \n"
            f"<span class='kef-muted'>Mentor: {rec.get('mentor','—')} · File: {rec.get('audioFile','—')}</span>",
            unsafe_allow_html=True,
        )

        st.markdown("##### Overall Summary")
        st.write(rec.get("summary", "—"))

        st.markdown("##### Detailed Scores & Notes")
        # grid layout
        field_map = [
            ("SN.NO", "sn"),
            ("Mentor", "mentor"),
            ("Student ID", "studentId"),
            ("Audio File", "audioFile"),
            ("Voice Modulation", "voiceModulation"),
            ("Supportive Environment", "supportiveEnvironment"),
            ("Positive Approach", "positiveApproach"),
            ("Polite Introduction", "politeIntroduction"),
            ("Language Comfort", "languageComfort"),
            ("Active Listening", "activeListening"),
            ("Positive Language", "positiveLanguage"),
            ("Probing Questions", "probingQuestions"),
            ("Open-Ended Questions", "openQuestions"),
            ("Student Comfort", "studentComfort"),
            ("Exploration of Areas", "explorationAreas"),
            ("Academic Progress", "academicProgress"),
            ("Career Goals", "careerGoals"),
            ("Challenges Identified", "challengesIdentified"),
            ("Guidance Provided", "guidanceProvided"),
            ("Scholarship Discussion", "scholarshipDiscussion"),
            ("Next Steps", "nextSteps"),
            ("Student Agreed", "studentAgreed"),
            ("Mentor Listened", "mentorListened"),
            ("Provides Guidance", "providesGuidance"),
            ("Overall Impact", "overallImpact"),
        ]

        # custom HTML grid
        html_fields = '<div class="kef-fields-grid">'
        for label, key in field_map:
            val = rec.get(key, "—")
            html_fields += f"""
<div class="kef-field">
  <div class="kef-field-label">{label}</div>
  <div class="kef-field-val">{val}</div>
</div>
"""
        html_fields += "</div>"
        st.markdown(html_fields, unsafe_allow_html=True)

        # Downloads
        pdf_buffer = build_pdf(rec)
        txt_content = build_txt(rec)

        col_d1, col_d2, col_d3 = st.columns([0.9, 0.9, 1])
        with col_d1:
            st.download_button(
                "Download PDF",
                data=pdf_buffer,
                file_name=f"{rec.get('studentId','result')}.pdf",
                mime="application/pdf",
            )
        with col_d2:
            st.download_button(
                "Download Text",
                data=txt_content,
                file_name=f"{rec.get('studentId','result')}.txt",
                mime="text/plain",
            )
        with col_d3:
            if st.button("Refresh"):
                fetch_results()

    else:
        st.markdown(
            '<p class="kef-muted">Select a card from the left to view details here.</p>',
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="kef-tiny">Filter</span>', unsafe_allow_html=True)
    q = st.text_input("Search student ID or mentor", label_visibility="collapsed")
    if st.button("Apply filter", key="apply_filter_btn"):
        all_rows = fetch_results()
        q_low = q.strip().lower()
        if q_low:
            st.session_state.records = [
                r
                for r in all_rows
                if q_low in str(r.get("studentId", "")).lower()
                or q_low in str(r.get("mentor", "")).lower()
            ]
        else:
            st.session_state.records = all_rows

    st.markdown("</div>", unsafe_allow_html=True)  # close right card

    # Info card
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown('<span class="kef-tiny">How it works</span>', unsafe_allow_html=True)
    st.markdown(
        """
<ol class="kef-tiny">
<li>Upload audio → stored to Drive</li>
<li>n8n pipeline analyzes and writes to Sheet</li>
<li>This portal polls the Sheet and shows cards</li>
</ol>
""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown(
    """
<div class="kef-tiny" style="text-align:center;margin-top:12px;">
  This portal uploads files to the KEF Drive folder and polls the KEF Google Sheet for analysis results.
</div>
""",
    unsafe_allow_html=True,
)
