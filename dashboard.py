import os
from dotenv import load_dotenv

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# ========================================
# CONFIG
# ========================================

# Carrega variáveis do .env (DB_USER, DB_PASS, etc.)
load_dotenv()

# Configurações de conexão (Lembre-se da porta 5436 para acesso externo ao Docker)
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
# DB_NAME = os.getenv("DB_NAME", "airflow_db")
DB_NAME = os.getenv("PROJECT_DB", "nyc_yellow_taxi")
DB_HOST = "localhost"
DB_PORT = "5436"

# Mapeamentos para exibição
VENDOR_LABELS = {1: "Creative Mobile", 2: "VeriFone"}

PAYMENT_LABELS = {
    1: "Cartao de Credito",
    2: "Dinheiro",
    3: "Sem Cobranca",
    4: "Disputa",
    5: "Desconhecido",
    6: "Cancelada",
}

DAY_ORDER = [
    "Segunda-feira",
    "Terca-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sabado",
    "Domingo",
]

# ========================================
# CONEXÃO
# ========================================

@st.cache_resource
def get_engine():
    conn_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(
        url=conn_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )

# ========================================
# QUERY
# ========================================

@st.cache_data(show_spinner="Consultando banco de dados...")
def load_data(filters: dict) -> pd.DataFrame:
    """Executa a query filtrada diretamente no Postgres"""
    engine = get_engine()

    # Query SQL parametrizada para evitar SQL Injection
    # O filtro de IN (:vendors) exige que o parâmetro seja uma tupla
    query = """
        SELECT
            vendor_id,
            vendor_name,
            hour_of_day,
            payment_label,
            day_of_week,

            total_trips,
            total_revenue,
            avg_fare,
            avg_distance,
            avg_tip_amount,
            avg_tip_pct,
            avg_duration,
            avg_speed
        FROM gold_taxi_metrics
        WHERE hour_of_day BETWEEN :start_h AND :end_h
          AND vendor_id = ANY(:vendors)
        ORDER BY hour_of_day
    """

    with engine.connect() as conn:
        df = pd.read_sql(
            text(query),
            conn,
            params={
                "start_h": filters["start_h"],
                "end_h": filters["end_h"],
                "vendors": list(filters["vendors"])
            }
        )

    return df

# ========================================
# FILTROS
# ========================================

def get_filter_values():
    """Captura os valores da sidebar do Streamlit"""
    st.sidebar.header("Filtros Dinâmicos (Postgres)")

    # Filtro de Hora (Slider)
    hour_range = st.sidebar.slider("Faixa de hora", 0, 23, (0, 23))

    # Filtro de Fornecedores (Multi-select)
    # Importante: Para filtrar isso na Gold, a coluna 'vendor_id' deve existir na tabela gold_taxi_metrics
    vendor_options = [1, 2] # IDs padrão do NYC Taxi
    selected_vendors = st.sidebar.multiselect(
        "Fornecedores",
        options=vendor_options,
        default=vendor_options,
        # format_func=lambda x: "VeriFone" if x == 2 else "Creative Mobile"
        format_func=lambda x: VENDOR_LABELS.get(x, str(x))
    )

    return {
        "start_h": hour_range[0],
        "end_h": hour_range[1],
        "vendors": tuple(selected_vendors) if selected_vendors else (1, 2)
    }

# ========================================
# FORMATADORES
# ========================================

def format_currency(value: float) -> str:
    return f"US$ {value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")

def format_usd_millions(value: float) -> str:
    return f"US$ {value/1_000_000:,.2f} Mi".replace(",", "X").replace(".", ",").replace("X", ".")

def format_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")

# ========================================
# APP
# ========================================

