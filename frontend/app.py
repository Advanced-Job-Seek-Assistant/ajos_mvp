import streamlit as st

st.set_page_config(
    page_title="Swedish Job Analytics MVP",
    layout="wide",
)

st.title("Swedish Labor Market Analytics MVP")

# --- OPTIONAL: Logo or banner image (убери или замени путь) ---
# st.image("logo.png", width=180, caption="Swedish Job Analytics")  # если нет картинки — просто закомментируй

st.markdown("""
Welcome!

Explore Swedish job market trends 2020–2024.
Choose an action below:
""")

# --- Page links (Streamlit 1.32+ only) ---
st.page_link("pages/1_Single_Search.py", label="🔎 Individual Search", icon="🔎")
st.page_link("pages/2_Compare.py", label="🔀 Compare Professions", icon="🔀")
st.page_link("pages/3_About.py", label="ℹ️ About / Info", icon="ℹ️")

# --- Media block (optional, remove if not needed) ---
st.markdown("---")
# st.image("team_photo.jpg", caption="Our team at Demo Day")
# st.video("demo_video.mp4")  # вставь свой файл или URL

# --- About/Contact section ---
st.markdown("""
---
Created by **AJOS Team**, 2025  
Contact: [ajos@example.com](mailto:contact@ajos.com)
""")
