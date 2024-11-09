import streamlit as st
import leafmap.foliumap as leafmap

st.set_page_config(layout="wide")

markdown = """Marcos Paulo Paolino\n\n
Giovanna Oliveira
"""

st.sidebar.title("Projeto Integrador I")
st.sidebar.info(markdown)
logo = "https://www.ufms.br/wp-content/uploads/2015/11/ufms_logo_assinatura_vertical_positiva.png"
st.sidebar.image(logo)

st.title("Análise de dados abertos referente ao ambiente")