def main() -> None:
    st.set_page_config(
        # page_title="NYC Yellow Taxi - Painel ETL",
        page_title="NYC Taxi Dashboard",
        page_icon="🚕",
        layout="wide",
    )

    st.title("🚕 NYC Yellow Taxi Analytics Dashboard")

    st.markdown(
        """
        ### Visão geral do pipeline de dados
        Este dashboard apresenta métricas da operação de táxis de Nova York, processadas via arquitetura **ETL em batch (Bronze → Silver → Gold)**.

        Fluxo de dados:
        **Extração → Limpeza → Transformação → Agregação → Visualização**

        Use os filtros laterais para explorar padrões por hora, fornecedor, tipo de pagamento e dia da semana.
        """
    )

    # 1. Captura os filtros da interface
    filters = get_filter_values()

    # 2. Carrega os dados filtrados direto do banco
    df = load_data(filters=filters)

    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        st.stop()
    
    # ================================
    # KPIs
    # ================================

    # --- Resumo Geral ---
    st.subheader("📊 Indicadores de Performance (KPIs)")
    col1, col2, col3, col4, col5 = st.columns([1, 1.2, 1, 1, 1])

    total_trips = df["total_trips"].sum()
    total_revenue = float(df["total_revenue"].sum())
    avg_fare = float(df["avg_fare"].mean())
    avg_distance = float(df["avg_distance"].mean())
    avg_tip_pct = float(df["avg_tip_pct"].mean())

    col1.metric("Total de corridas", format_int(total_trips))
    col2.metric("Faturamento total (USD)", format_usd_millions(total_revenue))
    col3.metric("Ticket médio por corrida", format_currency(avg_fare))
    col4.metric("Distância média (mi)", f"{avg_distance:.2f}")
    col5.metric("Gorjeta média (%)", f"{avg_tip_pct:.2f}")

    # ================================
    # GRÁFICOS
    # ================================

    tab_hour, tab_vendor, tab_payment, tab_weekday = st.tabs([
        "⏱️ Distribuição por Hora",
        "🚖 Performance por Fornecedor",
        "💳 Análise por Tipo de Pagamento",
        "📅 Padrões por Dia da Semana"
    ])

    # ---------------- HORA ----------------
    with tab_hour:
        st.subheader("⏱️ Padrão de demanda ao longo do dia")
        hourly = (
            df.groupby("hour_of_day", as_index=True)
            .agg(
                total_trips=("total_trips", "sum"),
                total_revenue=("total_revenue", "sum"),
                avg_fare=("avg_fare", "mean"),
                avg_distance=("avg_distance", "mean"),
                avg_tip_pct=("avg_tip_pct", "mean"),
                avg_speed=("avg_speed", "mean"),
                avg_duration=("avg_duration", "mean")
            )
            .sort_index()
            .round(2)
            .rename(
                columns={
                    "total_trips": "Total de viagens",
                    "total_revenue": "Receita total (US$)",
                    "avg_fare": "Tarifa média (US$)",
                    "avg_distance": "Distância média (mi)",
                    "avg_tip_pct": "Gorjeta média (%)",
                    "avg_speed": "Velocidade média (mph)",
                    "avg_duration": "Duração média (min)",
                }
            )
        )

        hourly.index.name = "Hora do dia"

        chart_col1, chart_col2 = st.columns(2)
        chart_col1.line_chart(hourly["Total de viagens"], use_container_width=True)
        chart_col2.bar_chart(hourly["Tarifa média (US$)"], use_container_width=True)
        st.dataframe(hourly, use_container_width=True)

    # ---------------- VENDOR ----------------
    with tab_vendor:
        st.subheader("🚖 Comparativo de desempenho entre fornecedores")
        vendor = (
            df.groupby("vendor_id", as_index=True)
            .agg(
                total_trips=("total_trips", "sum"),
                total_revenue=("total_revenue", "sum"),
                avg_fare=("avg_fare", "mean"),
                avg_distance=("avg_distance", "mean"),
                avg_tip_pct=("avg_tip_pct", "mean"),
                avg_speed=("avg_speed", "mean"),
            )
            .round(2)
            .rename(
                columns={
                    "total_trips": "Total de viagens",
                    "total_revenue": "Receita total (US$)",
                    "avg_fare": "Tarifa média (US$)",
                    "avg_distance": "Distância média (mi)",
                    "avg_tip_pct": "Gorjeta média (%)",
                    "avg_speed": "Velocidade média (mph)",
                }
            )
        )

        vendor.index = vendor.index.map(VENDOR_LABELS)
        vendor.index.name = "Fornecedor"

        st.bar_chart(vendor["Total de viagens"], use_container_width=True)
        st.dataframe(vendor, use_container_width=True)

    # ---------------- PAYMENT ----------------
    with tab_payment:
        st.subheader("💳 Comportamento de pagamento e gorjetas")
        payment = (
            df.groupby("payment_label", as_index=True)
            .agg(
                total_trips=("total_trips", "sum"),
                total_revenue=("total_revenue", "sum"),
                avg_tip_pct=("avg_tip_pct", "mean"),
                avg_fare=("avg_fare", "mean"),
                avg_tip_amount=("avg_tip_amount", "mean")
            )
            .round(2)
            .rename(
                columns={
                    "total_trips": "Total de viagens",
                    "total_revenue": "Receita total (US$)",
                    "avg_tip_pct": "Gorjeta média (%)",
                    "avg_fare": "Tarifa média (US$)",
                    "avg_tip_amount": "Gorjeta média (US$)",
                }
            )
        )

        payment.index = payment.index.map(PAYMENT_LABELS)
        payment.index.name = "Método de Pagamento"

        payment["% de viagens"] = (
            (payment["Total de viagens"] / payment["Total de viagens"].sum()) * 100
        ).round(2)

        st.bar_chart(payment["Total de viagens"], use_container_width=True)
        st.dataframe(payment, use_container_width=True)

    # ---------------- WEEKDAY ----------------
    with tab_weekday:
        st.subheader("📅 Variação de demanda por dia da semana")
        weekday = (
            df.groupby("day_of_week", as_index=True)
            .agg(
                total_trips=("total_trips", "sum"),
                total_revenue=("total_revenue", "sum"),
                avg_fare=("avg_fare", "mean"),
                avg_distance=("avg_distance", "mean"),
                avg_speed=("avg_speed", "mean"),
                avg_duration=("avg_duration", "mean"),
                avg_tip_pct=("avg_tip_pct", "mean"),
            )
            .round(2)
            .rename(
                columns={
                    "total_trips": "Total de viagens",
                    "total_revenue": "Receita total (US$)",
                    "avg_fare": "Tarifa média (US$)",
                    "avg_distance": "Distância média (mi)",
                    "avg_speed": "Velocidade média (mph)",
                    "avg_duration": "Duração média (min)",
                    "avg_tip_pct": "Gorjeta média (%)",
                }
            )
        )
        weekday = weekday.reindex(DAY_ORDER)
        weekday.index.name = "Dia da Semana"

        st.bar_chart(weekday["Total de viagens"], use_container_width=True)
        st.dataframe(weekday, use_container_width=True)


if __name__ == "__main__":
    main()