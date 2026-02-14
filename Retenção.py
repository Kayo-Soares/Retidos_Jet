import streamlit as st
import pandas as pd
import numpy as np
import re

st.set_page_config(page_title="Radar Retenção PDD", layout="wide")
st.title("📦 Radar de Criticidade - Retidos no PDD")

# ===========================
# HOME (Tela inicial com Cards + Fluxograma)
# ===========================
st.markdown("## 👋 Bem-vindo ao Radar de Retidos no PDD")
st.caption(
    "Objetivo: mostrar onde estão os pedidos parados (retidos), qual o nível de gravidade e onde agir primeiro."
)

st.markdown(
    """
**Definições rápidas (para leigos):**
- **Retidos**: pedidos/remessas parados no fluxo (sem movimentação).
- **Tempo de retenção**: há quantos dias o pedido está parado (1, 2, 3, 5, 7, 10, 15 ou **>15**).
- **Criticidade**: quanto maior o tempo parado, maior o risco (SLA, reclamação, devolução, custo).
"""
)

st.divider()
st.markdown("### 🧭 O que cada relatório responde?")

def kpi_card(title: str, desc: str, example: str = ""):
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 14px;
            padding: 14px 14px;
            background: rgba(255,255,255,0.03);
            height: 100%;
        ">
            <div style="font-size: 16px; font-weight: 700; margin-bottom: 6px;">{title}</div>
            <div style="font-size: 13px; opacity: 0.9; line-height: 1.35;">{desc}</div>
            {f'<div style="font-size: 12px; opacity: 0.75; margin-top: 8px;"><b>Exemplo:</b> {example}</div>' if example else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

row1 = st.columns(3)
with row1[0]:
    kpi_card(
        "🚨 Alertas automáticos",
        "Lista as unidades (bases/franquias) que precisam de atenção imediata, por volume alto, muita retenção >15 dias ou média de dias muito elevada.",
        "“F OCD-GO” concentrando 12% dos retidos ou 40 itens >15 dias."
    )
with row1[1]:
    kpi_card(
        "🏆 Top Unidades por Volume",
        "Mostra quem tem mais pedidos retidos (quantidade). Responde onde o acúmulo é maior.",
        "Base X com 193 retidos e Base Y com 102."
    )
with row1[2]:
    kpi_card(
        "⚠️ Top por Score Misto",
        "Ranking que combina quantidade (volume) e gravidade (dias parados). Prioriza o que é muito + velho.",
        "Uma base com poucos retidos, mas quase tudo >15 dias sobe no ranking."
    )

row2 = st.columns(3)
with row2[0]:
    kpi_card(
        "📍 Distribuição por dias de retenção",
        "Mostra em quais faixas (1,2,3,5,7,10,15,>15) estão concentrados os pedidos. Indica se é problema recente ou backlog antigo.",
        "70% em 1–3 dias = fluxo travado; muito em >15 = backlog grave."
    )
with row2[1]:
    kpi_card(
        "📉 Pareto (concentração)",
        "Mostra quanto do problema está nas poucas unidades do topo. Ajuda a focar energia onde dá mais retorno.",
        "Top 10 unidades concentrando 80% dos retidos."
    )
with row2[2]:
    kpi_card(
        "🚚 Motoristas & 🧾 Ocorrências",
        "Aponta padrões: motoristas que mais aparecem e ocorrências mais frequentes. Ajuda a enxergar causa e responsabilidade.",
        "Ocorrência “não chegou” dominando e um motorista aparecendo em muitos casos."
    )

st.divider()

st.markdown("### 🧩 Mini fluxograma de decisão (Retido → Criticidade → Ação)")
st.markdown(
    """
<div style="
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 14px;
    padding: 14px;
    background: rgba(255,255,255,0.03);
">
  <div style="font-size: 14px; line-height: 1.6;">
    <b>1) Retido</b> (pedido parado)
    <span style="opacity:0.65;">→</span>
    <b>2) Criticidade</b> (quanto tempo parado / >15 dias / concentração na base)
    <span style="opacity:0.65;">→</span>
    <b>3) Ação</b> (o que fazer primeiro)
  </div>

  <div style="margin-top: 10px; font-size: 13px; opacity:0.9; line-height: 1.6;">
    <b>Se a maioria está em 1–3 dias:</b> gargalo de fluxo → revisar triagem, rotas, expedição e capacidade diária.<br/>
    <b>Se há muito >15 dias:</b> backlog grave → varredura de inventário, fila PDD, bloqueios e tratativa dedicada.<br/>
    <b>Se 1 base concentra % alto:</b> foco gerencial → plano de ação na unidade (dono, prazo, meta de redução).<br/>
    <b>Se uma ocorrência domina:</b> foco na causa → ação específica (ex.: “não chegou”, “falha SC”, “endereço”).<br/>
    <b>Se um motorista aparece demais:</b> auditoria/treinamento → checar padrão de baixa/scan/rota.
  </div>
</div>
""",
    unsafe_allow_html=True
)

st.divider()

st.markdown("### ✅ Acessar o painel")
liberar = st.checkbox("Entendi o que cada bloco mostra e quero acessar os relatórios")
if not liberar:
    st.stop()

# ---------------------------
# Helpers
# ---------------------------
def extrair_peso(texto: str) -> int:
    """Converte '超15天滞留', '7天滞留' etc em peso numérico."""
    if pd.isna(texto):
        return 0
    s = str(texto).strip()
    if "超" in s:  # acima de 15
        return 20
    nums = re.findall(r"\d+", s)
    return int(nums[0]) if nums else 0

def eh_franquia(nome_base: str) -> bool:
    """Se começar com F (com ou sem espaço/hífen), considera franquia."""
    if pd.isna(nome_base):
        return False
    s = str(nome_base).strip().upper()
    return s.startswith("F ") or s.startswith("F-") or s == "F" or s.startswith("F")

def farol_participacao(pct: float) -> str:
    """Farol de participação no total de retidos (no recorte filtrado)."""
    if pct >= 0.10:
        return "🔴 Alta (>=10%)"
    if pct >= 0.05:
        return "🟡 Média (>=5%)"
    return "🟢 Baixa (<5%)"

def pick_first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retorna o primeiro nome de coluna existente (case-insensitive) dentre candidatos."""
    cols = list(df.columns)
    cols_upper = {c.upper(): c for c in cols}
    for cand in candidates:
        if cand.upper() in cols_upper:
            return cols_upper[cand.upper()]
    return None

def normalize_text_series(s: pd.Series) -> pd.Series:
    """Normaliza texto: strip, vira string, substitui vazios por NA."""
    out = s.astype(str).str.strip()
    out = out.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return out

# ---------------------------
# Upload
# ---------------------------
arquivo = st.file_uploader("Envie a base (.xlsx)", type=["xlsx"])
if not arquivo:
    st.info("Faça upload do Excel para gerar automaticamente ranking, farol, alertas e análises.")
    st.stop()

df = pd.read_excel(arquivo)

# ---------------------------
# Validação mínima
# ---------------------------
colunas_necessarias = ["Remessa", "Nome da base de entrega", "Tempo de retenção"]
faltando = [c for c in colunas_necessarias if c not in df.columns]
if faltando:
    st.error(f"Faltam colunas na planilha: {faltando}")
    st.write("Colunas disponíveis:", list(df.columns))
    st.stop()

# ---------------------------
# Tradução do Tempo de retenção (CN -> PT-BR) + coluna amigável
# ---------------------------
MAPA_RETENCAO_PT = {
    "1天滞留": "1 dia retido",
    "2天滞留": "2 dias retido",
    "3天滞留": "3 dias retido",
    "5天滞留": "5 dias retido",
    "7天滞留": "7 dias retido",
    "10天滞留": "10 dias retido",
    "15天滞留": "15 dias retido",
    "超15天滞留": "Acima de 15 dias retido",
}

df["Tempo de retenção (PT)"] = (
    df["Tempo de retenção"]
    .astype(str)
    .str.strip()
    .map(MAPA_RETENCAO_PT)
    .fillna(df["Tempo de retenção"].astype(str).str.strip())
)

ORDEM_RETEN_PT = [
    "1 dia retido", "2 dias retido", "3 dias retido", "5 dias retido",
    "7 dias retido", "10 dias retido", "15 dias retido", "Acima de 15 dias retido"
]
PESO_RETEN_PT = {
    "1 dia retido": 1,
    "2 dias retido": 2,
    "3 dias retido": 3,
    "5 dias retido": 5,
    "7 dias retido": 7,
    "10 dias retido": 10,
    "15 dias retido": 15,
    "Acima de 15 dias retido": 20,
}

# ---------------------------
# Detectar colunas para "motorista" e "ocorrências"
# ---------------------------
driver_candidates = [
    "Motorista", "Entregador", "Driver", "Courier",
    "Digitalizador de Saída para Entrega",
    "Digitalizador de saída para entrega",
    "Entregador de Saída para Entrega",
]
occ_candidates = [
    "Tipo problemático", "Ocorrência", "Ocorrencia", "Motivo", "Status", "Reason", "Exception"
]

col_driver = pick_first_existing(df, driver_candidates)
col_occ = pick_first_existing(df, occ_candidates)

# ---------------------------
# Colunas novas
# ---------------------------
df["Peso Criticidade"] = df["Tempo de retenção"].apply(extrair_peso)
df["Tipo Unidade"] = df["Nome da base de entrega"].apply(eh_franquia).map({True: "Franquia", False: "Base própria"})

# normalizar (se existirem)
if col_driver:
    df[col_driver] = normalize_text_series(df[col_driver])
if col_occ:
    df[col_occ] = normalize_text_series(df[col_occ])

# ---------------------------
# Sidebar filtros
# ---------------------------
st.sidebar.header("Filtros")

tipo_sel = st.sidebar.multiselect(
    "Tipo de unidade",
    options=["Franquia", "Base própria"],
    default=["Franquia", "Base própria"],
)
df_f = df[df["Tipo Unidade"].isin(tipo_sel)].copy()

# Tempo de retenção (PT)
reten_unique = df_f["Tempo de retenção (PT)"].astype(str).unique().tolist()
reten_options = [x for x in ORDEM_RETEN_PT if x in reten_unique] + [x for x in reten_unique if x not in ORDEM_RETEN_PT]

reten_sel = st.sidebar.multiselect(
    "Tempo de retenção",
    options=reten_options,
    default=reten_options
)
df_f = df_f[df_f["Tempo de retenção (PT)"].astype(str).isin(reten_sel)].copy()

# Top N e limiares
top_n = st.sidebar.slider("Top N (listas)", 5, 50, 15)
limiar_alerta_pct = st.sidebar.slider("Alerta por participação (%)", 1, 30, 10) / 100.0
limiar_alerta_media = st.sidebar.slider("Alerta por criticidade média (dias)", 5, 20, 10)
limiar_alerta_mais15 = st.sidebar.slider("Alerta por Qtd >15 dias", 5, 100, 30)

# ---------------------------
# Funções de agregação
# ---------------------------
def build_base_rank(d: pd.DataFrame) -> pd.DataFrame:
    base_rank = (
        d.groupby(["Nome da base de entrega", "Tipo Unidade"])
        .agg(
            Retidos=("Remessa", "count"),
            Soma_Peso=("Peso Criticidade", "sum"),
            Media_Criticidade=("Peso Criticidade", "mean"),
        )
        .reset_index()
    )
    base_rank["% Participação"] = base_rank["Retidos"] / max(len(d), 1)
    base_rank["Farol (%)"] = base_rank["% Participação"].apply(farol_participacao)

    # Qtd >15 por base
    mais15 = (
        d[d["Peso Criticidade"] >= 20]
        .groupby("Nome da base de entrega")
        .size()
        .reset_index(name="Qtd_>15dias")
    )
    base_rank = base_rank.merge(mais15, on="Nome da base de entrega", how="left")
    base_rank["Qtd_>15dias"] = base_rank["Qtd_>15dias"].fillna(0).astype(int)

    # Score misto (volume + criticidade)
    base_rank["Score Misto"] = (
        (base_rank["Retidos"] / max(base_rank["Retidos"].max(), 1)) * 0.6 +
        (base_rank["Media_Criticidade"] / max(base_rank["Media_Criticidade"].max(), 1)) * 0.4
    )
    return base_rank

def build_reten_dist(d: pd.DataFrame) -> pd.DataFrame:
    reten_dist = (
        d.groupby("Tempo de retenção (PT)")
        .agg(Retidos=("Remessa", "count"))
        .reset_index()
    )
    reten_dist["Peso"] = reten_dist["Tempo de retenção (PT)"].map(PESO_RETEN_PT).fillna(999)
    reten_dist = reten_dist.sort_values("Peso", ascending=True)
    reten_dist["%"] = reten_dist["Retidos"] / max(len(d), 1)
    return reten_dist

def top_counts(d: pd.DataFrame, col: str, topn: int) -> pd.DataFrame:
    if not col or col not in d.columns:
        return pd.DataFrame()
    tmp = d[col].dropna()
    if tmp.empty:
        return pd.DataFrame()
    out = tmp.value_counts().head(topn).reset_index()
    out.columns = [col, "Qtde"]
    out["%"] = out["Qtde"] / max(len(d), 1)
    return out

# ---------------------------
# Construir métricas globais do recorte
# ---------------------------
base_rank = build_base_rank(df_f)
reten_dist = build_reten_dist(df_f)

# alertas
alertas_crit = base_rank[
    (base_rank["% Participação"] >= limiar_alerta_pct) |
    (base_rank["Qtd_>15dias"] >= limiar_alerta_mais15) |
    (base_rank["Media_Criticidade"] >= limiar_alerta_media)
].sort_values(["% Participação", "Qtd_>15dias", "Media_Criticidade"], ascending=False)

# Top motoristas e ocorrências (no recorte)
top_drivers = top_counts(df_f, col_driver, top_n) if col_driver else pd.DataFrame()
top_occs = top_counts(df_f, col_occ, top_n) if col_occ else pd.DataFrame()

# ---------------------------
# Abas
# ---------------------------
tab_ger, tab_det = st.tabs(["📊 Gerencial", "🔎 Detalhado"])

# ===========================
# ABA GERENCIAL
# ===========================
with tab_ger:
    st.subheader("📌 Visão Geral (recorte atual)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de retidos", len(df_f))
    c2.metric("Média criticidade", round(df_f["Peso Criticidade"].mean(), 2) if len(df_f) else 0)
    c3.metric("Qtd >15 dias", int((df_f["Peso Criticidade"] >= 20).sum()))
    c4.metric("Bases/Unidades no recorte", df_f["Nome da base de entrega"].nunique())

    st.subheader("🚨 Alertas automáticos (unidades críticas)")
    if len(alertas_crit):
        st.error("Unidades críticas detectadas pelos critérios definidos.")
        st.dataframe(
            alertas_crit[[
                "Nome da base de entrega","Tipo Unidade","Retidos","% Participação","Farol (%)",
                "Qtd_>15dias","Media_Criticidade","Soma_Peso","Score Misto"
            ]],
            use_container_width=True
        )
    else:
        st.success("Nenhuma unidade crítica pelos critérios atuais.")

    colA, colB = st.columns(2)

    with colA:
        st.subheader("🏆 Top Unidades por Volume (mais retidos)")
        st.dataframe(
            base_rank.sort_values(["Retidos","Media_Criticidade"], ascending=[False, False]).head(top_n),
            use_container_width=True
        )

    with colB:
        st.subheader("⚠️ Top Unidades por Score Misto (volume + criticidade)")
        st.dataframe(
            base_rank.sort_values("Score Misto", ascending=False).head(top_n),
            use_container_width=True
        )

    st.subheader("📍 Distribuição: quais dias de retenção concentram mais pedidos?")
    st.dataframe(
        reten_dist.sort_values("Retidos", ascending=False)[["Tempo de retenção (PT)","Retidos","%"]],
        use_container_width=True
    )

    st.subheader("📉 Pareto (concentração do problema)")
    pareto = base_rank.sort_values("Retidos", ascending=False).copy()
    pareto["Retidos_acum"] = pareto["Retidos"].cumsum()
    pareto["%_acum"] = pareto["Retidos_acum"] / max(pareto["Retidos"].sum(), 1)
    pct_top10 = float(pareto.head(min(10, len(pareto)))["Retidos"].sum() / max(pareto["Retidos"].sum(), 1))
    st.info(f"Top 10 unidades concentram **{pct_top10:.1%}** dos retidos (no recorte atual).")
    st.dataframe(
        pareto[["Nome da base de entrega","Tipo Unidade","Retidos","% Participação","Retidos_acum","%_acum"]].head(30),
        use_container_width=True
    )

    st.subheader("🚚 Motoristas que mais aparecem (no recorte)")
    if col_driver:
        if not top_drivers.empty:
            st.dataframe(top_drivers, use_container_width=True)
        else:
            st.warning(f"Coluna de motorista detectada: **{col_driver}**, mas está vazia no recorte.")
    else:
        st.warning("Não encontrei coluna de motorista automaticamente. Colunas disponíveis:")
        st.write(list(df.columns))

    st.subheader("🧾 Ocorrências que mais aparecem (no recorte)")
    if col_occ:
        if not top_occs.empty:
            st.dataframe(top_occs, use_container_width=True)
        else:
            st.warning(f"Coluna de ocorrência detectada: **{col_occ}**, mas está vazia no recorte.")
    else:
        st.warning("Não encontrei coluna de ocorrência automaticamente. Colunas disponíveis:")
        st.write(list(df.columns))

# ===========================
# ABA DETALHADO
# ===========================
with tab_det:
    st.subheader("🔎 Drill-down por unidade")

    unidades = sorted(df_f["Nome da base de entrega"].unique().tolist())
    unidade_sel = st.selectbox("Escolha a unidade/base", unidades)

    d_u = df_f[df_f["Nome da base de entrega"] == unidade_sel].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Retidos (unidade)", len(d_u))
    c2.metric("% participação", f"{(len(d_u)/max(len(df_f),1)):.1%}")
    c3.metric("Média criticidade", round(d_u["Peso Criticidade"].mean(), 2) if len(d_u) else 0)
    c4.metric("Qtd >15 dias", int((d_u["Peso Criticidade"] >= 20).sum()))

    st.subheader("📍 Distribuição de retenção (unidade)")
    dist_u = build_reten_dist(d_u)
    st.dataframe(
        dist_u.sort_values("Retidos", ascending=False)[["Tempo de retenção (PT)","Retidos","%"]],
        use_container_width=True
    )

    colX, colY = st.columns(2)

    with colX:
        st.subheader("🚚 Top motoristas (unidade)")
        if col_driver:
            top_d_u = top_counts(d_u, col_driver, top_n)
            if not top_d_u.empty:
                st.dataframe(top_d_u, use_container_width=True)
            else:
                st.info("Sem dados de motorista para essa unidade (ou coluna vazia).")
        else:
            st.info("Sem coluna de motorista detectada nesta base.")

    with colY:
        st.subheader("🧾 Top ocorrências (unidade)")
        if col_occ:
            top_o_u = top_counts(d_u, col_occ, top_n)
            if not top_o_u.empty:
                st.dataframe(top_o_u, use_container_width=True)
            else:
                st.info("Sem dados de ocorrência para essa unidade (ou coluna vazia).")
        else:
            st.info("Sem coluna de ocorrência detectada nesta base.")

    st.subheader("📄 Linhas detalhadas (unidade)")
    prefer = [
        "Remessa", "Pedidos", "Tempo de retenção (PT)", "Peso Criticidade",
        "Horário de coleta", "Horário de expedição do SC", "Data prevista de entrega",
        "Horário de Recebimento na Base", "Horário de Saída para Entrega", "Horário da entrega",
        "Origem do Pedido", "Tipo de produto"
    ]
    if col_driver:
        prefer.append(col_driver)
    if col_occ:
        prefer.append(col_occ)

    cols_show = [c for c in prefer if c in d_u.columns] + [c for c in d_u.columns if c not in prefer]
    st.dataframe(d_u[cols_show], use_container_width=True)
