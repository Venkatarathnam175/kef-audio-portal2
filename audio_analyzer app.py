import streamlit as st
import requests
import time
import base64

# ---------------- CONFIG ----------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwQL9AzyGVKywaDJhAzPujmU_ynLoCzhm14dWc18v0RBJGdPaF3C1ZlM93l0-GsGRpM/exec"
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
def fetch_results():
    """Fetch only from n8n webhook."""
    try:
        resp = requests.get(N8N_RESULTS_URL + f"?t={time.time()}", timeout=20)
        data = resp.json()
        if isinstance(data, list):
            st.session_state.records = data
        return st.session_state.records
    except:
        return st.session_state.records


def short(text, n=200):
    if not text: return ""
    return text if len(text) <= n else text[:n] + "…"


# ---------------- POLLING FIX (FINAL VERSION) ----------------
def poll_until_result(file_name, placeholder, progress):

    try:
        initial = fetch_results()
    except:
        initial = []

    baseline = initial[-1].copy() if initial else None

    for attempt in range(1, 61):
        time.sleep(4)
        progress.progress(min(100, attempt * 2))
        placeholder.info(f"Waiting for analysis… attempt {attempt}")

        rows = fetch_results()
        if not rows:
            continue

        latest = rows[-1]

        # CASE 1 — first ever run
        if baseline is None:
            if latest.get("summary") not in (None, "", "null"):
                st.success("Analysis complete!")
                placeholder.empty()
                progress.empty()
                st.session_state.selected_index = len(rows) - 1
                return True

        # CASE 2 — row changed
        else:
            if latest != baseline:
                st.success("Analysis complete!")
                placeholder.empty()
                progress.empty()
                st.session_state.selected_index = len(rows) - 1
                return True

    st.error("Timeout. Analysis took too long. Try refreshing manually.")
    placeholder.empty()
    progress.empty()
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
# LEFT SIDE — UPLOAD + RECORDS
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

    if st.button("Start Upload"):
        if not audio_file:
            st.warning("Please select an audio file first.")
        else:
            try:
                status_msg.info("Uploading file…")
                progress.progress(10)

                raw_bytes = audio_file.read()
                b64 = base64.b64encode(raw_bytes).decode("utf-8")

                payload = {
                    "filename": audio_file.name,
                    "mimeType": audio_file.type,
                    "fileData": b64
                }

                r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=120)
                data = r.json()

                if data.get("status") == "success":
                    status_msg.success("Upload success! Waiting for analysis…")
                    poll_until_result(audio_file.name, status_msg, progress)
                else:
                    st.error("Upload failed.")

            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    # RECORDS LIST
    st.markdown('<div class="kef-card">', unsafe_allow_html=True)
    st.markdown("### Uploaded records")

    if st.button("Refresh records"):
        fetch_results()

    for idx, rec in enumerate(st.session_state.records):
        st.markdown(
            f"""
<div class="kef-record">
  <div class="kef-record-title">{rec.get('studentId','Unnamed')}</div>
  <div class="kef-record-sub">Mentor: {rec.get('mentor','—')} • File: {rec.get('audioFile','—')}</div>
  <div class="kef-record-summary">{short(rec.get('summary',""))}</div>
</div>
""",
            unsafe_allow_html=True
        )
        if st.button("Open", key=f"open_{idx}"):
            st.session_state.selected_index = idx

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
        st.write(rec.get("summary","—"))

        fields = [
            ("Voice Modulation","voiceModulation"),
            ("Supportive Environment","supportiveEnvironment"),
            ("Positive Approach","positiveApproach"),
            ("Polite Introduction","politeIntroduction"),
            ("Language Comfort","languageComfort"),
            ("Active Listening","activeListening"),
            ("Positive Language","positiveLanguage"),
            ("Probing Questions","probingQuestions"),
            ("Open Questions","openQuestions"),
            ("Student Comfort","studentComfort"),
            ("Exploration Areas","explorationAreas"),
            ("Academic Progress","academicProgress"),
            ("Career Goals","careerGoals"),
            ("Challenges Identified","challengesIdentified"),
            ("Guidance Provided","guidanceProvided"),
            ("Scholarship Discussion","scholarshipDiscussion"),
            ("Next Steps","nextSteps"),
            ("Overall Impact","overallImpact")
        ]

        html = '<div class="kef-fields-grid">'
        for lbl, key in fields:
            html += f"""
<div class="kef-field">
  <div class="kef-field-label">{lbl}</div>
  <div class="kef-field-val">{rec.get(key,'—')}</div>
</div>
"""
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    else:
        st.markdown('<p class="kef-muted">Select a record from the left.</p>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


st.markdown("<div class='kef-tiny' style='text-align:center;'>KEF Audio Analysis Portal</div>", unsafe_allow_html=True)
