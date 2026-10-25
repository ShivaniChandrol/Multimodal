"""
Multimodal Construction Intelligence Platform
Skill Wallet Capstone Project 1
Stack: Streamlit + Google Gemini (google-genai) + Pollinations AI. No database required.
"""
import json
import re
from datetime import datetime
from urllib.parse import quote

import streamlit as st
from PIL import Image

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")
MODEL = "gemini-2.5-flash"

CSS = """
<style>
.hero{background:linear-gradient(120deg,#0f2027,#203a43,#2c5364);padding:1.4rem 1.8rem;border-radius:14px;color:#fff;margin-bottom:1rem}
.hero h1{margin:0;font-size:1.9rem}.hero p{margin:.3rem 0 0;opacity:.85}
.card{background:#fff;border:1px solid #e5e9f0;border-radius:12px;padding:1rem 1.2rem;box-shadow:0 1px 4px rgba(0,0,0,.05);color:#1f2937}
.card .lbl{font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;color:#6b7280}
.card .val{font-size:1.7rem;font-weight:700;color:#0f2027}
.pill{display:inline-block;padding:.2rem .7rem;border-radius:999px;font-size:.8rem;font-weight:600;color:#fff}
.p-ok{background:#16a34a}.p-low{background:#65a30d}.p-medium{background:#d97706}
.p-high{background:#ea580c}.p-critical{background:#dc2626}.p-info{background:#2563eb}
.alert{border-left:5px solid #dc2626;background:#fef2f2;color:#7f1d1d;padding:.7rem 1rem;border-radius:6px;margin:.4rem 0}
.alert.warn{border-color:#d97706;background:#fffbeb;color:#78350f}
.alert.ok{border-color:#16a34a;background:#f0fdf4;color:#14532d}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def card(label: str, value: str) -> str:
    return f'<div class="card"><div class="lbl">{label}</div><div class="val">{value}</div></div>'


def pill(text: str, kind: str = "info") -> str:
    return f'<span class="pill p-{kind.lower()}">{text}</span>'


def sev_kind(sev: str) -> str:
    return {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}.get(str(sev).lower(), "info")


def inr(amount: float) -> str:
    """Format INR in Lakhs / Crores."""
    if amount >= 1e7:
        return f"₹{amount / 1e7:,.2f} Cr"
    return f"₹{amount / 1e5:,.2f} Lakhs"


def get_client():
    key = st.session_state.get("api_key", "").strip()
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception as e:  # missing package / bad key format
        st.sidebar.error(f"Gemini client error: {e}")
        return None


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def analyze_image(prompt: str, image: Image.Image, demo: dict) -> tuple[dict, bool]:
    """Returns (result, is_demo). Falls back to demo data on any failure."""
    client = get_client()
    if client is None:
        return demo, True
    try:
        from google.genai import types
        resp = client.models.generate_content(
            model=MODEL,
            contents=[prompt, image],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
        )
        return parse_json(resp.text), False
    except Exception as e:
        st.warning(f"Gemini request failed ({type(e).__name__}: {e}). Showing demonstration output instead.")
        return demo, True


def load_image(file) -> Image.Image | None:
    try:
        img = Image.open(file)
        img.load()
        img = img.convert("RGB")
        img.thumbnail((1600, 1600))
        return img
    except Exception as e:
        st.error(f"Could not read image: {e}")
        return None


def download_report(data: dict, name: str):
    st.download_button("⬇️ Download JSON report", json.dumps(data, indent=2),
                       file_name=f"{name}_{datetime.now():%Y%m%d_%H%M%S}.json", mime="application/json")


# ----------------------------------------------------------------------------
# Prompts & demo data
# ----------------------------------------------------------------------------
PPE_PROMPT = """You are a certified construction safety officer auditing a site photo against OSHA 29 CFR 1926
and relevant Indian codes (IS 456 for concrete works, IS 3696 scaffolding, IS 4130 demolition safety).
Assess PPE compliance for visible workers (hard helmets, high-visibility vests, steel-toe boots, safety harnesses
where working at height) and identify site hazards. Respond ONLY with JSON of this exact schema:
{"safety_score": int 0-100, "overall_status": "Compliant"|"Needs Improvement"|"Non-Compliant",
 "workers_detected": int,
 "ppe_detection": {"helmet": {"detected": bool, "note": str}, "high_vis_vest": {"detected": bool, "note": str},
   "steel_toe_boots": {"detected": bool, "note": str}, "safety_harness": {"detected": bool, "note": str}},
 "hazards": [{"hazard": str, "severity": "Low"|"Medium"|"High"|"Critical", "standard": str, "remedy": str}],
 "summary": str}
