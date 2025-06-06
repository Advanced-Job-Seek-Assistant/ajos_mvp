import pandas as pd
import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.title("Swedish Job Analytics MVP")
st.markdown("#### Find job posting dynamics by profession (2020-2024)")

query = st.text_input("Job title (in English)", "")

# --- Session state for refine logic and data ---
if "refine_suggestions" not in st.session_state:
    st.session_state["refine_suggestions"] = None
if "refine_query" not in st.session_state:
    st.session_state["refine_query"] = ""
if "allow_raw_search" not in st.session_state:
    st.session_state["allow_raw_search"] = False
if "search_data" not in st.session_state:
    st.session_state["search_data"] = None
if "last_query" not in st.session_state:
    st.session_state["last_query"] = ""


def run_search(query, refined=False):
    """Send request to backend /search endpoint and handle refine logic"""
    with st.spinner("Searching..."):
        try:
            resp = requests.get(f"{API_URL}/search", params={"query": query.strip(), "refined": refined})
            data = resp.json()
            if data.get("need_refine"):
                st.session_state["refine_suggestions"] = data.get("suggestions", [])
                st.session_state["refine_query"] = data.get("original_query", query)
                st.session_state["allow_raw_search"] = data.get("allow_raw_search", True)
                st.session_state["search_data"] = None
                st.session_state["last_query"] = ""
                return  # Stop further processing
            # If regular results
            if "dynamics" in data and data["dynamics"]:
                st.session_state["search_data"] = pd.DataFrame(data["dynamics"])
                st.session_state["search_data"] = st.session_state["search_data"].sort_values("week")
                st.session_state["last_query"] = query.strip()
                st.session_state["refine_suggestions"] = None
                st.session_state["refine_query"] = ""
                st.session_state["allow_raw_search"] = False
            else:
                st.session_state["search_data"] = None
                st.session_state["last_query"] = query.strip()
                st.session_state["refine_suggestions"] = None
                st.session_state["refine_query"] = ""
                st.session_state["allow_raw_search"] = False
                st.info(f'No vacancies found for "{query}"')
        except Exception as e:
            st.session_state["search_data"] = None
            st.session_state["last_query"] = query.strip()
            st.session_state["refine_suggestions"] = None
            st.session_state["refine_query"] = ""
            st.session_state["allow_raw_search"] = False
            st.error(f"API error: {e}")

def show_refine_block():
    st.warning(f'Your query **"{st.session_state["refine_query"]}"** is too general. Please clarify:')
    option = st.radio(
        "Select the most relevant profession:",
        st.session_state["refine_suggestions"],
        key="refine_option"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Search this profession", key="refine_select"):
            # Use only the English part before the first " ("
            query_en = option.split(" (")[0]
            run_search(query_en, refined=True)
            # Reset refine state
            st.session_state["refine_suggestions"] = None
            st.session_state["refine_query"] = ""
            st.session_state["allow_raw_search"] = False
            st.rerun()
    with col2:
        if st.session_state.get("allow_raw_search", False):
            if st.button("Search as is", key="refine_raw"):
                run_search(st.session_state["refine_query"], refined=True)
                st.session_state["refine_suggestions"] = None
                st.session_state["refine_query"] = ""
                st.session_state["allow_raw_search"] = False
                st.rerun()

# --- MAIN SEARCH ACTION ---
if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a job title!")
    else:
        run_search(query, refined=False)

# --- REFINEMENT FLOW ---
if st.session_state.get("refine_suggestions"):
    st.warning("Your query is too general. Please clarify:")
    options = st.session_state["refine_suggestions"] + ["Other..."]
    option = st.radio("Pick a profession to search:", options, key="refine_radio_option")

    custom_value = ""
    if option == "Other...":
        custom_value = st.text_input("Or enter your own profession:", key="refine_custom_input")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Search this profession"):
            if option == "Other...":
                if custom_value.strip():
                    run_search(custom_value.strip(), refined=True)
                    # <--- Вот здесь сбрось refine state до rerun
                    st.session_state["refine_suggestions"] = None
                    st.session_state["refine_query"] = ""
                    st.session_state["allow_raw_search"] = False
                    st.rerun()
                else:
                    st.warning("Please enter a profession!")
            else:
                run_search(option.split(" (")[0], refined=True)
                # <--- Вот здесь сбрось refine state до rerun
                st.session_state["refine_suggestions"] = None
                st.session_state["refine_query"] = ""
                st.session_state["allow_raw_search"] = False
                st.rerun()
    with col2:
        if st.session_state.get("allow_raw_search", False):
            if st.button("Search as is"):
                run_search(st.session_state["refine_query"], refined=True)
                # <--- Вот здесь сбрось refine state до rerun
                st.session_state["refine_suggestions"] = None
                st.session_state["refine_query"] = ""
                st.session_state["allow_raw_search"] = False
                st.rerun()
    st.stop()

# --- CHARTS IF DATA LOADED ---
if st.session_state["search_data"] is not None:
    group_by = st.radio(
        "Group by:",
        options=["Weeks", "Months"],
        index=0,
        horizontal=True
    )
    df = st.session_state["search_data"]
    if group_by == "Months":
        # Convert "YYYY-WW" to the first day of the week, then extract month
        df["week_start"] = pd.to_datetime(df["week"] + "-1", format="%G-%V-%u")
        df["month"] = df["week_start"].dt.strftime("%Y-%m")
        df_month = df.groupby("month", as_index=True)["count"].sum()
        df_month = df_month.to_frame()
        df_month["count"] = pd.to_numeric(df_month["count"], errors="coerce")
        df_month = df_month.dropna(subset=["count"])
        st.bar_chart(df_month, use_container_width=True)
        st.success(f'Found {df_month["count"].sum()} vacancies for "{st.session_state["last_query"]}" (by month)')
    else:
        smooth = st.checkbox("Smooth (moving average, 3 weeks)", value=True)
        window_size = 3
        df_plot = df[["week", "count"]].copy()
        df_plot["count"] = pd.to_numeric(df_plot["count"], errors="coerce")
        df_plot = df_plot.dropna(subset=["count"])
        df_plot = df_plot.set_index("week")
        if smooth:
            df_plot["smoothed"] = df_plot["count"].rolling(window=window_size, min_periods=1, center=True).mean()
            st.line_chart(df_plot[["smoothed"]], use_container_width=True)
            st.success(f'Found {df_plot["count"].sum()} vacancies for "{st.session_state["last_query"]}" (by week, smoothed)')
        else:
            st.line_chart(df_plot[["count"]], use_container_width=True)
            st.success(f'Found {df_plot["count"].sum()} vacancies for "{st.session_state["last_query"]}" (by week)')
