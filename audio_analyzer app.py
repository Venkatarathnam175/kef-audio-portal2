import streamlit as st
import requests
import time
import base64
from io import BytesIO

# ---------------- CONFIG ----------------
# Used ONLY for uploading the audio file (no more sheet fetching)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwQL9AzyGVKywaDJhAzPujmU_ynLoCzhm14dWc18v0RBJGdPaF3C1ZlM93l0-GsGRpM/exec" 

# NEW: n8n endpoint that returns ALL analysis records as JSON list
# 👇 REPLACE THIS with your actual n8n webhook URL
N8N_RESULTS_URL = "https://aiagent2.app.n8n.cloud/webhook/audio-results"

st.set_page_config(
    page_title="KEF Audio Analysis Portal",
    layout="wide",
)

# --------------- CSS ----------------
CUSTOM_CSS = """
<style>
html, body, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg,#F5F5F5,#ffffff);
  font-family: Inter, ui-sans-serif, system-ui;
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
  background:#ffffff; border-radius:12px;
  padding:16px 18px; margin-bottom:14px;
  box-shadow:0 10px 30px rgba(2,6,23,0.08);
}

.kef-muted{ color:#506072; font-size:13px; }

.kef-drop-wrapper{
  border:2px dashed #dfe7f2; border-radius:12px;
  padding:18px 16px; background:rgba(0,0,0,0.02);
}

.kef-record{
  border-radius:10px; padding:10px 12px;
  background:#fff; border:1px solid #eef6ff;
  margin-bottom:10px; cursor:pointer;
}

.kef-record-title{
  font-weight:700; color:#003874; font-size:14px;
}

.kef-fields-grid{
  display:grid; grid-template-columns:1fr 1fr; gap:8px;
}

@media (max-width: 900px){
  .kef-fields-grid{ grid-template-columns:1fr; }
}

.kef-field{
  background:#f8fbff; padding:8px; border-radius:8px;
  border:1px solid #eef6ff;
}

.kef-field-label{ font-weight:700; font-size:11px; color:#1f496b; }
.kef-field-val{ font-size:12px; color:#123; }

.kef-tiny{ font-size:12px; color:#6d7d89; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------- SESSION INIT --------------
if "records" not in st.session_state:
    st.session_state.records = []
if "selected_index" not in st.session_state:
    st.session_state.selected_index = None


# ---------------- HELPERS ----------------
# ⭐ NOW FETCHING FROM n8n INSTEAD OF GOOGLE SHEET ⭐
def fetch_results():
    try:
        # n8n webhook should return a JSON list of row-objects
        resp = requests.get(N8N_RESULTS_URL + f"?t={time.time()}", timeout=20)
        sheet_rows = resp.json()

        if not isinstance(sheet_rows, list) or len(sheet_rows) == 0:
            return st.session_state.records

        latest_row = sheet_rows[-1]   # newest record

        # If first time → load all
        if len(st.session_state.records) == 0:
            st.session_state.records = sheet_rows
            return st.session_state.records

        # Compare with last local row
        last_local = st.session_state.records[-1]

        # If new → append only latest
        if latest_row != last_local:
            st.session_state.records.append(latest_row)
            # auto-focus latest record
            st.session_state.selected_index = len(st.session_state.records) - 1

        return st.session_state.records

    except Exception as e:
        st.error(f"Error fetching results from n8n: {e}")
        return st.session_state.records


def short(text, n=200):
    if not text: return ""
    return text if len(text) <= n else text[:n] + "…"


def poll_until_result(file_name, placeholder, progress):
    for attempt in range(1, 61):
        time.sleep(4)
        progress.progress(min(100, attempt * 2))
        placeholder.info(f"Waiting for analysis… attempt {attempt}")

        rows = fetch_results()
        if not rows:
            continue

        latest = rows[-1]

        # matching new row
        if file_name.lower() in str(latest.get("audioFile", "")).lower():
            st.success("Analysis complete!")
            st.session_state.selected_index = len(rows) - 1
            return True

    st.error("Timeout. Analysis took too long. Try refreshing records manually.")
    return False


# ---------------- HEADER ----------------
st.markdown("""
<div class="kef-header">
  <img class="kef-logo" src="https://raw.githubusercontent.com/Venkatarathnam175/kef-audio-portal2/main/assets/ke_logo.jpeg">
  <div>
    <div class="kef-brand">KEF Audio Analysis Portal</div>
    <div class="kef-subtitle">Kotak Education Foundation — Voice-based insights</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ---------------- MAIN LAYOUT ----------------
left, right = st.columns([1.7, 1.3])