If no workers are visible, say so in summary and base the score on site conditions."""

PPE_DEMO = {
    "safety_score": 58, "overall_status": "Needs Improvement", "workers_detected": 3,
    "ppe_detection": {
        "helmet": {"detected": True, "note": "2 of 3 workers wearing helmets"},
        "high_vis_vest": {"detected": True, "note": "Vests worn but one is heavily soiled"},
        "steel_toe_boots": {"detected": False, "note": "Open footwear observed on one worker"},
        "safety_harness": {"detected": False, "note": "No fall arrest at elevated edge"}},
    "hazards": [
        {"hazard": "Unprotected slab edge / no guardrails", "severity": "Critical",
         "standard": "OSHA 1926.501(b)(1)", "remedy": "Install guardrails at 42 in height and mandate harness tie-off."},
        {"hazard": "Exposed rebar without caps", "severity": "High",
         "standard": "OSHA 1926.701(b)", "remedy": "Fit mushroom caps or wooden troughs over protruding rebar."},
        {"hazard": "Cluttered walkways / loose material", "severity": "Medium",
         "standard": "OSHA 1926.25", "remedy": "Daily housekeeping and designated material storage zones."}],
    "summary": "DEMO OUTPUT: Partial PPE compliance with critical fall-protection gaps."}

CRACK_PROMPT = """You are a licensed structural engineer inspecting a concrete/masonry surface photo per IS 456:2000,
IS 15988 (seismic retrofit) and IS 13935. Classify the defect as exactly one of: Hairline, Settlement,
Structural Shear, Thermal Expansion, Spalling. Respond ONLY with JSON:
{"defect_type": str, "confidence": int 0-100, "estimated_crack_width_mm": float, "pattern": str,
 "severity": "Low"|"Medium"|"High"|"Critical", "urgency": "Monitor"|"Within 3 months"|"Within 2 weeks"|"Immediate",
 "root_causes": [str], "recommended_repairs": [{"method": str, "details": str}],
 "monitoring_plan": str, "summary": str}
Repairs may include epoxy injection, structural re-grouting, polymer-modified mortar, carbon fibre wrapping, etc."""

CRACK_DEMO = {
    "defect_type": "Structural Shear", "confidence": 78, "estimated_crack_width_mm": 2.4,
    "pattern": "Diagonal (approx. 45°) stair-step crack near beam-column joint",
    "severity": "High", "urgency": "Within 2 weeks",
    "root_causes": ["Inadequate shear reinforcement / stirrup spacing", "Overloading beyond design capacity",
                    "Differential foundation movement"],
    "recommended_repairs": [
        {"method": "Epoxy injection", "details": "Low-viscosity epoxy under pressure for cracks 0.2-5 mm after cleaning."},
        {"method": "Structural re-grouting", "details": "Non-shrink cementitious grout around joint after removing loose concrete."},
        {"method": "Jacketing", "details": "Consider RC/steel jacketing if a structural audit confirms capacity loss."}],
    "monitoring_plan": "Install tell-tale gauges; log width weekly for 8 weeks.",
    "summary": "DEMO OUTPUT: Diagonal crack suggests shear distress; engage a structural engineer."}

WEATHER = {
    "Normal": {"kind": "ok", "alerts": ["Standard operations permitted.", "Maintain routine toolbox talk and PPE checks.",
                                         "Curing: moist-cure concrete a minimum of 7 days (IS 456 cl. 13.5)."]},
    "High Wind": {"kind": "crit", "alerts": [
        "🏗️ Suspend crane and hoist operations when wind exceeds ~38 km/h (manufacturer limit applies).",
        "Secure scaffolding sheets, formwork panels and loose materials; lower tower crane jibs to weathervane.",
        "Halt work at height and on exposed edges; restrict personnel from drop zones."]},
    "Heavy Rain": {"kind": "crit", "alerts": [
        "⚡ Electrical hazard: de-energise temporary supply, use RCCB-protected panels, keep cables off wet ground.",
        "Stop concrete pours; cover fresh concrete with tarpaulin to prevent washout and surface scaling.",
        "Inspect trenches/excavations for collapse risk; keep dewatering pumps running."]},
    "Extreme Heat": {"kind": "warn", "alerts": [
        "🌡️ Enforce hydration breaks (water, ORS) and shaded rest every hour above 38°C; watch for heat stroke.",
        "Concrete curing protocol: pour early morning/night, use chilled water/retarders, cure with wet hessian and curing compound for 10+ days.",
        "Reschedule heavy manual work outside 12:00-16:00 and inspect hot steel/formwork surfaces."]},
}

SYSTEM_PROMPT = ("You are an expert construction engineering assistant for Indian sites. Give concise, practical answers "
                 "referencing IS codes (IS 456, IS 800, IS 1893, NBC 2016) and OSHA where relevant. Use bullet points for "
                 "procedures, state assumptions, and recommend a licensed engineer for structural decisions.")


def demo_chat_reply(q: str) -> str:
    q = q.lower()
    if any(k in q for k in ("cure", "curing", "concrete")):
        return ("**Concrete curing (demo mode)**\n- Start curing within 24 h; keep moist for ≥7 days (OPC) / 10 days (blended cement or hot weather).\n"
                "- Use wet hessian, ponding or curing compound.\n- Protect from direct sun/wind (IS 456 cl. 13.5).")
    if any(k in q for k in ("steel", "rebar", "reinforc")):
        return ("**Reinforcement (demo mode)**\n- Use Fe500/Fe500D per IS 1786.\n- Maintain cover: 20 mm slabs, 25 mm beams, 40 mm columns (mild exposure).\n- Typical residential RCC uses ~3.5-4.5 kg steel per sq ft.")
    if any(k in q for k in ("safety", "ppe", "helmet")):
        return "**Safety (demo mode)**\n- Mandatory helmet, vest, boots; harness above 1.8 m (OSHA) / 2 m.\n- Daily toolbox talk and permit-to-work for hot work."
    return ("I'm in **demonstration mode** (no API key). Try asking about *curing*, *steel/rebar* or *PPE safety*, "
            "or add a Gemini API key in the sidebar for full AI answers.")


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🏗️ Control Panel")
    default_key = ""
    try:
        default_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    st.session_state["api_key"] = st.text_input("Google Gemini API Key", type="password", value=default_key,
                                                help="Get a free key at aistudio.google.com. Never stored on disk.")
    live = bool(st.session_state["api_key"].strip())
    st.markdown(pill("LIVE · Gemini" if live else "DEMO MODE", "ok" if live else "medium"), unsafe_allow_html=True)
    if not live:
        st.caption("No key supplied: modules return realistic sample outputs.")
    st.divider()
    st.subheader("Architecture")
    st.markdown("""
