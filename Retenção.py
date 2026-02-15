import streamlit as st
import pandas as pd
import numpy as np
import re
import os
from typing import Optional, List

# ==========================================================
# CONFIG
# ==========================================================
st.set_page_config(page_title="Radar Retenção PDD", layout="wide")
st.title("📦 Radar de Criticidade - Retidos no PDD")

# ==========================================================
# HOME (Tela inicial com Cards + Fluxograma)
# ==========================================================
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

# ==========================================================
# HELPERS
# ==========================================================
def _norm_text(x) -> str:
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).strip())

def pick_first_existing(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = list(df.columns)
    cols_upper = {c.upper(): c for c in cols}
    for cand in candidates:
        if cand.upper() in cols_upper:
            return cols_upper[cand.upper()]
    return None

def normalize_text_series(s: pd.Series) -> pd.Series:
    out = s.astype(str).str.strip()
    out = out.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return out

def extrair_peso_cn(texto: str) -> int:
    if pd.isna(texto):
        return 0
    s = str(texto).strip()
    if "超" in s:
        return 20
    nums = re.findall(r"\d+", s)
    return int(nums[0]) if nums else 0

def eh_franquia(nome_base: str) -> bool:
    if pd.isna(nome_base):
        return False
    s = str(nome_base).strip().upper()
    return s.startswith("F ") or s.startswith("F-") or s == "F" or s.startswith("F")

def farol_participacao(pct: float) -> str:
    if pct >= 0.10:
        return "🔴 Alta (>=10%)"
    if pct >= 0.05:
        return "🟡 Média (>=5%)"
    return "🟢 Baixa (<5%)"

def show_table(
    d: pd.DataFrame,
    percent_cols: Optional[List[str]] = None,
    height: Optional[int] = None,
):
    if d is None or d.empty:
        st.info("Sem dados para exibir (no recorte atual).")
        return

    percent_cols = percent_cols or []
    colcfg = {}
    for c in percent_cols:
        if c in d.columns:
            colcfg[c] = st.column_config.NumberColumn(c, format="%.1f%%")

    kwargs = dict(use_container_width=True, hide_index=True)
    if colcfg:
        kwargs["column_config"] = colcfg
    if height is not None:
        kwargs["height"] = height

    st.dataframe(d, **kwargs)

# ==========================================================
# RETENÇÃO (CN -> PT-BR) + ORDEM + PESOS
# ==========================================================
MAPA_RETENCAO_PT = {
    "1天滞留": "01 dia retido",
    "2天滞留": "02 dias retido",
    "3天滞留": "03 dias retido",
    "5天滞留": "05 dias retido",
    "7天滞留": "07 dias retido",
    "10天滞留": "08 a 10 dias retido",
    "15天滞留": "15 dias retido",
    "超15天滞留": "16+ dias retido",
}
ORDEM_RETEN_PT = [
    "01 dia retido",
    "02 dias retido",
    "03 dias retido",
    "05 dias retido",
    "07 dias retido",
    "08 a 10 dias retido",
    "15 dias retido",
    "16+ dias retido",
]
PESO_RETEN_PT = {
    "01 dia retido": 1,
    "02 dias retido": 2,
    "03 dias retido": 3,
    "05 dias retido": 5,
    "07 dias retido": 7,
    "08 a 10 dias retido": 10,
    "15 dias retido": 15,
    "16+ dias retido": 20,
}

# ==========================================================
# UPLOAD
# ==========================================================
arquivo = st.file_uploader("Envie a base de RETIDOS (.xlsx)", type=["xlsx"])
if not arquivo:
    st.info("Faça upload do Excel para gerar automaticamente ranking, farol, alertas e análises.")
    st.stop()

df = pd.read_excel(arquivo)

# ==========================================================
# VALIDAÇÃO MÍNIMA
# ==========================================================
colunas_necessarias = ["Remessa", "Nome da base de entrega", "Tempo de retenção"]
faltando = [c for c in colunas_necessarias if c not in df.columns]
if faltando:
    st.error(f"Faltam colunas na planilha: {faltando}")
    st.write("Colunas disponíveis:", list(df.columns))
    st.stop()

# ==========================================================
# ENRIQUECIMENTO: BASE DE COORDENADORES (arquivo dentro do projeto)
# ==========================================================
BASE_COORD_PATH = os.path.join("data", "Base_Coordenadores.xlsx")

df_coord = None
coord_status_msg = None

if os.path.exists(BASE_COORD_PATH):
    try:
        df_coord = pd.read_excel(BASE_COORD_PATH)
    except Exception as e:
        coord_status_msg = f"⚠️ Não consegui ler `{BASE_COORD_PATH}`: {e}"
else:
    coord_status_msg = f"⚠️ Não encontrei `{BASE_COORD_PATH}`. (Pasta/arquivo não existem ou nome diferente)"

def preparar_base_coord(df_coord_in: pd.DataFrame) -> tuple[Optional[pd.DataFrame], str]:
    if df_coord_in is None or df_coord_in.empty:
        return None, "⚠️ Base de coordenadores vazia."

    # base/unidade (obrigatório)
    col_base_map = pick_first_existing(df_coord_in, [
        "Nome da base de entrega", "Base", "Nome da Base", "Nome base", "Unidade", "Nome da unidade"
    ])
    if not col_base_map:
        return None, "⚠️ Não achei coluna de BASE/UNIDADE no Base_Coordenadores.xlsx."

    # coordenador/uf/filial (opcional)
    col_coord = pick_first_existing(df_coord_in, [
        "Coordenador", "Coord", "Responsável", "Responsavel", "Gestor", "Supervisor"
    ])
    col_uf = pick_first_existing(df_coord_in, ["UF", "Estado"])
    col_filial = pick_first_existing(df_coord_in, ["Filial", "Branch", "Regional"])

    out = df_coord_in.copy()
    out[col_base_map] = out[col_base_map].apply(_norm_text)

    rename = {col_base_map: "Nome da base de entrega"}
    if col_coord: rename[col_coord] = "Coordenador"
    if col_uf: rename[col_uf] = "UF"
    if col_filial: rename[col_filial] = "Filial"
    out = out.rename(columns=rename)

    keep = ["Nome da base de entrega"]
    if "Coordenador" in out.columns: keep.append("Coordenador")
    if "UF" in out.columns: keep.append("UF")
    if "Filial" in out.columns: keep.append("Filial")

    out = out[keep].drop_duplicates(subset=["Nome da base de entrega"], keep="first")

    msg = "✅ Base de coordenadores carregada."
    detalhes = []
    detalhes.append(f"Base: `{col_base_map}`")
    detalhes.append(f"Coord: `{col_coord}`" if col_coord else "Coord: (não mapeado)")
    detalhes.append(f"UF: `{col_uf}`" if col_uf else "UF: (não mapeado)")
    detalhes.append(f"Filial: `{col_filial}`" if col_filial else "Filial: (não mapeado)")
    msg += " " + " | ".join(detalhes)

    return out, msg

df["Nome da base de entrega"] = df["Nome da base de entrega"].apply(_norm_text)

df_coord_p = None
if df_coord is not None and not df_coord.empty:
    df_coord_p, prep_msg = preparar_base_coord(df_coord)
    coord_status_msg = prep_msg

# merge se tiver base tratada
if df_coord_p is not None:
    df = df.merge(df_coord_p, on="Nome da base de entrega", how="left")

# ✅ GARANTIR COLUNAS (evita KeyError SEMPRE)
for col in ["Coordenador", "UF", "Filial"]:
    if col not in df.columns:
        df[col] = pd.NA

# ==========================================================
# DETECTAR COLUNAS DE MOTORISTA E OCORRÊNCIA
# ==========================================================
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

if col_driver:
    df[col_driver] = normalize_text_series(df[col_driver])
if col_occ:
    df[col_occ] = normalize_text_series(df[col_occ])

# ==========================================================
# COLUNAS DERIVADAS
# ==========================================================
df["Tempo de retenção (PT)"] = (
    df["Tempo de retenção"]
    .astype(str)
    .str.strip()
    .map(MAPA_RETENCAO_PT)
    .fillna(df["Tempo de retenção"].astype(str).str.strip())
)

df["Peso Criticidade"] = (
    df["Tempo de retenção (PT)"].map(PESO_RETEN_PT)
    .fillna(df["Tempo de retenção"].apply(extrair_peso_cn))
    .fillna(0)
    .astype(float)
)

df["Tipo Unidade"] = df["Nome da base de entrega"].apply(eh_franquia).map({True: "Franquia", False: "Base própria"})

# ==========================================================
# SIDEBAR FILTROS
# ==========================================================
st.sidebar.header("Filtros")

tipo_sel = st.sidebar.multiselect(
    "Tipo de unidade",
    options=["Franquia", "Base própria"],
    default=["Franquia", "Base própria"],
)

# ✅ agora não quebra, pois as colunas SEMPRE existem
coord_opts = sorted([x for x in df["Coordenador"].dropna().astype(str).unique().tolist() if x.strip() != ""])
uf_opts = sorted([x for x in df["UF"].dropna().astype(str).unique().tolist() if x.strip() != ""])
filial_opts = sorted([x for x in df["Filial"].dropna().astype(str).unique().tolist() if x.strip() != ""])

coord_sel = st.sidebar.multiselect("Coordenador", options=coord_opts, default=coord_opts) if coord_opts else []
uf_sel = st.sidebar.multiselect("UF", options=uf_opts, default=uf_opts) if uf_opts else []
filial_sel = st.sidebar.multiselect("Filial", options=filial_opts, default=filial_opts) if filial_opts else []

df_f = df[df["Tipo Unidade"].isin(tipo_sel)].copy()
if coord_opts:
    df_f = df_f[df_f["Coordenador"].astype(str).isin(coord_sel)].copy()
if uf_opts:
    df_f = df_f[df_f["UF"].astype(str).isin(uf_sel)].copy()
if filial_opts:
    df_f = df_f[df_f["Filial"].astype(str).isin(filial_sel)].copy()

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
limiar_alerta_mais15 = st.sidebar.slider("Alerta por Qtd 16+ dias", 5, 100, 30)

# ==========================================================
# AGREGAÇÕES
# ==========================================================
def build_base_rank(d: pd.DataFrame) -> pd.DataFrame:
    grp_cols = ["Nome da base de entrega", "Tipo Unidade", "Coordenador", "UF", "Filial"]

    base_rank = (
        d.groupby(grp_cols, dropna=False)
        .agg(
            Retidos=("Remessa", "count"),
            Soma_Peso=("Peso Criticidade", "sum"),
            Media_Criticidade=("Peso Criticidade", "mean"),
        )
        .reset_index()
    )

    total = max(len(d), 1)
    base_rank["% Participação"] = base_rank["Retidos"] / total
    base_rank["Farol (%)"] = base_rank["% Participação"].apply(farol_participacao)

    mais15 = (
        d[d["Peso Criticidade"] >= 20]
        .groupby("Nome da base de entrega")
        .size()
        .reset_index(name="Qtd_16+")
    )
    base_rank = base_rank.merge(mais15, on="Nome da base de entrega", how="left")
    base_rank["Qtd_16+"] = base_rank["Qtd_16+"].fillna(0).astype(int)

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

def build_coord_rank(d: pd.DataFrame) -> pd.DataFrame:
    dd = d.dropna(subset=["Coordenador"]).copy()
    dd = dd[dd["Coordenador"].astype(str).str.strip() != ""]
    if dd.empty:
        return pd.DataFrame()

    r = (
        dd.groupby("Coordenador")
        .agg(
            Retidos=("Remessa", "count"),
            Media_Criticidade=("Peso Criticidade", "mean"),
            Qtd_16mais=("Peso Criticidade", lambda s: int((s >= 20).sum())),
        )
        .reset_index()
    )
    r["% Participação"] = r["Retidos"] / max(len(d), 1)
    r["Score Misto"] = (
        (r["Retidos"] / max(r["Retidos"].max(), 1)) * 0.6 +
        (r["Media_Criticidade"] / max(r["Media_Criticidade"].max(), 1)) * 0.4
    )
    r = r.sort_values(["Score Misto", "Retidos"], ascending=False)
    return r

# ==========================================================
# MÉTRICAS DO RECORTE
# ==========================================================
base_rank = build_base_rank(df_f)
reten_dist = build_reten_dist(df_f)
coord_rank = build_coord_rank(df_f)

alertas_crit = base_rank[
    (base_rank["% Participação"] >= limiar_alerta_pct) |
    (base_rank["Qtd_16+"] >= limiar_alerta_mais15) |
    (base_rank["Media_Criticidade"] >= limiar_alerta_media)
].sort_values(["% Participação", "Qtd_16+", "Media_Criticidade"], ascending=False)

top_drivers = top_counts(df_f, col_driver, top_n) if col_driver else pd.DataFrame()
top_occs = top_counts(df_f, col_occ, top_n) if col_occ else pd.DataFrame()

# ==========================================================
# ABAS
# ==========================================================
tab_ger, tab_det = st.tabs(["📊 Gerencial", "🔎 Detalhado"])

# ==========================
# ABA GERENCIAL
# ==========================
with tab_ger:
    st.subheader("📌 Visão Geral (recorte atual)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de retidos", len(df_f))
    c2.metric("Média criticidade", round(float(df_f["Peso Criticidade"].mean()), 2) if len(df_f) else 0)
    c3.metric("Qtd 16+ dias", int((df_f["Peso Criticidade"] >= 20).sum()))
    c4.metric("Unidades no recorte", int(df_f["Nome da base de entrega"].nunique()))

    if not coord_rank.empty:
        st.subheader("🧑‍💼 Ranking de Coordenadores (no recorte)")
        cols = ["Coordenador", "Retidos", "% Participação", "Qtd_16mais", "Media_Criticidade", "Score Misto"]
        show_table(coord_rank[cols].head(50), percent_cols=["% Participação"], height=420)

    st.subheader("🚨 Alertas automáticos (unidades críticas)")
    if len(alertas_crit):
        st.error("Unidades críticas detectadas pelos critérios definidos.")
        cols = [
            "Nome da base de entrega","Tipo Unidade","Coordenador","UF","Filial",
            "Retidos","% Participação","Farol (%)","Qtd_16+","Media_Criticidade","Soma_Peso","Score Misto"
        ]
        cols = [c for c in cols if c in alertas_crit.columns]
        show_table(alertas_crit[cols], percent_cols=["% Participação"], height=420)
    else:
        st.success("Nenhuma unidade crítica pelos critérios atuais.")

    colA, colB = st.columns(2)

    with colA:
        st.subheader("🏆 Top Unidades por Volume (mais retidos)")
        show_table(
            base_rank.sort_values(["Retidos", "Media_Criticidade"], ascending=[False, False]).head(top_n),
            percent_cols=["% Participação"],
            height=420
        )

    with colB:
        st.subheader("⚠️ Top Unidades por Score Misto (volume + criticidade)")
        show_table(
            base_rank.sort_values("Score Misto", ascending=False).head(top_n),
            percent_cols=["% Participação"],
            height=420
        )

    st.subheader("📍 Distribuição: quais dias de retenção concentram mais pedidos?")
    show_table(
        reten_dist.sort_values("Retidos", ascending=False)[["Tempo de retenção (PT)", "Retidos", "%"]],
        percent_cols=["%"],
        height=320
    )

    st.subheader("📉 Pareto (concentração do problema)")
    pareto = base_rank.sort_values("Retidos", ascending=False).copy()
    pareto["Retidos_acum"] = pareto["Retidos"].cumsum()
    pareto["%_acum"] = pareto["Retidos_acum"] / max(pareto["Retidos"].sum(), 1)
    pct_top10 = float(pareto.head(min(10, len(pareto)))["Retidos"].sum() / max(pareto["Retidos"].sum(), 1))
    st.info(f"Top 10 unidades concentram **{pct_top10:.1%}** dos retidos (no recorte atual).")
    cols = [
        "Nome da base de entrega","Tipo Unidade","Coordenador","UF","Filial",
        "Retidos","% Participação","Retidos_acum","%_acum"
    ]
    cols = [c for c in cols if c in pareto.columns]
    show_table(pareto[cols].head(30), percent_cols=["% Participação", "%_acum"], height=420)

    st.subheader("🚚 Motoristas que mais aparecem (no recorte)")
    if col_driver:
        if not top_drivers.empty:
            show_table(top_drivers, percent_cols=["%"], height=320)
        else:
            st.warning(f"Coluna de motorista detectada: **{col_driver}**, mas está vazia no recorte.")
    else:
        st.warning("Não encontrei coluna de motorista automaticamente.")

    st.subheader("🧾 Ocorrências que mais aparecem (no recorte)")
    if col_occ:
        if not top_occs.empty:
            show_table(top_occs, percent_cols=["%"], height=320)
        else:
            st.warning(f"Coluna de ocorrência detectada: **{col_occ}**, mas está vazia no recorte.")
    else:
        st.warning("Não encontrei coluna de ocorrência automaticamente.")

# ==========================
# ABA DETALHADO
# ==========================
with tab_det:
    st.subheader("🔎 Drill-down por unidade")

    unidades = sorted(df_f["Nome da base de entrega"].unique().tolist())
    if not unidades:
        st.warning("Sem unidades no recorte atual. Ajuste os filtros.")
        st.stop()

    unidade_sel = st.selectbox("Escolha a unidade/base", unidades)
    d_u = df_f[df_f["Nome da base de entrega"] == unidade_sel].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Retidos (unidade)", len(d_u))
    c2.metric("% participação", f"{(len(d_u)/max(len(df_f),1)):.1%}")
    c3.metric("Média criticidade", round(float(d_u["Peso Criticidade"].mean()), 2) if len(d_u) else 0)
    c4.metric("Qtd 16+ dias", int((d_u["Peso Criticidade"] >= 20).sum()))

    meta_cols = []
    for c in ["Coordenador", "UF", "Filial", "Tipo Unidade"]:
        if c in d_u.columns and d_u[c].notna().any():
            v = d_u[c].dropna().astype(str)
            if len(v):
                meta_cols.append(f"**{c}**: {v.iloc[0]}")
    if meta_cols:
        st.caption(" | ".join(meta_cols))

    st.subheader("📍 Distribuição de retenção (unidade)")
    dist_u = build_reten_dist(d_u)
    show_table(
        dist_u.sort_values("Retidos", ascending=False)[["Tempo de retenção (PT)", "Retidos", "%"]],
        percent_cols=["%"],
        height=320
    )

    colX, colY = st.columns(2)

    with colX:
        st.subheader("🚚 Top motoristas (unidade)")
        if col_driver:
            top_d_u = top_counts(d_u, col_driver, top_n)
            if not top_d_u.empty:
                show_table(top_d_u, percent_cols=["%"], height=360)
            else:
                st.info("Sem dados de motorista para essa unidade (ou coluna vazia).")
        else:
            st.info("Sem coluna de motorista detectada nesta base.")

    with colY:
        st.subheader("🧾 Top ocorrências (unidade)")
        if col_occ:
            top_o_u = top_counts(d_u, col_occ, top_n)
            if not top_o_u.empty:
                show_table(top_o_u, percent_cols=["%"], height=360)
            else:
                st.info("Sem dados de ocorrência para essa unidade (ou coluna vazia).")
        else:
            st.info("Sem coluna de ocorrência detectada nesta base.")

    st.subheader("📄 Linhas detalhadas (unidade)")
    prefer = [
        "Remessa", "Pedidos",
        "Tempo de retenção (PT)", "Peso Criticidade",
        "Horário de coleta", "Horário de expedição do SC", "Data prevista de entrega",
        "Horário de Recebimento na Base", "Horário de Saída para Entrega", "Horário da entrega",
        "Origem do Pedido", "Tipo de produto",
        "Coordenador", "UF", "Filial", "Tipo Unidade"
    ]
    if col_driver:
        prefer.append(col_driver)
    if col_occ:
        prefer.append(col_occ)

    cols_show = [c for c in prefer if c in d_u.columns] + [c for c in d_u.columns if c not in prefer]
    show_table(d_u[cols_show], height=520)
