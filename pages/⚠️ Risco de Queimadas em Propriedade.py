import streamlit as st
import leafmap.foliumap as leafmap
import folium
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
import altair as alt
import json
from shapely.geometry import Point, Polygon

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

def generate_map_with_polygon_and_hotspots(polygon_value, df):
    # 1. Parse do polígono e cálculo do centroide
    coords = json.loads(polygon_value)
    lats = [pt[0] for pt in coords]
    lons = [pt[1] for pt in coords]
    centroid = [sum(lats) / len(lats), sum(lons) / len(lons)]

    st.subheader("📍 Visualização do Polígono da Propriedade e Focos de Incêndio")

    # 2. Cria o mapa já centralizado e com zoom adequado
    m = leafmap.Map(center=centroid, zoom=10)

    # 3. Desenha o polígono
    try:
        folium.Polygon(
            locations=coords,
            color="green",
            weight=2,
            fill=True,
            fill_color="green",
            fill_opacity=0.3,
        ).add_to(m)
    except Exception as e:
        st.error(f"❌ Erro ao desenhar o polígono: {e}")

    # 4. Plota os focos de incêndio como círculos vermelhos
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=1,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.3,
            popup=f"Data: {row['data_hora_gmt']}\nRisco: {row['risco_fogo']}"
        ).add_to(m)

    # 5. Renderiza no Streamlit
    m.to_streamlit(
        height=700,
        scrolling=False,
        add_layer_control=False,
    )

def process_df_on_polygon(polygon_value,df):
    # 1. Converte o JSON string em lista de [lat, lon]
    coords = json.loads(polygon_value)
    # 2. Inverte para (lon, lat) e monta uma lista de tuplas
    poly_coords = [(lon, lat) for lat, lon in coords]
    # 3. Cria o Polygon corretamente
    poly = Polygon(poly_coords)
    # 4. Testa cada ponto do df
    df = df.copy()
    df['dentro'] = df.apply(
        lambda row: poly.contains(Point(row['lon'], row['lat'])),
        axis=1
    )
    return df

st.set_page_config(layout="wide")

markdown = """
Projeto dados do Pantanal.
"""

st.sidebar.title("Sobre nós")
st.sidebar.info(markdown)
logo = "https://www.ufms.br/wp-content/uploads/2015/11/ufms_logo_assinatura_vertical_positiva.png"
st.sidebar.image(logo)

st.title("⚠️ Risco de Queimadas em Propriedade")

date = st.date_input("Selecione uma data", value=pd.to_datetime(datetime.now().date()) - timedelta(days=1))

polygon_input = st.text_area(
    "Cole aqui a lista de coordenadas do polígono:",
    value = '[[-16.40, -58.50],[-16.40, -52.10],[-23.60, -52.10],[-23.60, -58.50],[-16.40, -58.50]]',
    height=100,
)

radius = st.slider("Defina um raio de agregação:", 5, 50, 10)

df = get_data_from_inpe(date)

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

generate_map_with_polygon_and_hotspots(polygon_input, df)

df = process_df_on_polygon(polygon_input, df)

count = int(df['dentro'].sum())

st.subheader("📊 Incêndios ativos na área")
st.metric(label="Número de focos detectados", value=count)