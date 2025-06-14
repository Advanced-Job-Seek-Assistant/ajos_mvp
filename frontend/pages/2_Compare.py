# streamlit: name = 🔀 Compare Professions
# streamlit: icon = 🔀

import pandas as pd
import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.title("Compare Professions (Pair Search)")
st.markdown("#### Compare job posting dynamics for two professions (2020-2024)")

# --- Безопасное обновление значений input-полей через "next" переменные (до объявления полей!) ---
if "cmp_query1_next" in st.session_state:
    st.session_state["cmp_query1"] = st.session_state["cmp_query1_next"]
    del st.session_state["cmp_query1_next"]
if "cmp_query2_next" in st.session_state:
    st.session_state["cmp_query2"] = st.session_state["cmp_query2_next"]
    del st.session_state["cmp_query2_next"]

# --- Session State для refine логики ---
if "cmp_refine_suggestions" not in st.session_state:
    st.session_state["cmp_refine_suggestions"] = [None, None]
if "cmp_refine_query" not in st.session_state:
    st.session_state["cmp_refine_query"] = ["", ""]
if "cmp_allow_raw_search" not in st.session_state:
    st.session_state["cmp_allow_raw_search"] = [False, False]
if "cmp_search_data" not in st.session_state:
    st.session_state["cmp_search_data"] = None
if "cmp_last_queries" not in st.session_state:
    st.session_state["cmp_last_queries"] = ["", ""]
if "cmp_final_queries" not in st.session_state:
    st.session_state["cmp_final_queries"] = ["", ""]
if "cmp_query1" not in st.session_state:
    st.session_state["cmp_query1"] = ""
if "cmp_query2" not in st.session_state:
    st.session_state["cmp_query2"] = ""

col1, col2 = st.columns(2)
with col1:
    query1 = st.text_input("First profession (in English):", key="cmp_query1")
with col2:
    query2 = st.text_input("Second profession (in English):", key="cmp_query2")

def run_multi_search(qs, refined=None):
    with st.spinner("Searching..."):
        if not qs[0].strip() or not qs[1].strip():
            st.warning("Please enter both professions.")
            return
        params = [("queries", qs[0].strip()), ("queries", qs[1].strip())]
        if refined:
            params += [("refined", "true" if refined[0] else "false"), ("refined", "true" if refined[1] else "false")]
        try:
            resp = requests.get(f"{API_URL}/multi_search", params=params)
            data = resp.json()
            if data.get("results"):
                st.session_state["cmp_search_data"] = data["results"]
                st.session_state["cmp_last_queries"] = qs
                st.session_state["cmp_refine_suggestions"] = [None, None]
                st.session_state["cmp_refine_query"] = ["", ""]
                st.session_state["cmp_allow_raw_search"] = [False, False]
                st.session_state["cmp_final_queries"] = qs
                return
            if data.get("need_refine"):
                refine_suggestions = data.get("suggestions", [[], []])
                orig_queries = data.get("original_queries", qs)
                allow_raw = data.get("allow_raw_search", [True, True])
                st.session_state["cmp_refine_suggestions"] = refine_suggestions
                st.session_state["cmp_refine_query"] = orig_queries
                st.session_state["cmp_allow_raw_search"] = allow_raw
                st.session_state["cmp_search_data"] = None
                st.session_state["cmp_last_queries"] = qs
                return
            st.session_state["cmp_search_data"] = None
            st.info("No results found.")
        except Exception as e:
            st.session_state["cmp_search_data"] = None
            st.error(f"API error: {e}")

# --- Refine (уточнение) по каждому запросу независимо ---
refine_suggestions = st.session_state["cmp_refine_suggestions"]
refine_query = st.session_state["cmp_refine_query"]
allow_raw = st.session_state["cmp_allow_raw_search"]
final_queries = st.session_state.get("cmp_final_queries", ["", ""])

# --- Блок уточнения (refine) — ОН ВСЕГДА ПЕРЕД ОСТАЛЬНЫМ! ---
if refine_suggestions and any(refine_suggestions):
    st.warning("At least one of your queries is too general. Please clarify each:")

    need_refine = [False, False]
    refined_queries = [None, None]

    for i in [0, 1]:
        if refine_suggestions[i]:
            need_refine[i] = True
            options = refine_suggestions[i] + ["Other..."]
            selected = st.radio(
                f"Choose for: \"{refine_query[i]}\"", options, key=f"cmp_refine_radio_{i}"
            )
            custom_val = ""
            if selected == "Other...":
                custom_val = st.text_input(
                    "Or enter your own profession:", key=f"cmp_refine_custom_{i}"
                )
            refined_queries[i] = custom_val.strip() if selected == "Other..." else selected.split(" (")[0]
            if refined_queries[i]:
                final_queries[i] = refined_queries[i]
        else:
            final_queries[i] = refine_query[i] or [query1, query2][i]

    st.session_state["cmp_final_queries"] = final_queries

    # Кнопка поиска появляется только если все необходимые уточнения выбраны
    if all(q for i, q in enumerate(final_queries) if need_refine[i]):
        if st.button("Search with these refinements", key="cmp_refine_btn"):
            run_multi_search(final_queries, refined=[need_refine[0], need_refine[1]])
            # --- Сохраняем уточнённые значения в "next", чтобы подставить после rerun ---
            st.session_state["cmp_query1_next"] = final_queries[0]
            st.session_state["cmp_query2_next"] = final_queries[1]
            st.rerun()
    else:
        st.info("Please refine all required queries before searching.")

    # Альтернативная кнопка для поиска "как есть", если разрешено API
    if all(allow_raw) and st.button("Search both as is", key="cmp_refine_raw_btn"):
        run_multi_search(refine_query, refined=[True, True])
        st.session_state["cmp_query1_next"] = refine_query[0]
        st.session_state["cmp_query2_next"] = refine_query[1]
        st.rerun()
    st.stop()

# --- Основная кнопка запуска поиска --- (только если НЕ нужен refine)
if st.button("Compare"):
    st.session_state["cmp_refine_suggestions"] = [None, None]
    st.session_state["cmp_refine_query"] = ["", ""]
    st.session_state["cmp_allow_raw_search"] = [False, False]
    st.session_state["cmp_search_data"] = None
    st.session_state["cmp_final_queries"] = ["", ""]
    run_multi_search([query1, query2], refined=[False, False])
    # --- Сохраняем исходные значения в "next" для input-полей (можно закомментировать, если не надо) ---
    st.session_state["cmp_query1_next"] = query1
    st.session_state["cmp_query2_next"] = query2
    st.rerun()

# --- Графики сравнения, если данные загружены ---
if st.session_state["cmp_search_data"]:
    results = st.session_state["cmp_search_data"]
    st.markdown("### Comparison Chart")
    df1 = pd.DataFrame(results[0]["dynamics"])
    df2 = pd.DataFrame(results[1]["dynamics"])
    df1["week"] = df1["week"].astype(str)
    df2["week"] = df2["week"].astype(str)
    df1.set_index("week", inplace=True)
    df2.set_index("week", inplace=True)
    all_weeks = sorted(set(df1.index) | set(df2.index))
    df1 = df1.reindex(all_weeks).fillna(0)
    df2 = df2.reindex(all_weeks).fillna(0)
    compare_df = pd.DataFrame({
        results[0]["query"]: df1["count"],
        results[1]["query"]: df2["count"]
    }, index=all_weeks)
    st.line_chart(compare_df, use_container_width=True)
    st.success(
        f'Found {int(df1["count"].sum())} vacancies for "{results[0]["query"]}" '
        f'and {int(df2["count"].sum())} for "{results[1]["query"]}".'
    )