```
Streamlit UI
 ├─ Safety & PPE ─┐
 ├─ Crack Diag.  ─┼─► Gemini 2.5 Flash
 ├─ Valuation    ─┤   (multimodal, JSON)
 └─ Site Chat    ─┘
Pollinations AI → 3D concept render
Session state only · no database
```""")
    st.subheader("Navigation")
    st.markdown("1. 🦺 Safety & PPE Audit\n2. 🧱 Crack Diagnostics\n3. 💰 Planning & Valuation\n4. 🌦️ Site Assistant")
    st.caption("Skill Wallet Capstone Project 1")

st.markdown('<div class="hero"><h1>🏗️ Multimodal Construction Intelligence Platform</h1>'
            '<p>AI-powered safety audits · structural diagnostics · cost &amp; valuation planning · weather-aware site advisory</p></div>',
            unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🦺 Safety & PPE Audit", "🧱 Crack Diagnostics", "💰 Planning & Valuation", "🌦️ Site Assistant"])

# ----------------------------------------------------------------------------
# Tab 1: Safety & PPE
# ----------------------------------------------------------------------------
with tab1:
    st.subheader("Site Safety & PPE Compliance Audit")
    up = st.file_uploader("Upload a construction site photo", type=["jpg", "jpeg", "png"], key="ppe_up")
    if up:
        img = load_image(up)
        if img:
            c1, c2 = st.columns([1, 1.4])
            c1.image(img, caption="Uploaded site photo", use_container_width=True)
            if c1.button("🔍 Run Safety Audit", type="primary", key="ppe_btn"):
                with st.spinner("Analysing PPE and hazards..."):
                    res, is_demo = analyze_image(PPE_PROMPT, img, PPE_DEMO)
                st.session_state["ppe_res"] = (res, is_demo)
    if "ppe_res" in st.session_state:
        res, is_demo = st.session_state["ppe_res"]
        try:
            score = int(res.get("safety_score", 0))
            status = res.get("overall_status", "Unknown")
            skind = "ok" if score >= 80 else "medium" if score >= 60 else "critical"
            if is_demo:
                st.info("Demonstration output shown.")
            m = st.columns(4)
            m[0].markdown(card("Safety Score", f"{score}/100"), unsafe_allow_html=True)
            m[1].markdown(card("Status", pill(status, skind)), unsafe_allow_html=True)
            m[2].markdown(card("Workers Detected", str(res.get("workers_detected", "–"))), unsafe_allow_html=True)
            m[3].markdown(card("Hazards Found", str(len(res.get("hazards", [])))), unsafe_allow_html=True)
            st.progress(max(0, min(score, 100)) / 100)
            st.markdown("#### PPE Checklist")
            labels = {"helmet": "⛑️ Helmet", "high_vis_vest": "🦺 High-Vis Vest",
                      "steel_toe_boots": "🥾 Steel-Toe Boots", "safety_harness": "🪢 Safety Harness"}
            cols = st.columns(4)
            for col, (k, lab) in zip(cols, labels.items()):
                item = res.get("ppe_detection", {}).get(k, {})
                ok = item.get("detected", False)
                col.markdown(f"**{lab}**<br>{pill('Detected' if ok else 'Missing', 'ok' if ok else 'critical')}<br>"
                             f"<small>{item.get('note', '')}</small>", unsafe_allow_html=True)
            st.markdown("#### Identified Hazards")
            for h in res.get("hazards", []):
                st.markdown(f"{pill(h.get('severity', 'Info'), sev_kind(h.get('severity')))} **{h.get('hazard', '')}** "
                            f"<small>({h.get('standard', '')})</small><br>✅ {h.get('remedy', '')}", unsafe_allow_html=True)
                st.write("")
            st.caption(res.get("summary", ""))
            download_report(res, "safety_audit")
        except Exception as e:
            st.error(f"Unexpected report format: {e}")
            st.json(res)

# ----------------------------------------------------------------------------
# Tab 2: Crack diagnostics
# ----------------------------------------------------------------------------
with tab2:
    st.subheader("Crack Diagnostics & Structural Integrity")
    up2 = st.file_uploader("Upload concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crack_up")
    if up2:
        img2 = load_image(up2)
        if img2:
            c1, c2 = st.columns([1, 1.4])
            c1.image(img2, caption="Surface under inspection", use_container_width=True)
            if c1.button("🧪 Diagnose Defect", type="primary", key="crack_btn"):
                with st.spinner("Running structural diagnostics..."):
                    res, is_demo = analyze_image(CRACK_PROMPT, img2, CRACK_DEMO)
                st.session_state["crack_res"] = (res, is_demo)
    if "crack_res" in st.session_state:
        res, is_demo = st.session_state["crack_res"]
        try:
            if is_demo:
                st.info("Demonstration output shown.")
            m = st.columns(4)
            m[0].markdown(card("Defect Type", res.get("defect_type", "–")), unsafe_allow_html=True)
            m[1].markdown(card("Crack Width", f"{res.get('estimated_crack_width_mm', '–')} mm"), unsafe_allow_html=True)
            m[2].markdown(card("Severity", pill(res.get("severity", "–"), sev_kind(res.get("severity")))), unsafe_allow_html=True)
            m[3].markdown(card("Urgency", res.get("urgency", "–")), unsafe_allow_html=True)
            st.markdown(f"**Pattern:** {res.get('pattern', '–')}  |  **Confidence:** {res.get('confidence', '–')}%")
            a, b = st.columns(2)
            with a:
                st.markdown("#### Probable Root Causes")
                for rc in res.get("root_causes", []):
                    st.markdown(f"- {rc}")
            with b:
                st.markdown("#### Recommended Engineering Repairs")
                for r in res.get("recommended_repairs", []):
                    st.markdown(f"- **{r.get('method', '')}**: {r.get('details', '')}")
            st.markdown(f"**Monitoring plan:** {res.get('monitoring_plan', '–')}")
            st.caption(res.get("summary", ""))
            download_report(res, "crack_diagnosis")
        except Exception as e:
            st.error(f"Unexpected report format: {e}")
            st.json(res)

# ----------------------------------------------------------------------------
# Tab 3: Planning & valuation
# ----------------------------------------------------------------------------
# cost per sq ft (INR) by structure type; (steel kg/sqft, cement bags/sqft)
STRUCT = {"RCC Framed Residential": (2000, 4.0, 0.45), "Load-Bearing Masonry": (1600, 2.0, 0.40),
          "Commercial Complex": (2600, 5.0, 0.50), "Steel / PEB Industrial": (2200, 7.0, 0.20),
          "Luxury Villa": (3200, 4.5, 0.48)}
TIER = {"Tier 1 (Mumbai, Delhi, Bengaluru)": (1.30, 9500), "Tier 2 (Indore, Pune, Jaipur)": (1.00, 5500),
        "Tier 3 (Smaller cities & towns)": (0.80, 3200)}
MILESTONES = [(0, "Site prep"), (10, "Foundation"), (30, "Plinth"), (50, "Superstructure"), (70, "Masonry & MEP"),
              (85, "Finishing"), (100, "Handover")]

with tab3:
    st.subheader("Planning & Real Estate Valuation")
    c1, c2 = st.columns(2)
    stype = c1.selectbox("Structure type", list(STRUCT))
    tier = c2.selectbox("Location tier", list(TIER))
    sqft = c1.number_input("Built-up area (sq ft)", 200, 500000, 1500, step=100)
    pct = c2.slider("Completion (%)", 0, 100, 40)

    base, steel_kg, cement_bag = STRUCT[stype]
    t_mult, mkt_rate = TIER[tier]
    budget = sqft * base * t_mult
    capex = budget * pct / 100
    full_value = sqft * mkt_rate * (1.35 if stype == "Luxury Villa" else 1.15 if stype == "Commercial Complex" else 1.0)
    land_share = 0.30  # land assumed to be 30% of finished asset value
    asset = full_value * (land_share + (1 - land_share) * pct / 100)

    m = st.columns(4)
    m[0].markdown(card("Total Project Budget", inr(budget)), unsafe_allow_html=True)
    m[1].markdown(card("CapEx Incurred", inr(capex)), unsafe_allow_html=True)
    m[2].markdown(card("Current Asset Value", inr(asset)), unsafe_allow_html=True)
    m[3].markdown(card("Value at Completion", inr(full_value)), unsafe_allow_html=True)
    st.write("")
    m = st.columns(3)
    m[0].markdown(card("Steel Required", f"{sqft * steel_kg / 1000:,.1f} tonnes"), unsafe_allow_html=True)
    m[1].markdown(card("Cement Required", f"{sqft * cement_bag:,.0f} bags"), unsafe_allow_html=True)
    m[2].markdown(card("Remaining Spend", inr(budget - capex)), unsafe_allow_html=True)

    st.markdown("#### Milestone Progress")
    st.progress(pct / 100)
    current = max(((p, n) for p, n in MILESTONES if p <= pct), key=lambda x: x[0])
    st.markdown(" → ".join(f"**{n}**" if n == current[1] else (f"~~{n}~~" if p < pct else n) for p, n in MILESTONES))
    st.caption("Estimates are indicative planning figures (rates are editable constants in the source), not a formal valuation or BOQ.")

    st.markdown("#### 🎨 Conceptual 3D Architectural Rendering (Pollinations AI)")
    style = st.text_input("Style / extra details", "modern minimalist, glass facade, landscaped garden, golden hour")
    render_prompt = (f"photorealistic 3D architectural rendering of a {stype.lower()} building, about {sqft} sq ft, "
                     f"located in an Indian city, {style}, ultra detailed, 8k")
    st.code(render_prompt, language=None)
    if st.button("Generate concept render", key="render_btn"):
        url = f"https://image.pollinations.ai/prompt/{quote(render_prompt)}?width=1024&height=576&nologo=true"
        st.image(url, caption="AI concept render (Pollinations)", use_container_width=True)

# ----------------------------------------------------------------------------
# Tab 4: Weather advisory + chatbot
# ----------------------------------------------------------------------------
with tab4:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    wx = st.radio("Today's weather condition", list(WEATHER), horizontal=True, index=0)
    cfg = WEATHER[wx]
    css = {"ok": "ok", "warn": "warn", "crit": ""}[cfg["kind"]]
    for a in cfg["alerts"]:
        st.markdown(f'<div class="alert {css}">{a}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 💬 Construction Engineering Assistant")
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant",
                                  "content": "Hello! I'm your site engineering assistant. Ask about curing, reinforcement, scheduling or safety."}]
    top = st.columns([6, 1])
    if top[1].button("Clear", key="clear_chat"):
        st.session_state.chat = st.session_state.chat[:1]
        st.rerun()
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a construction engineering question..."):
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            client = get_client()
            if client is None:
                reply = demo_chat_reply(prompt)
            else:
                try:
                    from google.genai import types
                    history = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in st.session_state.chat[-12:])
                    with st.spinner("Thinking..."):
                        r = client.models.generate_content(
                            model=MODEL,
                            contents=f"Current site weather: {wx}.\n\n{history}\nASSISTANT:",
                            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.4))
                    reply = r.text
                except Exception as e:
                    reply = f"⚠️ Gemini request failed ({type(e).__name__}). Falling back to demo reply.\n\n" + demo_chat_reply(prompt)
            st.markdown(reply)
        st.session_state.chat.append({"role": "assistant", "content": reply})

st.markdown("---")
st.caption("⚠️ AI output is advisory only. Safety and structural decisions must be verified by qualified professionals.")
