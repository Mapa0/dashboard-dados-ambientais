import streamlit as st
import leafmap.foliumap as leafmap
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import StringIO

def get_data_from_inpe(date):
    # Construa a URL com base na data
    url = f'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_{date}.csv'

    # Tente fazer o download do arquivo
    response = requests.get(url)

    if response.status_code == 200:
        # Carregue o conteúdo CSV em um DataFrame do Pandas
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        if df is not None:
            print("RETORNEISAMERDA")
            return pd.DataFrame(df)
        else:
            print("RETORNEISAPORRA")
            return []

st.set_page_config(layout="wide")

markdown = """
Projeto dados do Pantanal.
"""

st.sidebar.title("Sobre nós")
st.sidebar.info(markdown)
logo = "https://www.ufms.br/wp-content/uploads/2015/11/ufms_logo_assinatura_vertical_positiva.png"
st.sidebar.image(logo)

st.title("🔥 Focos de incêndio por dia")

date = st.date_input("Start Date", value=pd.to_datetime("20241027", format="%Y%m%d"))

df = get_data_from_inpe(date)
print("AEEAEAEEEEE")
print(df)

with st.expander("See source code"):
    with st.echo():
        m = leafmap.Map(center=[40, -100], zoom=4)
        m.add_heatmap(
            data=df,
            latitude="latitude",
            longitude="longitude",
            value="pop_max",
            name="Heat map",
            radius=20,
        )
m.to_streamlit(height=700)
