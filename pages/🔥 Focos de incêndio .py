import streamlit as st
import leafmap.foliumap as leafmap
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO

def get_data_from_inpe(date):
    date = date.strftime('%Y%m%d')
    
    # Construa a URL com base na data
    url = f'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_{date}.csv'
    
    # Tente fazer o download do arquivo
    response = requests.get(url)
    if response.status_code == 200:
        # Carregue o conteúdo CSV em um DataFrame do Pandas
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        if not df.empty:
            return df
        else:
            return pd.DataFrame()  # Retorna um DataFrame vazio se não houver dados
    else:
        print("Erro ao acessar a URL:", response.status_code)
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de falha na solicitação

st.set_page_config(layout="wide")

markdown = """
Projeto dados do Pantanal.
"""

st.sidebar.title("Sobre nós")
st.sidebar.info(markdown)
logo = "https://www.ufms.br/wp-content/uploads/2015/11/ufms_logo_assinatura_vertical_positiva.png"
st.sidebar.image(logo)

st.title("🔥 Focos de incêndio - INPE")

date = st.date_input("Selecione uma data", value=pd.to_datetime(datetime.now().date()) - timedelta(days=1))

option = st.selectbox(
    "Qual métrica você deseja analisar?",
    ("Intensidade do incêndio", "Quantidade de dias sem chuva", "Risco de fogo"),
)

radius = st.slider("Defina um raio de agregação:", 5, 50, 10)


options_map = {
    "Intensidade do incêndio": "frp",
    "Quantidade de dias sem chuva": "numero_dias_sem_chuva",
    "Risco de fogo": "risco_fogo"
}

df = get_data_from_inpe(date)
df = df.dropna(subset=[options_map[option]])

estado_siglas = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPÁ": "AP", "AMAZONAS": "AM", "BAHIA": "BA", 
    "CEARÁ": "CE", "DISTRITO FEDERAL": "DF", "ESPÍRITO SANTO": "ES", "GOIÁS": "GO", 
    "MARANHÃO": "MA", "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG", 
    "PARÁ": "PA", "PARAÍBA": "PB", "PARANÁ": "PR", "PERNAMBUCO": "PE", "PIAUÍ": "PI", 
    "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS", 
    "RONDÔNIA": "RO", "RORAIMA": "RR", "SANTA CATARINA": "SC", "SÃO PAULO": "SP", 
    "SERGIPE": "SE", "TOCANTINS": "TO"
}
df['estado_sigla'] = df['estado'].map(estado_siglas)
df['municipio_siglaUF'] = df['municipio'].str.title() + '-' + df['estado_sigla']

st.subheader(f"Mapa de calor ({option}):")
m = leafmap.Map(center=[-10.91, -51.0641], zoom=4)
m.add_heatmap(
data=df,
latitude="lat",
longitude="lon",
value=options_map[option],
name=option,
radius=radius,
)
m.to_streamlit(height=700, scrolling=False, add_layer_control=False)

quantidade_total_focos = df.shape[0]

municipio_mais_focos = df['municipio_siglaUF'].value_counts().idxmax()
quantidade_focos_municipio = df['municipio_siglaUF'].value_counts().max()

municipio_maior_metrica = df.groupby('municipio_siglaUF')[options_map[option]].sum().idxmax()
metrica_municipio = df.groupby('municipio_siglaUF')[options_map[option]].sum().max()

bioma_maior_metrica = df.groupby('bioma')[options_map[option]].sum().idxmax()
metrica_bioma = df.groupby('bioma')[options_map[option]].sum().max()

bioma_mais_focos = df['bioma'].value_counts().idxmax()
quantidade_focos_bioma = df['bioma'].value_counts().max()

focos_por_bioma = df.groupby('bioma').size().reset_index(name='Quantidade de Focos')

st.metric(label=f"Focos de incêndios totais", value=quantidade_total_focos)
col1, col2 = st.columns(2)
with col1:
    st.metric(label=f"Município com mais focos de incêndio", value=municipio_mais_focos, delta=str(quantidade_focos_municipio), delta_color="off")
    st.metric(label=f"Município com maior {option.lower()}", value=municipio_maior_metrica, delta=str(metrica_municipio), delta_color="off")
with col2:
    st.metric(label=f"Bioma com mais focos de incêndio", value=bioma_mais_focos, delta=str(quantidade_focos_bioma), delta_color="off")
    st.metric(label=f"Bioma com maior {option.lower()}", value=bioma_maior_metrica, delta=str(metrica_bioma), delta_color="off")

st.table(focos_por_bioma.to_dict(orient='records'))