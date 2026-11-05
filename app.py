import streamlit as st
from pathlib import Path
from src.ingestion.loader import load_source
from src.llm.factory import build_provider, PROVIDERS
from src.analysis.pipeline import build_analysis_prompt, build_document_prompt
from src.citations.validator import validate_document
from src.generators.render import render_document, number_lines_for_display, format_invalid_citations

st.set_page_config(page_title="Code Intelligence - DataBricks", page_icon="🧠", layout="wide")
st.title("Code Intelligence - DataBricks")
st.caption("Understand Databricks notebooks with evidence-backed documentation.")

with st.sidebar:
    st.header("LLM configuration")
    provider_name = st.selectbox("Provider", list(PROVIDERS.keys()))
    model = st.text_input("Model", value=PROVIDERS[provider_name]["default_model"])
    st.caption(PROVIDERS[provider_name]["hint"])
    st.info("API keys are read from environment variables. They are never stored in the app.")

uploaded = st.file_uploader("Upload Databricks source", type=["py", "ipynb", "sql", "txt"])
if uploaded:
    raw = uploaded.getvalue()
    try:
        source = load_source(uploaded.name, raw)
    except Exception as exc:
        st.error(f"Could not parse this file: {exc}")
        st.stop()

    st.success(f"Loaded {uploaded.name}: {len(source['cells'])} cell(s), {source['line_count']} source line(s).")
    with st.expander("Preview parsed source"):
        for cell in source["cells"]:
            st.markdown(f"**Cell {cell['cell_id']} · {cell['language']}**")
            st.code(number_lines_for_display(cell["code"]), language=cell["language"].lower() if cell["language"].lower() in ("python","sql","scala","r") else "text")

    if st.button("Analyze and generate documents", type="primary", use_container_width=True):
        try:
            llm = build_provider(provider_name, model)
            with st.spinner(f"Analyzing with {provider_name} / {model}..."):
                analysis_prompt = build_analysis_prompt(source)
                analysis_text = llm.generate(analysis_prompt, system="You are a careful code analyst. Ground every factual statement in supplied source.")
                st.session_state["analysis"] = analysis_text
                docs = {}
                for audience in ("business", "developer", "agent"):
                    prompt = build_document_prompt(source, analysis_text, audience)
                    docs[audience] = llm.generate(prompt, system="Write precise documentation. Never invent code behavior or source locations.")
                st.session_state["docs"] = docs
                st.session_state["source"] = source
                st.session_state["filename"] = uploaded.name
        except Exception as exc:
            st.error(f"Generation failed: {exc}")
            st.stop()

if "docs" in st.session_state:
    st.subheader("Generated documentation")
    labels = {
        "business": "Business understanding",
        "developer": "Developer documentation",
        "agent": "AI coding agent guide",
    }
    tabs = st.tabs([labels[k] for k in labels])
    for tab, key in zip(tabs, labels):
        with tab:
            doc = st.session_state["docs"][key]
            result = validate_document(doc, st.session_state["source"])
            if result["invalid"]:
                st.warning(f"{len(result['invalid'])} citation(s) could not be verified. Review or correct them before relying on the document.")
                st.markdown(format_invalid_citations(result["invalid"]))
            else:
                st.success("All detected citations point to valid source locations.")
            st.markdown(render_document(doc, st.session_state["source"]))
            st.download_button(
                "Download Markdown",
                data=doc,
                file_name=f"{Path(st.session_state['filename']).stem}_{key}.md",
                mime="text/markdown",
                key=f"download_{key}",
            )
    with st.expander("Citation source viewer"):
        source = st.session_state["source"]
        cell_ids = [str(c["cell_id"]) for c in source["cells"]]
        selected = st.selectbox("Cell", cell_ids)
        cell = next(c for c in source["cells"] if str(c["cell_id"]) == selected)
        st.code(number_lines_for_display(cell["code"]), language=cell["language"].lower() if cell["language"].lower() in ("python","sql","scala","r") else "text")
        st.caption("Citation format: [Cell N, lines X-Y]. The number before each \"|\" is the line number used in citations.")

st.divider()
st.caption("Local-first application. Uploaded code is sent only to the selected provider when cloud inference is used. Use Ollama for local inference.")
