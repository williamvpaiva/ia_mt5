import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import httpx
import time
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="IA_MT5 Dashboard", layout="wide", initial_sidebar_state="expanded")

# Estilos Customizados (CSS)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4250; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4CAF50; color: white; }
    .stop-button>button { background-color: #f44336; }
    </style>
    """, unsafe_allow_html=True)

BACKEND_URL = "http://backend:8000"

# Funções de API
def get_bots():
try:
response = httpx.get(f"{BACKEND_URL}/bots/")
response.raise_for_status()
data = response.json()
return data if isinstance(data, list) else []
except Exception as e:
print(f"Erro ao buscar bots: {e}")
return []

def toggle_bot(bot_id, action):
    try:
        httpx.post(f"{BACKEND_URL}/bots/{bot_id}/{action}")
        return True
    except:
        return False

def create_bot(name, magic):
    try:
        httpx.post(f"{BACKEND_URL}/bots/", params={"name": name, "magic": magic})
        return True
    except:
        return False

# --- SIDEBAR ---
st.sidebar.title("🤖 IA_MT5 Controller")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Meus Bots", "IA & Notícias", "Backtest", "Configurações"])

# --- HEADER ---
st.title("🏆 Omni-Bot V21 (SINCRO OK)")
st.markdown("Monitoramento de alta performance para Mini Índice B3")

if menu == "Dashboard":
    # Linha 1: Métricas Principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="PnL Total (Dia)", value="R$ 1.250,00", delta="+R$ 450,00")
    with col2:
        st.metric(label="Win Rate", value="68%", delta="2%")
    with col3:
        st.metric(label="Drawdown Máx", value="4.2%", delta="-0.5%", delta_color="inverse")
    with col4:
        st.metric(label="Dataset (Velas)", value="2.450", delta="100")

    # Linha 2: Gráfico de Equity
    st.markdown("### 📈 Curva de Equity Real-time")
    # Gerando dados fictícios para exemplo visual
    data = pd.DataFrame({"Tempo": pd.date_range(start="2026-04-18", periods=20, freq="H"),
                         "Balance": [10000 + i*100 + (pd.Series(np.random.randn(20)).cumsum().iloc[i]*50) for i in range(20)]})
    fig = px.line(data, x="Tempo", y="Balance", template="plotly_dark", color_discrete_sequence=['#00ff88'])
    st.plotly_chart(fig, use_container_width=True)

elif menu == "Meus Bots":
    st.header("⚙️ Gerenciamento de Robôs")
    
    with st.expander("➕ Adicionar Novo Robô"):
        new_name = st.text_input("Nome do Bot")
        new_magic = st.number_input("Magic Number", value=12345)
        if st.button("Criar Robô"):
            if create_bot(new_name, new_magic):
                st.success("Robô criado com sucesso!")
                st.rerun()

    st.markdown("---")
    bots = get_bots()
    
    if not bots:
        st.info("Nenhum robô cadastrado.")
    else:
        for bot in bots:
            with st.container():
                b_col1, b_col2, b_col3, b_col4 = st.columns([2, 1, 1, 1])
                b_col1.markdown(f"**{bot['name']}** (Magic: {bot['magic_number']})")
                b_col2.write(f"Símbolo: {bot['symbol']}")
                b_col3.write(f"Status: {'🟢 Ativo' if bot['active'] else '🔴 Inativo'}")
                
                if not bot['active']:
                    if b_col4.button("START", key=f"start_{bot['id']}"):
                        toggle_bot(bot['id'], "start")
                        st.rerun()
                else:
                    if b_col4.button("STOP", key=f"stop_{bot['id']}"):
                        toggle_bot(bot['id'], "stop")
                        st.rerun()
            st.markdown("---")

elif menu == "IA & Notícias":
    st.header("🧠 Inteligência Artificial (Ollama)")
    st.write("Acompanhe o que a IA está analisando no momento.")
    
    test_text = st.text_area("Simular Notícia para Análise", "O Banco Central sinaliza manutenção da taxa Selic, o que anima investidores do Mini Índice.")
    if st.button("Analisar Sentimento"):
        st.write("🔍 **IA Processando...**")
        # Aqui chamaria o backend que consulta o Ollama
        st.success("Resultado Simulado: **BULLISH** (Score: 82/100)")

elif menu == "Backtest":
    st.header("🧪 Simulador de Estratégias (Backtest)")
    st.write("Teste a performance dos indicadores sobre dados históricos reais do MT5.")
    
    col_bt1, col_bt2, col_bt3 = st.columns(3)
    bt_symbol = col_bt1.selectbox("Símbolo", ["WIN$", "WDO$", "PETR4"])
    bt_tf = col_bt2.selectbox("Timeframe", ["M1", "M5", "M15"])
    bt_count = col_bt3.slider("Quantidade de Candles", 100, 2000, 500)
    
    if st.button("🚀 Rodar Backtest"):
        with st.spinner("Processando simulação..."):
            try:
                res = httpx.post(f"{BACKEND_URL}/dashboard/backtest", 
                                 params={"symbol": bt_symbol, "timeframe": bt_tf, "count": bt_count},
                                 timeout=60.0)
                bt_data = res.json()
                
                if "error" in bt_data:
                    st.error(bt_data["error"])
                else:
                    # Métricas de Resultado
                    m1, m2, m3 = st.columns(3)
                    m1.metric("PnL Simulado", f"R$ {bt_data['total_pnl']:.2f}")
                    m2.metric("Nº de Trades", bt_data['trades_count'])
                    m3.metric("Win Rate", f"{bt_data['win_rate']*100:.1f}%")
                    
                    # Gráfico de Lucro Acumulado
                    st.markdown("### 📊 Evolução do Patrimônio (Simulação)")
                    ec_df = pd.DataFrame({"Equity": bt_data['equity_curve']})
                    st.line_chart(ec_df, color="#ffaa00")
                    
                    # Tabela de Trades
                    st.markdown("### 📝 Histórico de Trades")
                    st.table(pd.DataFrame(bt_data['trades']))
            except Exception as e:
                st.error(f"Erro ao conectar ao backend: {e}")

st.sidebar.markdown("---")
st.sidebar.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
