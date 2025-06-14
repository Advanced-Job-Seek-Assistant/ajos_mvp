# streamlit: name = ℹ️ About / Info
# streamlit: icon = ℹ️

import streamlit as st


st.title("About AJOS")

st.markdown("""
**AJOS (Advanced JOb Search)** is a project designed to help users explore and analyze historical job posting data from the Swedish Public Employment Service ([Arbetsförmedlingen](https://arbetsformedlingen.se/)). Our platform utilizes open data covering the years 2020 to 2024.
""")

st.header("What We Offer")

# - **Track how employer requirements have shifted** over time

st.markdown("""
While up-to-date job vacancies can be found on specialized job boards and directly on [Arbetsförmedlingen’s official site](https://arbetsformedlingen.se/), AJOS provides a unique opportunity to explore **trends and patterns** in the Swedish job market over recent years. Our focus is not on exact numbers, but on highlighting how professions have evolved and how demand has changed.

With AJOS, you can:
- **Analyze trends** for specific professions over the past few years
- **Compare the number of published job postings** between two different professions

AJOS is a resource for job seekers, researchers, and anyone interested in the Swedish labor market’s development.
""")

st.markdown("""
If you have any questions or suggestions, feel free to contact us at: [contact@ajos.pro](mailto:contact@ajos.pro).
""")
