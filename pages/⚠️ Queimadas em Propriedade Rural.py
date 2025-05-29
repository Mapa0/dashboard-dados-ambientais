import streamlit as st
import leafmap.foliumap as leafmap
import folium
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
import altair as alt
import json
import re
from shapely.geometry import Point, Polygon, LineString, shape
import random


from fastkml import kml, Placemark

def generate_fake_df(poly, n=10):
    """
    Gera um DataFrame com n pontos aleatórios dentro de `poly`,
    no formato exigido.
    """
    minx, miny, maxx, maxy = poly.bounds  # lon_min, lat_min, lon_max, lat_max
    records = []
    for i in range(n):
        # sortea até cair dentro do polígono
        while True:
            lon = random.uniform(minx, maxx)
            lat = random.uniform(miny, maxy)
            if poly.contains(Point(lon, lat)):
                break

        registro = {
            'id': i + 1,
            'lat': lat,
            'lon': lon,
            'data_hora_gmt': (datetime.utcnow() - timedelta(days=random.randint(0,5))
                              ).strftime('%Y-%m-%d %H:%M:%S'),
            'satelite': random.choice(['Aqua', 'Terra']),
            'municipio': 'MunicípioFake',
            'estado': 'EstadoFake',
            'pais': 'Brasil',
            'municipio_id': random.randint(1000, 9999),
            'estado_id': random.randint(10, 99),
            'pais_id': 105,
            'numero_dias_sem_chuva': random.randint(0, 30),
            'precipitacao': round(random.uniform(0, 100), 2),
            'risco_fogo': random.choice([0, 1, 2, 3]),
            'bioma': random.choice(['Cerrado', 'Pantanal']),
            'frp': round(random.uniform(0, 500), 2),
            'estado_sigla': 'EF',
            'municipio_siglaUF': 'MunicípioFake-EF',
        }
        records.append(registro)

    return pd.DataFrame.from_records(records)


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

def generate_map_with_polygon_and_hotspots(folium_coords, df):
    # folium_coords já é: [(lat1, lon1), (lat2, lon2), ...]
    lats = [pt[0] for pt in folium_coords]
    lons = [pt[1] for pt in folium_coords]
    centroid = [sum(lats) / len(lats), sum(lons) / len(lons)]

    st.subheader("📍 Visualização do Polígono da Propriedade e Focos de Incêndio")
    m = leafmap.Map(center=centroid, zoom=10)

    # desenha o polígono diretamente
    folium.Polygon(
        locations=folium_coords,
        color="green",
        weight=2,
        fill=True,
        fill_color="green",
        fill_opacity=0.3,
    ).add_to(m)

    # plota os focos
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

    m.to_streamlit(
        height=700,
        scrolling=False,
        add_layer_control=False,
    )

def process_df_on_polygon(poly,df):
    df = df.copy()
    df['dentro'] = df.apply(
        lambda row: poly.contains(Point(row['lon'], row['lat'])),
        axis=1
    )
    return df

def extract_placemarks(features):
    """
    Dada uma lista de features (Document, Folder, Placemark, etc),
    retorna uma lista plana de todos os Placemarks encontradas recursivamente.
    """
    pms = []
    for fea in features:
        if isinstance(fea, Placemark):
            pms.append(fea)
        # todo objeto que tenha .features() pode conter Placemarks dentro
        elif hasattr(fea, "features"):
            pms.extend(extract_placemarks(list(fea.features)))
    return pms

def handle_manual_input():
    raw = st.text_area(
        "Cole aqui a lista de coordenadas do polígono:",
        value='[[-16.40, -58.50],[-16.40, -52.10],[-23.60, -52.10],'
            '[-23.60, -58.50],[-16.40, -58.50]]',
        height=100,
    )
    try:
        latlon = json.loads(raw)
        # 2. Cria shapely Polygon em (lon, lat)
        poly = Polygon([(lon, lat) for lat, lon in latlon])
        # 3. Mantém lista de (lat, lon) para o seu map
        folium_coords = latlon
        st.success("✅ Polígono manual normalizado com sucesso")
    except Exception as e:
        st.error(f"Falha no parse do JSON: {e}")
        st.stop()
    
    return poly,folium_coords

