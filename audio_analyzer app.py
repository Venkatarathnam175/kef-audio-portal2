import streamlit as st
import requests
import time
from io import BytesIO
from fpdf import FPDF

# ---------------- CONFIG ----------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby3OQ796QhPyEGRH9hidEjmysOytyGhGPWxrItDt4V6eixJrD6c_k1ujPhVIf3yGdkU/exec"

st.set_page_config(
    page_title="KEF Audio Analysis Portal",
    layout="wide",
)

# --------------- CSS (UI LOOK) ----------------
CUSTOM_CSS = """
<style>
html, body, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg,#F5F5F5,#ffffff);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial;
  color:#0b2540;
}
.block-container { max-width: 1100px; }
.kef-header{
  background:#003874; color:#ffffff; padding:18px 20px;
  border-radius:0 0 16px 16px; display:flex; gap:16px;
  margin:-1rem -1rem 1.2rem -1rem; box-shadow:0 10px 30px rgba(2,6,23,0.25);
}
.kef-logo{ width:130px; object-fit:contain; }
.kef-brand{ font-size:20px; font-weight:700; }
.kef-subtitle{ font-size:13px; opacity:0.95; }
.kef-card{
  background:#ffffff; border-radius:12px; box-shadow:0 10px 30px rgba(2,6,23,0.08);
  padding:16px 18px 14px 18px; margin-bottom:14px;
}
.kef-muted{ color:#506072; font-size:13px; }
.kef-drop-wrapper{
  border:2px dashed #dfe7f2; border-radius:12px;
  padding:18px 16px 10px 16px; background:linear-gradient(180deg,rgba(0,0,0,0.02),transparent);
}
.kef-record{
  border-radius:10px; padding:10px 12px;
  background:linear-gradient(180deg,#ffffff,#fbfdff);
  border:1px solid #eef6ff; margin-bottom:10px; cursor:pointer;
}
.kef-record-title{ font-weight:700; color:#003874; font-size:14px; }
.kef-fields-grid{
  display:grid; grid-template-columns:1fr 1fr; gap:8px;
}
@media (max-width: 900px){ .kef-fields-grid{ grid-template-columns:1fr; } }
.kef-field{
  background:#f8fbff; padding:8px; border-radius:8px; border:1px solid #eef6ff;
}
.kef-field-label{ font-weight:700; color:#1f496b; font-size:11px; }
.kef-field-val{ font-size:12px; color:#123; }
.kef-tiny{ font-size:12px; color:#6d7d89; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------- STATE INIT --------------
if "records" not in st.session_state:
    st.session_state.records = []
if "selected_index" not in st.session_state:
    st.session_state.selected_index = None


# -------------- HELPERS --------------
def fetch_results():
    """GET all analysis rows from Apps Script."""
    try:
        resp = requests.get(APPS_SCRIPT_URL, timeout=20)
        data = resp.json()
        if isinstance(data, list):
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
    return "\n".join([f"{k}: {rec.get(k,'')}" for k in fields_order])


def poll_until_result(file_name: str, placeholder, progress_bar):
    """Wait until n8n writes result into Google Sheet."""
    for attempt in range(1, 61):
        time.sleep(4)
        progress_bar.progress(min(100, attempt * 2))
        placeholder.info(f"Waiting for analysis result… attempt {attempt}")

        rows = fetch_results()
        for idx, r in enumerate(rows):
            if file_name in str(r.get("audioFile", "")):
                st.success("Analysis complete! Record loaded.")
                st.session_state.selected_index = idx
                return True

    st.error("Timed out. Try Refresh later.")
    return False


# ---------------- HEADER ----------------
st.markdown(
    """
<div class="kef-header">
  <img class="kef-logo"
       src="https://raw.githubusercontent.com/Venkatarathnam175/kef-audio-portal2/main/assets/ke_logo.jpeg">
  <div>
    <div class="kef-brand">KEF Audio Analysis Portal</div>
    <div class="kef-subtitle">Kotak Education Foundation — Voice-based learning insights</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------
# MAIN LAYOUT
# ----------------------------------------
left_col, right_col = st.columns([1.7, 1.3])

