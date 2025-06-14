# streamlit: name = 🔎 Individual Search
# streamlit: icon = 🔎

import pandas as pd
import streamlit as st
import requests
import os
from dotenv import load_dotenv
import altair as alt

X_TICKS_STEP = 4

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

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
if "query_text" not in st.session_state:
    st.session_state["query_text"] = ""

# --- Apply pending_query_text to query_text before widget creation ---
if "pending_query_text" in st.session_state:
    st.session_state["query_text"] = st.session_state.pop("pending_query_text")

st.title("Job Postings Analytics")
st.markdown("#### Find job posting dynamics by profession (2020-2024)")

# --- Main text input, bound to session_state
query = st.text_input("Job title (in English)", value=st.session_state["query_text"], key="query_text")

def run_search(query, refined=False):
    """Send request to backend /search endpoint and handle refine logic."""
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
                return
            if "dynamics" in data and data["dynamics"]:
                st.session_state["search_data"] = pd.DataFrame(data["dynamics"])
                st.session_state["search_data"] = st.session_state["search_data"].sort_values("week")
                st.session_state["last_query"] = query.strip()
                # Field will be updated on rerun if needed, don't set here!
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

# --- MAIN SEARCH ACTION ---
if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a job title!")
    else:
        st.session_state["pending_query_text"] = query.strip()  # ensure field always updates
        run_search(query, refined=False)
        st.rerun()

# --- REFINEMENT FLOW ---
if st.session_state.get("refine_suggestions"):
    st.warning(f'Your query "{st.session_state["refine_query"]}" is too general. Please clarify:')
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
                    st.session_state["pending_query_text"] = custom_value.strip()  # Set new field value for rerun
                    run_search(custom_value.strip(), refined=True)
                    st.session_state["refine_suggestions"] = None
                    st.session_state["refine_query"] = ""
                    st.session_state["allow_raw_search"] = False
                    st.rerun()
                else:
                    st.warning("Please enter a profession!")
            else:
                refined_value = option.split(" (")[0]
                st.session_state["pending_query_text"] = refined_value  # Set new field value for rerun
                run_search(refined_value, refined=True)
                st.session_state["refine_suggestions"] = None
                st.session_state["refine_query"] = ""
                st.session_state["allow_raw_search"] = False
                st.rerun()
    with col2:
        if st.session_state.get("allow_raw_search", False):
            if st.button("Search as is"):
                st.session_state["pending_query_text"] = st.session_state["refine_query"]
                run_search(st.session_state["refine_query"], refined=True)
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
        # Convert ISO week to date, then extract month
        df["week_start"] = pd.to_datetime(df["week"] + "-1", format="%G-%V-%u")
        df["month"] = df["week_start"].dt.strftime("%Y-%m")

        # Aggregate counts by month
        df_month = df.groupby("month", as_index=False)["count"].sum()
        df_month["count"] = pd.to_numeric(df_month["count"], errors="coerce")
        df_month = df_month.dropna(subset=["count"])

        # Create label column: show only every 2nd label
        df_month["x_label"] = df_month["month"]
        df_month.loc[df_month.index % X_TICKS_STEP != 0, "x_label"] = ""  # Empty for odd indexes

        # Build chart
        chart = alt.Chart(df_month).mark_line().encode(
                x=alt.X(
                    "x_label:N",
                    title="Month",
                    axis=alt.Axis(labelAngle=45)  # Rotate X-axis labels
                ),
                y=alt.Y("count:Q", title="Number of Vacancies"),
                tooltip=["month", "count"]
            ).properties(
                width='container',
                height=400
            )

        st.altair_chart(chart, use_container_width=True)
        st.success(f'Found {df_month["count"].sum()} vacancies for "{st.session_state["last_query"]}" (by month)')

    else:
        # Smooth weekly counts
        window_size = 3
        df_plot = df[["week", "count"]].copy()
        df_plot["count"] = pd.to_numeric(df_plot["count"], errors="coerce")
        df_plot = df_plot.dropna(subset=["count"])
        df_plot["smoothed"] = df_plot["count"].rolling(window=window_size, min_periods=1, center=True).mean()
        df_plot = df_plot.reset_index(drop=True)

        # Create label column for x-axis
        df_plot["x_label"] = df_plot["week"]
        df_plot.loc[df_plot.index % X_TICKS_STEP != 0, "x_label"] = ""

        # Build chart
        chart = alt.Chart(df_plot).mark_line().encode(
            x=alt.X(
                "x_label:N", 
                title="Week", 
                axis=alt.Axis(labelAngle=45) # Rotate X-axis labels
            ),  
            y=alt.Y("smoothed:Q", title="Number of Vacancies"),
            tooltip=["week", "smoothed"]
        ).properties(
            width='container',
            height=400
        )

        st.altair_chart(chart, use_container_width=True)
        st.success(f'Found {df_plot["count"].sum()} vacancies for "{st.session_state["last_query"]}" (by week, smoothed)')