def handle_kml_input():
    uploaded = st.file_uploader("Faça upload do seu KML", type="kml")
    if not uploaded:
        st.stop()

    content = uploaded.read().decode("utf-8")
    content = re.sub(r'^\s*<\?xml[^>]+\?>\s*', "", content)
    content = re.sub(
        r'<kml[^>]*xmlns="[^"]+"',
        '<kml xmlns="http://www.opengis.net/kml/2.2"',
        content,
        count=1
    )
    k = kml.KML.from_string(content)

    root_feats = list(k.features)
    placemarks = extract_placemarks(root_feats)

    if not placemarks:
        st.error("Nenhuma trilha/polígono encontrada neste KML.")
        st.stop()

    valid_items = []
    for pm in placemarks:

        geom = pm.geometry
        raw = list(geom.coords)

        if len(raw) <= 1:
            continue

        shp = shape(pm.geometry)  # converte para shapely

        if shp.geom_type == "LineString" and shp.is_ring:
            shp = shape(pm.geometry)
            coords = list(shp.coords)
            poly = Polygon([(lon, lat) for lon, lat, *_ in coords])
            folium_coords = [(lat, lon) for lon, lat, *_ in coords]
            valid_items.append((pm,poly,folium_coords))

    if not valid_items:
        st.error("Nenhum polígono (anel fechado) encontrado neste KML.")
        st.stop()

    valid_items.sort(key=lambda tpl: tpl[1].area, reverse=True)
    ring_pms, ring_polys, folium_coords = zip(*valid_items)
    ring_names = [pm.name or "<sem nome>" for pm in ring_pms]

    escolha = st.selectbox("Selecione um polígono válido", ring_names, index=0)
    idx = ring_names.index(escolha)
    poly = ring_polys[idx]
    folium_coord = folium_coords[idx]

    st.success(f"✅ Polígono `{escolha}` selecionado!")
    return poly, folium_coord

def parameter_input():
    st.subheader("🔧 Definição")
    date = st.date_input("Selecione uma data", value=pd.to_datetime(datetime.now().date()) - timedelta(days=1))

    # 1) Fonte
    fonte = st.radio("De onde vem o polígono?", ["Manual (input de texto)", "Do KML"])

    # depois de st.radio(…)
    poly = None
    folium_coords = None

    if fonte == "Manual (input de texto)":
        poly,folium_coords = handle_manual_input()

    else:  # fonte == "Do KML"
        poly, folium_coords = handle_kml_input()

    return date,poly,folium_coords

def create_dataframe(date):
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

    return df

def page_layout_base():
    st.set_page_config(layout="wide")

    markdown = """
    Projeto dados do Pantanal.
    """

    st.sidebar.title("Sobre nós")
    st.sidebar.info(markdown)
    logo = "https://www.ufms.br/wp-content/uploads/2015/11/ufms_logo_assinatura_vertical_positiva.png"
    st.sidebar.image(logo)

    st.title("⚠️ Queimadas em Propriedade Rural")

def metrics(df,poly):
    df = process_df_on_polygon(poly, df)
    count = int(df['dentro'].sum())
    st.subheader("📊 Incêndios ativos na área")
    st.metric(label="Número de focos detectados", value=count)

def main_content():
    col1, col2 = st.columns([1, 3])
    with col1:
        date,poly,folium_coords = parameter_input()
        df = create_dataframe(date)
        #df = generate_fake_df(poly,100)
    with col2:
        generate_map_with_polygon_and_hotspots(folium_coords, df)
    metrics(df,poly)

page_layout_base()
main_content()