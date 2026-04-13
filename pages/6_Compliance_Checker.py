import streamlit as st
import anthropic
import json
import re
import os
import datetime
import io

st.set_page_config(page_title="Compliance Checker", page_icon="✅", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.pass-row{background:#D1FAE5}
.partial-row{background:#FEF3C7}
.missing-row{background:#FDECEA}
</style>""", unsafe_allow_html=True)


def get_api_key():
    if "ANTHROPIC_API_KEY" in st.secrets:
        return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY", "")


def extract_text(uploaded_file):
    name = uploaded_file.name.lower()
    raw  = uploaded_file.read()
    if name.endswith(".pdf"):
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(raw))
        return "\n\n".join(
            p.extract_text() for p in reader.pages if p.extract_text()
        )
    elif name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(raw))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        return raw.decode("utf-8", errors="ignore")


def extract_requirements(client, rfp_text):
    prompt = f"""You are a grant compliance specialist. Read this RFP and extract
EVERY distinct requirement an applicant must address.

For each requirement return a JSON object with:
  "id": sequential number
  "category": one of: Eligibility | Program Design | Evaluation | Budget |
               Organizational Capacity | Formatting | Attachments | Other
  "requirement": plain-language statement (1-2 sentences)
  "mandatory": true if explicitly required, false if recommended
  "source_quote": exact phrase from RFP (max 20 words)

Return ONLY a valid JSON array. No prose, no markdown fences.

RFP:\n{rfp_text[:12000]}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = re.sub(r"^```json\s*", "", msg.content[0].text.strip())
    raw = re.sub(r"```\s*$", "", raw)
    return json.loads(raw)


def check_requirement(client, req, draft_text):
    prompt = f"""Check whether this grant narrative draft addresses the following requirement.

REQUIREMENT #{req['id']} ({req['category']}):
{req['requirement']}
Source: "{req.get('source_quote','')}"

DRAFT NARRATIVE:
{draft_text[:8000]}

Return ONLY a JSON object:
  "status": "Pass" | "Partial" | "Missing"
  "confidence": 1-5
  "finding": 1-2 sentence explanation
  "recommendation": specific suggestion if Partial/Missing, else "None needed."
  "draft_excerpt": most relevant 1-2 sentences from draft, or "Not found."

Valid JSON only, no prose."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = re.sub(r"^```json\s*", "", msg.content[0].text.strip())
    raw = re.sub(r"```\s*$", "", raw)
    try:
        return {**req, **json.loads(raw)}
    except Exception:
        return {**req, "status": "Unknown", "confidence": 1,
                "finding": "Could not parse response",
                "recommendation": "Review manually", "draft_excerpt": "N/A"}


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("✅ Grant Compliance Checker")
st.caption("Upload your RFP and draft narrative — Claude checks every requirement and flags gaps.")

api_key = get_api_key()
if not api_key:
    st.markdown(
        '<div class="warn">⚠ API key not set. Add ANTHROPIC_API_KEY in '
        'Streamlit Cloud → Settings → Secrets.</div>',
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.markdown("### About")
    st.markdown("""This tool:
1. Reads your RFP and extracts every requirement
2. Checks your draft against each one
3. Returns Pass / Partial / Missing for each
4. Gives specific recommendations for gaps

**Cost:** ~$0.10–0.20 per check depending on document length.
""")
    st.markdown("---")
    st.markdown("### Filters")
    filter_status = st.multiselect(
        "Show statuses",
        ["Pass", "Partial", "Missing", "Unknown"],
        default=["Partial", "Missing"],
    )
    filter_mandatory = st.checkbox("Required items only", value=False)

# Upload section
st.markdown("## Step 1 — Upload your files")

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="hint">Your RFP or NOFO — PDF or Word</div>',
                unsafe_allow_html=True)
    rfp_file = st.file_uploader("Upload RFP",
        type=["pdf", "docx", "txt"], label_visibility="collapsed", key="rfp")

with c2:
    st.markdown('<div class="hint">Your draft narrative — Word or text</div>',
                unsafe_allow_html=True)
    draft_file = st.file_uploader("Upload draft",
        type=["pdf", "docx", "txt"], label_visibility="collapsed", key="draft")

if "compliance_results" not in st.session_state:
    st.session_state.compliance_results = []

if rfp_file and draft_file:
    c_btn, _ = st.columns([2, 3])
    with c_btn:
        run_btn = st.button(
            "✨ Run compliance check",
            disabled=not api_key,
            use_container_width=True,
        )

    if run_btn:
        with st.spinner("Reading files..."):
            rfp_text   = extract_text(rfp_file)
            draft_text = extract_text(draft_file)

        if not rfp_text.strip():
            st.error("Could not read RFP file.")
        elif not draft_text.strip():
            st.error("Could not read draft file.")
        else:
            client = anthropic.Anthropic(api_key=api_key)

            progress = st.progress(0, text="Extracting requirements from RFP...")
            try:
                requirements = extract_requirements(client, rfp_text)
            except Exception as e:
                st.error(f"Could not extract requirements: {e}")
                st.stop()

            results = []
            for i, req in enumerate(requirements):
                progress.progress(
                    (i + 1) / len(requirements),
                    text=f"Checking requirement {i+1}/{len(requirements)}: "
                         f"{req.get('category','')} — {req.get('requirement','')[:50]}...",
                )
                results.append(check_requirement(client, req, draft_text))

            progress.empty()
            st.session_state.compliance_results = results
            st.rerun()

# Results
results = st.session_state.compliance_results
if results:
    total   = len(results)
    passed  = sum(1 for r in results if r.get("status") == "Pass")
    partial = sum(1 for r in results if r.get("status") == "Partial")
    missing = sum(1 for r in results if r.get("status") == "Missing")
    mand_m  = sum(1 for r in results if r.get("status") == "Missing"
                  and r.get("mandatory", True))
    score   = round(passed / total * 100) if total else 0

    st.markdown("## Results")

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total requirements", total)
    k2.metric("✓ Passing", passed)
    k3.metric("~ Partial", partial)
    k4.metric("✗ Missing", missing)
    k5.metric("Compliance score", f"{score}%")

    if mand_m > 0:
        names = [r["requirement"][:60] for r in results
                 if r.get("status") == "Missing" and r.get("mandatory", True)]
        st.error(
            f"⚠ **{mand_m} mandatory requirement(s) missing** — "
            f"address before submitting:\n" +
            "\n".join(f"• {n}..." for n in names[:5])
        )
    else:
        st.success("✓ All mandatory requirements addressed. Review Partial items before submitting.")

    # Filter
    filtered = results
    if filter_status:
        filtered = [r for r in filtered if r.get("status") in filter_status]
    if filter_mandatory:
        filtered = [r for r in filtered if r.get("mandatory", True)]

    st.caption(f"Showing {len(filtered)} of {total} requirements")

    # Table
    import pandas as pd
    df = pd.DataFrame([{
        "#":              r.get("id", ""),
        "Category":       r.get("category", ""),
        "Requirement":    r.get("requirement", "")[:100],
        "Required?":      "Required" if r.get("mandatory", True) else "Preferred",
        "Status":         r.get("status", ""),
        "Finding":        r.get("finding", "")[:120],
        "Recommendation": r.get("recommendation", ""),
    } for r in filtered])

    def color_status(val):
        if val == "Pass":    return "background-color:#D1FAE5;color:#065F46;font-weight:600"
        if val == "Partial": return "background-color:#FEF3C7;color:#92400E;font-weight:600"
        if val == "Missing": return "background-color:#FDECEA;color:#C0392B;font-weight:600"
        return ""

    st.dataframe(
        df.style.applymap(color_status, subset=["Status"]),
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    # Detailed expanders for missing/partial
    missing_partial = [r for r in filtered
                       if r.get("status") in ("Missing", "Partial")]
    if missing_partial:
        st.markdown("### Detailed recommendations")
        for r in missing_partial:
            color = "🔴" if r.get("status") == "Missing" else "🟡"
            with st.expander(
                f"{color} #{r.get('id')} [{r.get('category')}] "
                f"{r.get('requirement','')[:80]}..."
            ):
                st.markdown(f"**Status:** {r.get('status')}")
                st.markdown(f"**Finding:** {r.get('finding','')}")
                if r.get("draft_excerpt") and r["draft_excerpt"] != "Not found.":
                    st.markdown(f"**Found in draft:** *{r.get('draft_excerpt','')}*")
                st.markdown(f"**Recommendation:** {r.get('recommendation','')}")
                if r.get("source_quote"):
                    st.caption(f"RFP source: \"{r.get('source_quote','')}\"")

    # Download
    out = io.BytesIO()
    full_df = pd.DataFrame([{
        "ID": r.get("id"), "Category": r.get("category"),
        "Requirement": r.get("requirement"), "Mandatory": r.get("mandatory"),
        "Status": r.get("status"), "Confidence": r.get("confidence"),
        "Finding": r.get("finding"), "Recommendation": r.get("recommendation"),
        "Draft Excerpt": r.get("draft_excerpt"),
    } for r in results])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        full_df.to_excel(w, index=False, sheet_name="Compliance Report")
    st.download_button(
        "⬇ Download full report as Excel",
        data=out.getvalue(),
        file_name=f"compliance_report_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
