import streamlit as st
import anthropic
import os
import datetime
import sys

st.set_page_config(page_title="Boilerplate Library", page_icon="📚", layout="wide")

st.markdown("""
<style>
h1{color:#1A6E6E!important}h2{color:#1A6E6E!important;font-size:1.1rem!important}
.stButton>button{background:#1A6E6E!important;color:white!important;border:none!important;
  border-radius:8px!important;font-weight:600!important}
.hint{background:#E1F5EE;border-radius:8px;padding:10px 14px;font-size:.85rem;color:#085041;margin-bottom:10px}
.warn{background:#FEF3C7;border-left:3px solid #BA7517;border-radius:0 8px 8px 0;
  padding:10px 14px;font-size:.85rem;color:#92400E;margin-bottom:10px}
.save-ok{background:#D1FAE5;border-left:3px solid #065F46;border-radius:0 8px 8px 0;
  padding:8px 14px;font-size:.85rem;color:#065F46;margin-bottom:8px}
.block-card{background:white;border-radius:10px;padding:14px 18px;margin-bottom:10px;
  box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #1A6E6E}
.block-card.amber{border-left-color:#BA7517}.block-card.blue{border-left-color:#185FA5}
.block-card.purple{border-left-color:#534AB7}.block-card.coral{border-left-color:#993C1D}
.block-card.green{border-left-color:#065F46}.block-card.gray{border-left-color:#9CA3AF}
.tag{display:inline-block;background:#E1F5EE;color:#085041;padding:2px 8px;border-radius:99px;font-size:11px;margin:2px}
</style>""", unsafe_allow_html=True)

# ── OneDrive helper ────────────────────────────────────────────────────────────

try:
    from onedrive_helper import (
        load_boilerplate, save_boilerplate,
        STARTER_BLOCKS, BOILERPLATE_HEADERS,
    )
    ONEDRIVE_AVAILABLE = True
except Exception:
    ONEDRIVE_AVAILABLE = False

# ── API key ────────────────────────────────────────────────────────────────────

def get_api_key():
    if "ANTHROPIC_API_KEY" in st.secrets: return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY", "")

CATEGORY_COLORS = {
    "Org Identity":"teal","Community Need":"blue","Pilot Data & Outcomes":"green",
    "Staff Bios":"amber","Program Descriptions":"purple","Partnerships":"coral",
    "Evaluation":"blue","Equity":"green","Sustainability":"amber",
}

def get_color(cat): return CATEGORY_COLORS.get(cat, "teal")

# ── Session state ──────────────────────────────────────────────────────────────

def init_library():
    if "library" not in st.session_state:
        if ONEDRIVE_AVAILABLE:
            with st.spinner("Loading your library from OneDrive..."):
                st.session_state.library = load_boilerplate()
        else:
            st.session_state.library = list(STARTER_BLOCKS)
        ids = [b.get("id",0) for b in st.session_state.library if b.get("id")]
        st.session_state.next_id = max(ids) + 1 if ids else len(st.session_state.library) + 1
    if "polished_text"  not in st.session_state: st.session_state.polished_text  = ""
    if "last_saved"     not in st.session_state: st.session_state.last_saved      = None
    if "save_pending"   not in st.session_state: st.session_state.save_pending    = False

def persist(action=""):
    """Save library to OneDrive and update last_saved timestamp."""
    if ONEDRIVE_AVAILABLE:
        ok = save_boilerplate(st.session_state.library)
        if ok:
            st.session_state.last_saved = datetime.datetime.now().strftime("%I:%M %p")
    st.session_state.save_pending = False

def get_blocks(): return st.session_state.library
def get_categories():
    seen = []
    for b in st.session_state.library:
        if b["category"] not in seen: seen.append(b["category"])
    return seen

def search_blocks(query):
    if not query.strip(): return st.session_state.library
    terms = query.lower().split()
    return sorted(
        [b for b in st.session_state.library
         if all(t in (b["title"]+b["content"]+b["tags"]+b["category"]+b.get("notes","")).lower()
                for t in terms)],
        key=lambda x: x.get("use_count",0), reverse=True
    )

def add_block(category, title, tags, content, notes):
    new_id = st.session_state.next_id
    st.session_state.library.append({
        "id": new_id, "category": category, "title": title,
        "tags": tags, "content": content, "notes": notes,
        "use_count": 0, "created": str(datetime.date.today()),
    })
    st.session_state.next_id += 1
    persist("add")
    return new_id

def delete_block(block_id):
    st.session_state.library = [b for b in st.session_state.library if b["id"] != block_id]
    persist("delete")

def increment_use(block_id):
    for b in st.session_state.library:
        if b["id"] == block_id:
            b["use_count"] = b.get("use_count", 0) + 1
            break
    persist("use")

