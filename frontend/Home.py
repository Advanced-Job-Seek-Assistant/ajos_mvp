# streamlit: name = 🏠 Home
# streamlit: icon = 🏠

import streamlit as st

st.set_page_config(
    page_title="Advanced Job Search",
    layout="wide",
)

st.title("Swedish Labor Market Analytics")

st.markdown("""
Welcome to AJOS! This is the **A**dvanced **JO**b **S**earch assistant.

Explore Swedish job market trends 2020–2024. \n
Choose an action below:
""")

# --- Page links (Streamlit 1.32+ only) ---
st.page_link("pages/1_Single_Search.py", label="Individual Search", icon="🔎")
st.page_link("pages/2_Compare.py", label="Compare Professions", icon="🔀")
st.page_link("pages/3_About.py", label="About / Info", icon="ℹ️")

# --- Media block (optional, remove if not needed) ---
st.markdown("---")
# st.image("team_photo.jpg", caption="Our team at Demo Day")
# st.video("demo_video.mp4")

# --- About/Contact section ---
st.markdown("""
---
Created by **AJOS Team**, 2025  
Contact: [contact@ajos.com](mailto:contact@ajos.com)
""")
