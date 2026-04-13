import streamlit as st
import anthropic
import json, os, re, datetime, subprocess, tempfile

st.set_page_config(page_title="Logic Model Builder", page_icon="📋", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.section-card{background:white;border-radius:10px;padding:14px 18px;margin-bottom:10px;
  box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #1A6E6E}
.section-card.blue{border-left-color:#1E40AF}.section-card.purple{border-left-color:#3C3489}
.section-card.green{border-left-color:#065F46}.section-card.amber{border-left-color:#92400E}
.section-card.coral{border-left-color:#993C1D}.section-card.gray{border-left-color:#5F5E5A}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
</style>""", unsafe_allow_html=True)

FIELDS = ["inputs","activities","outputs","short_term_outcomes",
          "medium_term_outcomes","long_term_outcomes","assumptions","external_factors"]
FIELD_META = {
    "inputs":               ("Inputs",               "teal",   "Resources — staff, funding, facilities, partnerships"),
    "activities":           ("Activities",            "blue",   "What you do — services, training, outreach"),
    "outputs":              ("Outputs",               "purple", "Countable products — sessions, participants, events"),
    "short_term_outcomes":  ("Short-Term Outcomes",   "green",  "Changes 0–6 months after participation"),
    "medium_term_outcomes": ("Medium-Term Outcomes",  "amber",  "Changes 6–24 months after participation"),
    "long_term_outcomes":   ("Long-Term Outcomes",    "coral",  "Broader changes 2–5 years out"),
    "assumptions":          ("Assumptions",           "gray",   "Conditions that must hold for the theory of change"),
    "external_factors":     ("External Factors",      "gray",   "Outside conditions that could affect outcomes"),
}

for f in FIELDS:
    if f not in st.session_state: st.session_state[f] = []
for k,v in [("lm_program",""),("lm_org","Communicare Alliance"),
            ("lm_location","Woonsocket, RI"),("lm_funder",""),
            ("lm_period",""),("lm_extracted",False),("lm_docx",None)]:
    if k not in st.session_state: st.session_state[k] = v

def get_api_key():
    if "ANTHROPIC_API_KEY" in st.secrets: return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY","")

def extract_text(f):
    name = f.name.lower(); raw = f.read()
    if name.endswith(".pdf"):
        import PyPDF2, io
        r = PyPDF2.PdfReader(io.BytesIO(raw))
        return "\n\n".join(p.extract_text() for p in r.pages if p.extract_text())
    elif name.endswith(".docx"):
        from docx import Document; import io
        return "\n\n".join(p.text for p in Document(io.BytesIO(raw)).paragraphs if p.text.strip())
    elif name.endswith((".xlsx",".xls")):
        import pandas as pd, io
        sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None)
        return "\n\n".join(f"Sheet: {k}\n{v.to_string(index=False)}" for k,v in sheets.items())
    else:
        return raw.decode("utf-8", errors="ignore")

def extract_logic_model(text, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""Read this document and extract a complete logic model.
Return ONLY valid JSON with these keys:
{{"program_name":"","org_name":"","funder":"","period":"",
"inputs":[],"activities":[],"outputs":[],
"short_term_outcomes":[],"medium_term_outcomes":[],"long_term_outcomes":[],
"assumptions":[],"external_factors":[]}}
Extract only what is actually in the document. 5-12 items per list where supported.
DOCUMENT:\n{text[:12000]}"""
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=3000,
        messages=[{"role":"user","content":prompt}])
    raw = re.sub(r"^```json\s*","",msg.content[0].text.strip())
    raw = re.sub(r"```\s*$","",raw)
    return json.loads(raw)

def build_docx(program):
    today = datetime.date.today().strftime("%B %d, %Y")
    payload = json.dumps({**program,"today":today}, ensure_ascii=False)
    js = r"""
const{Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,
AlignmentType,BorderStyle,WidthType,ShadingType,LevelFormat,VerticalAlign}=require('docx');
const fs=require('fs');
const D=""" + payload + r""";
const OUT=D.output_path;
const T="1A6E6E",TP="E1F5EE",TM="9FE1CB",W="FFFFFF",GL="F5F5F5",GM="D1D5DB",DK="1F2937";
const AM="92400E",AML="FEF3C7",BL="1E40AF",BLL="DBEAFE";
const GN="065F46",GNL="D1FAE5",PU="3C3489",PUL="EEEDFE",CO="993C1D",COL="FAECE7";
const COLS=[
  {key:"inputs",label:"INPUTS",hbg:T,bbg:TP,tc:"0F6E56"},
  {key:"activities",label:"ACTIVITIES",hbg:BL,bbg:BLL,tc:BL},
  {key:"outputs",label:"OUTPUTS",hbg:PU,bbg:PUL,tc:PU},
  {key:"short_term_outcomes",label:"SHORT-TERM\nOUTCOMES",hbg:GN,bbg:GNL,tc:GN},
  {key:"medium_term_outcomes",label:"MEDIUM-TERM\nOUTCOMES",hbg:AM,bbg:AML,tc:AM},
  {key:"long_term_outcomes",label:"LONG-TERM\nOUTCOMES",hbg:CO,bbg:COL,tc:CO},
];
const TW=14040,CW=Math.floor(TW/COLS.length);
const cw=COLS.map((_,i)=>i<COLS.length-1?CW:TW-CW*(COLS.length-1));
const bdr=(c=GM)=>({style:BorderStyle.SINGLE,size:4,color:c});
const bdrs=c=>({top:bdr(c),bottom:bdr(c),left:bdr(c),right:bdr(c)});
const shd=h=>({fill:h,type:ShadingType.CLEAR});
const mg=(t=80,b=80,l=100,r=100)=>({top:t,bottom:b,left:l,right:r});
const tr=(text,o={})=>new TextRun({text,font:"Arial",size:o.size||18,bold:o.bold||false,
  color:o.color||DK,italics:o.italic||false});
const p=(text,o={})=>new Paragraph({children:[tr(text,o)],
  spacing:{before:o.before||0,after:o.after||60},alignment:o.align||AlignmentType.LEFT});
const blt=(text,color=DK)=>new Paragraph({numbering:{reference:"bullets",level:0},
  spacing:{before:0,after:40},children:[tr(text,{size:17,color})]});
const lt=new Table({width:{size:TW,type:WidthType.DXA},columnWidths:cw,rows:[
  new TableRow({children:[new TableCell({columnSpan:COLS.length,borders:bdrs(T),
    width:{size:TW,type:WidthType.DXA},shading:shd(T),margins:mg(120,120,160,160),
    verticalAlign:VerticalAlign.CENTER,children:[
      new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:0,after:40},
        children:[tr(D.program_name||"Program Logic Model",{bold:true,size:30,color:W})]}),
      new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:0,after:0},
        children:[tr((D.org_name||"")+(D.org_location?" \u00b7 "+D.org_location:""),{size:20,color:TM}),
          tr(D.funder?" \u00b7 "+D.funder:"",{size:20,color:TM}),
          tr(D.period?" \u00b7 "+D.period:"",{size:20,color:TM})]}),
    ]})]
  }),
  new TableRow({height:{value:280,rule:"atLeast"},children:[
    ...[{label:"RESOURCES",span:1,bg:TP,tc:T},
        {label:"PROGRAM IMPLEMENTATION",span:2,bg:BLL,tc:BL},
        {label:"\u2190\u2014\u2014\u2014 RESULTS \u2014\u2014\u2014\u2192",span:3,bg:GNL,tc:GN}]
      .map((g,idx)=>{const si=idx===0?0:idx===1?1:3;
        const w=cw.slice(si,si+g.span).reduce((a,b)=>a+b,0);
        return new TableCell({columnSpan:g.span,borders:bdrs(GM),
          width:{size:w,type:WidthType.DXA},shading:shd(g.bg),margins:mg(60,60,120,120),
          verticalAlign:VerticalAlign.CENTER,children:[new Paragraph({
            alignment:AlignmentType.CENTER,spacing:{before:0,after:0},
            children:[tr(g.label,{bold:true,size:16,color:g.tc})]})]})})
  ]}),
  new TableRow({tableHeader:true,height:{value:500,rule:"atLeast"},
    children:COLS.map((col,i)=>new TableCell({borders:bdrs(col.hbg),
      width:{size:cw[i],type:WidthType.DXA},shading:shd(col.hbg),margins:mg(100,100,120,120),
      verticalAlign:VerticalAlign.CENTER,
      children:col.label.split("\n").map((line,li)=>new Paragraph({
        alignment:AlignmentType.CENTER,spacing:{before:0,after:li===0&&col.label.includes("\n")?20:0},
        children:[tr(line,{bold:true,size:18,color:W})]}))}))}),
  new TableRow({children:COLS.map((col,i)=>new TableCell({borders:bdrs(GM),
    width:{size:cw[i],type:WidthType.DXA},shading:shd(col.bbg),margins:mg(100,100,120,120),
    verticalAlign:VerticalAlign.TOP,children:(D[col.key]||[]).map(item=>blt(item,col.tc))}))})
]});
const smt=(label,items,hbg,bbg,tc)=>{const SW=9360;return new Table({
  width:{size:SW,type:WidthType.DXA},columnWidths:[SW],rows:[
    new TableRow({children:[new TableCell({borders:bdrs(hbg),width:{size:SW,type:WidthType.DXA},
      shading:shd(hbg),margins:mg(80,80,120,120),children:[p(label,{bold:true,size:18,color:W})]})]}),
    new TableRow({children:[new TableCell({borders:bdrs(GM),width:{size:SW,type:WidthType.DXA},
      shading:shd(bbg),margins:mg(100,100,120,120),verticalAlign:VerticalAlign.TOP,
      children:(items||[]).map(item=>blt(item,tc))})]})
  ]})};
const doc=new Document({
  styles:{default:{document:{run:{font:"Arial",size:18}}}},
  numbering:{config:[{reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,
    text:"\u2022",alignment:AlignmentType.LEFT,
    style:{paragraph:{indent:{left:360,hanging:260}}}}]}]},
  sections:[
    {properties:{page:{size:{width:12240,height:15840,orientation:"landscape"},
      margin:{top:720,right:900,bottom:720,left:900}}},
     children:[lt,new Paragraph({spacing:{before:120,after:0},alignment:AlignmentType.CENTER,
       children:[tr((D.org_name||"")+" \u00b7 Logic Model \u00b7 "+(D.program_name||"")+" \u00b7 "+D.today,
         {size:14,color:"AAAAAA",italic:true})]})]},
    {properties:{page:{size:{width:12240,height:15840},margin:{top:1080,right:1080,bottom:1080,left:1080}}},
     children:[p((D.program_name||"Program")+" \u2014 Supporting Notes",{bold:true,size:24,color:T,after:120}),
       p("Generated: "+D.today,{size:16,color:"888888",italic:true,after:200}),
       smt("ASSUMPTIONS",D.assumptions,T,TP,"0F6E56"),
       new Paragraph({spacing:{before:200,after:0},children:[]}),
       smt("EXTERNAL FACTORS",D.external_factors,"5F5E5A",GL,"444441"),
       new Paragraph({spacing:{before:240,after:0},alignment:AlignmentType.CENTER,
         children:[tr((D.org_name||"")+" \u00b7 Generated "+D.today,{size:14,color:"AAAAAA",italic:true})]})]},
  ],
});
Packer.toBuffer(doc).then(buf=>{fs.writeFileSync(OUT,buf);console.log("saved:"+OUT);});
"""
    with tempfile.TemporaryDirectory() as tmp:
        js_path   = os.path.join(tmp,"build.js")
        docx_path = os.path.join(tmp,"logic_model.docx")
        program["output_path"] = docx_path
        js2 = js.replace("const D="+payload,
                         "const D="+json.dumps({**program,"today":today},ensure_ascii=False))
        with open(js_path,"w") as f: f.write(js2)
        r = subprocess.run(["node",js_path],capture_output=True,text=True,timeout=30)
        if r.returncode != 0: raise RuntimeError(r.stderr[:400])
        return open(docx_path,"rb").read()

def editable_list(field, label, color, hint):
    st.markdown(f'<div class="section-card {color}"><strong>{label}</strong> '
                f'<span style="color:#9CA3AF;font-size:.8rem">— {hint}</span></div>',
                unsafe_allow_html=True)
    to_del = []
    for i, item in enumerate(st.session_state[field]):
        c1,c2 = st.columns([11,1])
        with c1:
            v = st.text_input(f"{field}_{i}",value=item,key=f"{field}_inp_{i}",
                              label_visibility="collapsed")
            st.session_state[field][i] = v
        with c2:
            if st.button("✕",key=f"del_{field}_{i}"): to_del.append(i)
    for idx in reversed(to_del):
        st.session_state[field].pop(idx); st.rerun()
    new = st.text_input(f"add_{field}",placeholder=f"+ Add {label.lower()}...",
                        key=f"new_{field}",label_visibility="collapsed")
    if new:
        st.session_state[field].append(new); st.rerun()
    st.caption(f"{len(st.session_state[field])} items")
    st.markdown("---")

# ── UI ──────────────────────────────────────────────────────────────────────

st.title("📋 Logic Model Builder")
st.caption("Upload a document — Claude extracts your program data and builds a formatted Word logic model.")

api_key = get_api_key()
if not api_key:
    st.markdown('<div class="warn">⚠ API key not set. Add it in Streamlit Cloud → Settings → Secrets as ANTHROPIC_API_KEY.</div>',
                unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Program details")
    st.session_state.lm_org      = st.text_input("Organization", st.session_state.lm_org)
    st.session_state.lm_location = st.text_input("Location",     st.session_state.lm_location)
    st.session_state.lm_program  = st.text_input("Program name", st.session_state.lm_program)
    st.session_state.lm_funder   = st.text_input("Funder",       st.session_state.lm_funder)
    st.session_state.lm_period   = st.text_input("Grant period",  st.session_state.lm_period)
    st.markdown("---")
    if st.button("🗑 Clear all", use_container_width=True):
        for f in FIELDS: st.session_state[f] = []
        st.session_state.lm_extracted = False
        st.session_state.lm_docx = None
        st.rerun()
    st.markdown("### Item counts")
    for field in FIELDS:
        label,_,_ = FIELD_META[field]
        n = len(st.session_state[field])
        st.caption(f"{'🟢' if n>=3 else '🟡' if n>=1 else '⚪'} {label}: {n}")

st.markdown("## Step 1 — Upload your document")
st.markdown('<div class="hint">Accepts PDF, Word (.docx), Excel (.xlsx), or text files. '
            'The more detail your file contains, the better the logic model.</div>',
            unsafe_allow_html=True)

uploaded = st.file_uploader("Drop file here",
    type=["pdf","docx","xlsx","xls","txt"], label_visibility="collapsed")

if uploaded:
    c1,c2 = st.columns([3,1])
    with c1: st.success(f"✅ {uploaded.name}  ({uploaded.size:,} bytes)")
    with c2:
        if st.button("✨ Extract with Claude", disabled=not api_key):
            with st.spinner("Reading and extracting..."):
                try:
                    text = extract_text(uploaded)
                    if not text.strip():
                        st.error("Could not read text from this file.")
                    else:
                        result = extract_logic_model(text, api_key)
                        for f in FIELDS:
                            if f in result and result[f]:
                                st.session_state[f] = result[f]
                        if result.get("program_name"): st.session_state.lm_program = result["program_name"]
                        if result.get("funder"):       st.session_state.lm_funder  = result["funder"]
                        if result.get("period"):       st.session_state.lm_period  = result["period"]
                        st.session_state.lm_extracted = True
                        st.session_state.lm_docx = None
                        total = sum(len(st.session_state[f]) for f in FIELDS)
                        st.success(f"✅ Extracted {total} items. Review below.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

st.markdown("## Step 2 — Review and edit")

total = sum(len(st.session_state[f]) for f in FIELDS)
if total > 0:
    cols = st.columns(len(FIELDS))
    for i,f in enumerate(FIELDS):
        lbl,_,_ = FIELD_META[f]
        with cols[i]:
            st.markdown(f'<div style="background:#E1F5EE;border-radius:8px;padding:10px;text-align:center">'
                        f'<div style="font-size:1.4rem;font-weight:700;color:#1A6E6E">{len(st.session_state[f])}</div>'
                        f'<div style="font-size:.7rem;color:#6B7280">{lbl.split()[0]}</div></div>',
                        unsafe_allow_html=True)

cl, cr = st.columns(2)
with cl:
    for f in ["inputs","activities","outputs","assumptions"]:
        editable_list(f, *FIELD_META[f])
with cr:
    for f in ["short_term_outcomes","medium_term_outcomes","long_term_outcomes","external_factors"]:
        editable_list(f, *FIELD_META[f])

st.markdown("## Step 3 — Generate")
has = any(len(st.session_state[f]) > 0 for f in FIELDS)

if not has:
    st.info("Add at least one item above to generate.")
else:
    g1,g2 = st.columns([2,1])
    with g1:
        if st.button("📄 Generate Logic Model Word Doc", use_container_width=True):
            prog = {"org_name":st.session_state.lm_org,"org_location":st.session_state.lm_location,
                    "program_name":st.session_state.lm_program,"funder":st.session_state.lm_funder,
                    "period":st.session_state.lm_period,"preparer":"Program Development & Grants Manager"}
            for f in FIELDS: prog[f] = st.session_state[f]
            with st.spinner("Building Word document..."):
                try:
                    st.session_state.lm_docx = build_docx(prog)
                    st.success("✅ Ready to download!")
                except FileNotFoundError:
                    st.error("Node.js not available. The Word doc builder requires Node.js.")
                except Exception as e:
                    st.error(f"Build failed: {e}")
    with g2:
        if st.session_state.lm_docx:
            slug = (st.session_state.lm_program or "logic_model").lower().replace(" ","_")[:30]
            st.download_button("⬇ Download .docx", data=st.session_state.lm_docx,
                file_name=f"{slug}_logic_model.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)