def polish_with_claude(content, funder, program, word_count, notes_text, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=800,
        messages=[{"role":"user","content":
            f"You are helping a grant writer at Communicare Alliance in Woonsocket, RI "
            f"tailor a boilerplate text block for a specific grant application.\n\n"
            f"ORIGINAL TEXT:\n{content}\n\n"
            f"TAILOR FOR:\n- Funder: {funder}\n- Grant/program: {program}\n"
            f"- Target word count: {word_count} words\n- Special notes: {notes_text or 'None'}\n\n"
            f"Rewrite optimally for this funder. Keep all facts accurate. "
            f"Stay within 10% of word count. Return ONLY the rewritten text."}])
    return msg.content[0].text.strip()

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

init_library()
api_key = get_api_key()

st.title("📚 Boilerplate Library")
st.caption("Searchable database of reusable text blocks — saved permanently to OneDrive.")

# Save status banner
if ONEDRIVE_AVAILABLE:
    if st.session_state.last_saved:
        st.markdown(
            f'<div class="save-ok">✅ Library synced to OneDrive at {st.session_state.last_saved} '
            f'— your blocks are saved permanently.</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="warn">⚠ OneDrive not configured — blocks will reset when you close the browser. '
        'Add Azure credentials to Streamlit Secrets to enable persistence.</div>',
        unsafe_allow_html=True,
    )

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Library stats")
    blocks = get_blocks()
    st.metric("Total blocks", len(blocks))
    st.metric("Categories",   len(get_categories()))
    top = sorted(blocks, key=lambda x: x.get("use_count",0), reverse=True)[:3]
    if any(b.get("use_count",0) > 0 for b in top):
        st.markdown("**Most used:**")
        for b in top:
            if b.get("use_count",0) > 0:
                st.caption(f"• {b['title'][:38]}... ({b['use_count']}x)")
    st.markdown("---")
    if st.button("🔄 Reload from OneDrive", use_container_width=True, disabled=not ONEDRIVE_AVAILABLE):
        del st.session_state["library"]
        st.rerun()
    if st.button("🗑 Clear session cache", use_container_width=True):
        for k in ["library","next_id","polished_text","last_saved","save_pending"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.markdown("---")
    st.markdown("### Export all blocks")
    export_text = "\n\n".join(
        f"[{b['id']}] {b['category'].upper()} — {b['title']}\n"
        f"Tags: {b['tags']}\n\n{b['content']}"
        + (f"\n\nNOTES: {b['notes']}" if b.get('notes') else "")
        + "\n" + "─"*60
        for b in blocks
    )
    st.download_button("⬇ Download all as text", data=export_text.encode("utf-8"),
        file_name=f"boilerplate_{datetime.date.today()}.txt", mime="text/plain",
        use_container_width=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_search, tab_browse, tab_add, tab_polish = st.tabs([
    "🔍 Search", "📂 Browse", "➕ Add new block", "✨ Polish with Claude"
])

# ── TAB 1: Search ──────────────────────────────────────────────────────────────

with tab_search:
    st.markdown("### Search your library")
    st.markdown('<div class="hint">Try: mission · pilot data · equity · youth mental health · sustainability · bio</div>', unsafe_allow_html=True)
    query   = st.text_input("Search", placeholder="Type keywords...", label_visibility="collapsed")
    results = search_blocks(query)

    if query and not results:
        st.info("No results. Try different keywords or browse by category.")

    for b in results:
        wc    = len(b["content"].split())
        color = get_color(b["category"])
        st.markdown(
            f'<div class="block-card {color}"><strong>{b["title"]}</strong>'
            f'<span style="color:#9CA3AF;font-size:.8rem"> — {b["category"]} · {wc} words · used {b.get("use_count",0)}x</span></div>',
            unsafe_allow_html=True,
        )
        if b.get("tags"):
            st.markdown(" ".join(f'<span class="tag">{t.strip()}</span>' for t in b["tags"].split(",")), unsafe_allow_html=True)

        show_full = st.checkbox("Show full text", key=f"show_{b['id']}")
        if show_full:
            st.text_area("Content", value=b["content"], height=150,
                         key=f"content_{b['id']}", label_visibility="collapsed")
            if b.get("notes"): st.caption(f"📝 {b['notes']}")
            if st.button("✅ Mark as used", key=f"use_{b['id']}"):
                increment_use(b["id"])
                st.success("Logged and saved to OneDrive!" if ONEDRIVE_AVAILABLE else "Logged!")
                st.rerun()
        else:
            st.caption(b["content"][:200] + ("..." if len(b["content"]) > 200 else ""))

        if st.button("🗑 Delete", key=f"del_{b['id']}"):
            delete_block(b["id"])
            st.rerun()
        st.markdown("---")

# ── TAB 2: Browse ──────────────────────────────────────────────────────────────

with tab_browse:
    st.markdown("### Browse by category")
    selected_cat = st.selectbox("Category", get_categories(), label_visibility="collapsed")
    cat_blocks   = [b for b in get_blocks() if b["category"] == selected_cat]
    st.caption(f"{len(cat_blocks)} block(s) in {selected_cat}")
    for b in cat_blocks:
        wc = len(b["content"].split())
        with st.expander(f"**{b['title']}** — {wc} words · used {b.get('use_count',0)}x"):
            st.text_area("Content", value=b["content"], height=130,
                         key=f"browse_{b['id']}", label_visibility="collapsed")
            if b.get("notes"): st.caption(f"📝 {b['notes']}")
            if b.get("tags"):
                st.markdown(" ".join(f'<span class="tag">{t.strip()}</span>' for t in b["tags"].split(",")), unsafe_allow_html=True)
            if st.button("✅ Mark as used", key=f"buse_{b['id']}"):
                increment_use(b["id"])
                st.success("Saved!" if ONEDRIVE_AVAILABLE else "Logged!")

# ── TAB 3: Add ─────────────────────────────────────────────────────────────────

with tab_add:
    st.markdown("### Add a new block")
    st.markdown('<div class="hint">Every good paragraph you write can go in the library for next time. '
                'Saved permanently to OneDrive.</div>', unsafe_allow_html=True)
    existing_cats = get_categories() + ["+ New category"]
    cat_choice    = st.selectbox("Category", existing_cats)
    new_category  = st.text_input("New category name") if cat_choice == "+ New category" else cat_choice
    new_title     = st.text_input("Title")
    new_tags      = st.text_input("Tags (comma-separated)")
    new_content   = st.text_area("Text content", height=180)
    new_notes     = st.text_input("Internal notes")

    if st.button("💾 Save to library"):
        if not new_title: st.error("Please enter a title.")
        elif not new_content: st.error("Please enter content.")
        elif not new_category or new_category == "+ New category": st.error("Please enter a category.")
        else:
            new_id = add_block(new_category, new_title, new_tags, new_content, new_notes)
            wc     = len(new_content.split())
            msg = f"✅ Saved as block #{new_id} ({wc} words)"
            msg += " and synced to OneDrive." if ONEDRIVE_AVAILABLE else "."
            st.success(msg)
            st.rerun()

# ── TAB 4: Polish ──────────────────────────────────────────────────────────────

with tab_polish:
    st.markdown("### Polish a block for a specific funder")
    st.markdown('<div class="hint">Claude rewrites any block tuned to a specific funder\'s '
                'priorities and word count.</div>', unsafe_allow_html=True)

    if not api_key:
        st.markdown('<div class="warn">⚠ API key not set.</div>', unsafe_allow_html=True)

    all_blocks    = get_blocks()
    block_options = {f"[{b['id']}] {b['title']}": b for b in all_blocks}
    selected_key  = st.selectbox("Select a block", list(block_options.keys()))
    selected_block = block_options[selected_key]

    st.text_area("Original text", value=selected_block["content"],
                 height=110, disabled=True, label_visibility="collapsed")
    st.caption(f"{len(selected_block['content'].split())} words · {selected_block['category']}")

    c1, c2 = st.columns(2)
    with c1:
        polish_funder  = st.text_input("Funder name")
        polish_program = st.text_input("Grant/program")
    with c2:
        polish_words = st.number_input("Target word count", 20, 500,
                                       value=len(selected_block["content"].split()))
        polish_notes = st.text_input("Special emphasis for this funder")

    if st.button("✨ Polish with Claude", disabled=not api_key):
        if not polish_funder:
            st.error("Please enter a funder name.")
        else:
            with st.spinner(f"Tailoring for {polish_funder}..."):
                try:
                    polished = polish_with_claude(
                        selected_block["content"], polish_funder,
                        polish_program, polish_words, polish_notes, api_key,
                    )
                    st.session_state.polished_text = polished
                except Exception as e:
                    st.error(f"Polish failed: {e}")

    if st.session_state.polished_text:
        st.markdown("#### Polished version")
        polished_edit = st.text_area("Edit as needed", value=st.session_state.polished_text,
                                     height=180, label_visibility="collapsed")
        st.caption(f"{len(polished_edit.split())} words")

        if st.button("💾 Save polished version as new block"):
            new_id = add_block(
                selected_block["category"],
                f"{selected_block['title']} — tailored for {polish_funder}",
                selected_block.get("tags",""),
                polished_edit,
                f"Tailored from block #{selected_block['id']} for {polish_funder} / {polish_program}",
            )
            msg = f"✅ Saved as block #{new_id}"
            msg += " and synced to OneDrive." if ONEDRIVE_AVAILABLE else "."
            st.success(msg)
            st.session_state.polished_text = ""
            st.rerun()