# ================= LEFT SIDE ======================
with left_col:

    # Upload Section
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("### Upload audio")
    st.markdown(
        '<p class="kef-muted">Upload an audio file. Processing happens via n8n pipeline.</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="kef-drop-wrapper">', unsafe_allow_html=True)
    audio_file = st.file_uploader(
        "Drag & drop audio here",
        type=["mp3", "wav", "m4a"],
        label_visibility="visible"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    status_placeholder = st.empty()
    progress_bar = st.progress(0)

    start_upload = st.button("Start Upload")

    # -------------- FIXED UPLOAD LOGIC --------------
    if start_upload:
        if audio_file is None:
          st.warning("Please select an audio file first.")
        else:
          try:
              status_placeholder.info("Uploading file…")
              progress_bar.progress(10)

            # ---- CORRECT WAY: multipart/form-data ----
            files = {
                "file": (
                    audio_file.name,
                    audio_file,
                    audio_file.type or "application/octet-stream"
                )
             }

            resp = requests.post(
                APPS_SCRIPT_URL,
                files=files,        # multipart/form-data
                timeout=120
            )

            try:
                data = resp.json()
            except Exception:
                st.error("Apps Script returned non-JSON response:")
                st.error(resp.text)
                data = None

        except Exception as e:
            st.error(f"Error uploading file: {e}")
            data = None

        if data and data.get("status") == "success":
            status_placeholder.success("Upload successful. Processing started.")
            progress_bar.progress(40)

            file_name = data.get("fileName") or audio_file.name
            poll_until_result(file_name, status_placeholder, progress_bar)

        else:
            st.error(f"Upload failed: {data}")

    

    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------ RECORD LIST ------------------
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("### Uploaded records")
    st.markdown('<p class="kef-muted">Click any record to view details.</p>', unsafe_allow_html=True)

    if st.button("Refresh records"):
        fetch_results()

    records = st.session_state.records

    for idx, rec in enumerate(reversed(records)):
        real_index = len(records) - 1 - idx
        student = rec.get("studentId") or rec.get("sn") or "Unnamed"
        mentor = rec.get("mentor", "—")
        audio_name = rec.get("audioFile", "—")
        summary = short(rec.get("summary", ""))

        st.markdown(
            f"""
<div class="kef-record">
  <div class="kef-record-title">{student}</div>
  <div class="kef-record-sub">Mentor: {mentor} • File: {audio_name}</div>
  <div class="kef-record-summary">{summary}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Open", key=f"rec_{real_index}"):
            st.session_state.selected_index = real_index

    st.markdown("</div>", unsafe_allow_html=True)

# ================= RIGHT SIDE ======================
with right_col:

    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("#### Quick view")

    selected = st.session_state.selected_index

    if selected is not None and selected < len(st.session_state.records):
        rec = st.session_state.records[selected]

        st.markdown(
            f"**{rec.get('studentId','Unnamed')}**<br>"
            f"<span class='kef-muted'>Mentor: {rec.get('mentor','—')}</span>",
            unsafe_allow_html=True,
        )

        st.markdown("##### Overall Summary")
        st.write(rec.get("summary", "—"))

        # All fields
        st.markdown("##### Detailed Scores")
        html_fields = '<div class="kef-fields-grid">'
        for label, key in [
            ("SN.NO","sn"), ("Mentor","mentor"), ("Student ID","studentId"),
            ("Audio File","audioFile"), ("Voice Modulation","voiceModulation"),
            ("Supportive Environment","supportiveEnvironment"),
            ("Positive Approach","positiveApproach"),
            ("Polite Introduction","politeIntroduction"),
            ("Language Comfort","languageComfort"),
            ("Active Listening","activeListening"),
            ("Positive Language","positiveLanguage"),
            ("Probing Questions","probingQuestions"),
            ("Open-Ended Questions","openQuestions"),
            ("Student Comfort","studentComfort"),
            ("Exploration of Areas","explorationAreas"),
            ("Academic Progress","academicProgress"),
            ("Career Goals","careerGoals"),
            ("Challenges Identified","challengesIdentified"),
            ("Guidance Provided","guidanceProvided"),
            ("Scholarship Discussion","scholarshipDiscussion"),
            ("Next Steps","nextSteps"),
            ("Student Agreed","studentAgreed"),
            ("Mentor Listened","mentorListened"),
            ("Provides Guidance","providesGuidance"),
            ("Overall Impact","overallImpact"),
        ]:
            val = rec.get(key, "—")
            html_fields += f"""
<div class="kef-field">
  <div class="kef-field-label">{label}</div>
  <div class="kef-field-val">{val}</div>
</div>
"""
        html_fields += "</div>"
        st.markdown(html_fields, unsafe_allow_html=True)

    else:
        st.markdown('<p class="kef-muted">Select a record from the left.</p>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # How it works
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown(
        """
<ol class="kef-tiny">
<li>Upload → Stored to Google Drive</li>
<li>n8n analyzes audio → writes to Google Sheet</li>
<li>This portal polls the sheet and displays results</li>
</ol>
""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown(
    "<div class='kef-tiny' style='text-align:center;'>KEF Audio Analysis Portal</div>",
    unsafe_allow_html=True,
)