# =========================================================
# LEFT SIDE – UPLOAD + RECORD LIST
# =========================================================
with left:

    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("### Upload audio")
    st.markdown('<p class="kef-muted">Uploads audio and sends to Drive.</p>', unsafe_allow_html=True)

    st.markdown('<div class="kef-drop-wrapper">', unsafe_allow_html=True)
    audio_file = st.file_uploader("Drag & drop audio here", type=["mp3", "wav", "m4a"])
    st.markdown('</div>', unsafe_allow_html=True)

    status_msg = st.empty()
    progress = st.progress(0)

    start_upload = st.button("Start Upload")

    # ---- CORRECTED UPLOAD LOGIC (BASE64) ----
    if start_upload:
        if not audio_file:
            st.warning("Please select an audio file first.")
        else:
            try:
                status_msg.info("Uploading file…")
                progress.progress(10)

                audio_file.seek(0)
                raw_bytes = audio_file.read()
                base64_audio = base64.b64encode(raw_bytes).decode("utf-8")

                payload = {
                    "filename": audio_file.name,
                    "mimeType": audio_file.type,
                    "fileData": base64_audio
                }

                resp = requests.post(
                    APPS_SCRIPT_URL,
                    json=payload,
                    timeout=120
                )

                try:
                    data = resp.json()
                except:
                    st.error("Apps Script returned non-JSON. Check Apps Script logs for errors.")
                    st.error(resp.text)
                    data = None
                
                if data and data.get("status") == "success":
                    status_msg.success("Upload successful! Starting analysis watch.")
                    progress.progress(40)

                    file_name = data.get("fileName") or audio_file.name
                    poll_until_result(file_name, status_msg, progress)

                else:
                    st.error(f"Upload failed: {data}")

            except Exception as e:
                st.error(f"Upload error (requests failed): {e}")
                
    st.markdown('</div>', unsafe_allow_html=True)

    # Records block
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("### Uploaded records")

    if st.button("Refresh records"):
        fetch_results()

    records = st.session_state.records

    for idx, rec in enumerate(reversed(records)):
        real_idx = len(records) - 1 - idx
        st.markdown(
            f"""
<div class="kef-record">
  <div class="kef-record-title">{rec.get('studentId', 'Unnamed')}</div>
  <div class="kef-record-sub">Mentor: {rec.get('mentor','—')} • File: {rec.get('audioFile','—')}</div>
  <div class="kef-record-summary">{short(rec.get('summary',""))}</div>
</div>
""", unsafe_allow_html=True)

        if st.button("Open", key=f"open_{real_idx}", on_click=lambda i=real_idx: st.session_state.__setitem__('selected_index', i)):
            pass

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# RIGHT SIDE — QUICK VIEW
# =========================================================
with right:

    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("#### Quick view")

    sel = st.session_state.selected_index

    if sel is not None and sel < len(st.session_state.records):
        rec = st.session_state.records[sel]

        st.markdown(
            f"**{rec.get('studentId','Unnamed')}**<br>"
            f"<span class='kef-muted'>Mentor: {rec.get('mentor','—')}</span>",
            unsafe_allow_html=True,
        )

        st.markdown("##### Summary")
        st.write(rec.get("summary", "—"))

        st.markdown("##### Details")
        fields = [
            ("SN.NO","sn"), ("Mentor","mentor"), ("Student ID","studentId"),
            ("Audio File","audioFile"), ("Voice Modulation","voiceModulation"),
            ("Supportive Environment","supportiveEnvironment"),
            ("Positive Approach","positiveApproach"), ("Polite Introduction","politeIntroduction"),
            ("Language Comfort","languageComfort"), ("Active Listening","activeListening"),
            ("Positive Language","positiveLanguage"), ("Probing Questions","probingQuestions"),
            ("Open-Ended Questions","openQuestions"), ("Student Comfort","studentComfort"),
            ("Exploration Areas","explorationAreas"), ("Academic Progress","academicProgress"),
            ("Career Goals","careerGoals"), ("Challenges Identified","challengesIdentified"),
            ("Guidance Provided","guidanceProvided"), ("Scholarship Discussion","scholarshipDiscussion"),
            ("Next Steps","nextSteps"), ("Student Agreed","studentAgreed"),
            ("Mentor Listened","mentorListened"), ("Provides Guidance","providesGuidance"),
            ("Overall Impact","overallImpact")
        ]

        html = '<div class="kef-fields-grid">'
        for label, key in fields:
            value = str(rec.get(key, '—')) if rec.get(key) is not None else '—'
            html += f"""
<div class="kef-field">
  <div class="kef-field-label">{label}</div>
  <div class="kef-field-val">{value}</div>
</div>
"""
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p class="kef-muted">Select a record from the left.</p>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("""
<ol class='kef-tiny'>
<li>Upload → Stored to Google Drive</li>
<li>n8n analyzes audio → Saves final JSON</li>
<li>Portal reads from n8n and displays results</li>
</ol>
""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div class='kef-tiny' style='text-align:center;'>KEF Audio Analysis Portal</div>", unsafe_allow_html=True)

