"""Componentes visuais (HTML/CSS) da interface Streamlit.

Tudo aqui é apresentação: nenhuma regra de negócio. Textos vindos das bases
passam por ``escape`` antes de entrar no HTML.
"""

from __future__ import annotations

from html import escape

import streamlit as st

# Paleta do guia visual Olos, usada também pelo app.py nos indicadores.
LARANJA, LAVANDA, CIANO, VERMELHO = "#FB5C28", "#000049", "#3189AE", "#DC2626"
AZUL, AMBAR, VERDE = "#7ECBDD", "#D97706", "#16A34A"

LOGO = "app/static/olos_logo.png"

CSS = """
:root {
  --laranja: #FB5C28; --laranja2: #FF8155; --laranja-suave: #FFF1EC; --laranja-borda: #FDC9B6;
  --azul: #7ECBDD; --azul-fundo: #3189AE; --marinho: #000049;
  --tinta: #111827; --texto: #475467; --suave: #667085;
  --superficie: #FFFFFF; --superficie2: #F8FAFC; --superficie3: #EEF2F6;
  --linha: #D8DEE8; --linha-forte: #C8D2DE;
  --verde: #16A34A; --vermelho: #DC2626; --ambar: #D97706;
  --sombra: 0 16px 42px rgba(16,40,58,.06);
  --sans: "Plus Jakarta Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", Consolas, monospace;
}
.stApp { background: #F3F6F9; color: var(--tinta); }
.stApp, .stApp p, .stApp li, .stApp label { font-family: var(--sans); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 2.5rem; max-width: 1320px; }
code { font-family: var(--mono) !important; }

/* ---------- Barra lateral */
[data-testid="stSidebar"] { background: var(--superficie); border-right: 1px solid var(--linha); }
[data-testid="stSidebarUserContent"] { padding: 0 0 2rem; }
[data-testid="stSidebarHeader"] { height: 1.5rem; }
.marca { padding: 10px 22px 24px; border-bottom: 1px solid var(--linha); margin: 0 -1rem 14px; }
.marca img { display: block; height: 30px; width: auto; object-fit: contain; margin-bottom: 20px; }
.marca b { display: block; font-size: 1.3rem; font-weight: 800; color: var(--tinta); letter-spacing: -.01em; }
.marca span { color: var(--texto); font-size: .92rem; line-height: 1.5; }
.menu { margin: 0 -1rem; }
.menu a { display: flex; gap: 18px; align-items: center; padding: 13px 24px; color: var(--tinta) !important;
  text-decoration: none !important; font-size: 1rem; font-weight: 500; border-left: 3px solid transparent;
  transition: background .15s; }
.menu a:hover { background: var(--superficie2); }
.menu a .n { font-family: var(--mono); font-size: .78rem; font-weight: 700; color: var(--suave); width: 20px; }
.menu a.ativo { background: var(--laranja-suave); color: var(--laranja) !important; border-left-color: var(--laranja); }
.menu a.ativo .n { color: var(--laranja); }
.menu a.ok .n { color: var(--verde); }
.menu a.inativo { color: #A3ACBA !important; pointer-events: none; }
.menu a.inativo .n { color: #C0C7D2; }
.regras-tit { font-size: .72rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--suave);
  margin: 26px 0 10px; }
.regras { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 9px; }
.regras li { font-size: .82rem; line-height: 1.5; color: var(--texto); padding-left: 12px; border-left: 2px solid var(--laranja-borda); }
.regras b { color: var(--tinta); }
.privado { margin-top: 20px; font-size: .78rem; color: var(--suave); }

/* ---------- Cabeçalho */
.hero { position: relative; overflow: hidden; padding: 34px 40px 36px; margin-bottom: 8px;
  background: radial-gradient(520px 320px at 92% 30%, rgba(251,92,40,.07) 0%, transparent 70%), var(--superficie2);
  border: 1px solid var(--linha); border-radius: 22px; }
.hero::before { content: ""; position: absolute; inset: 0 0 auto; height: 3px;
  background: linear-gradient(90deg, var(--laranja), var(--azul)); }
.hero-logo { display: block; height: 46px; width: auto; object-fit: contain; margin-bottom: 26px; }
.pilula { display: inline-block; font-weight: 700; font-size: .82rem; letter-spacing: .06em; text-transform: uppercase;
  color: var(--laranja); background: var(--laranja-suave); border: 1px solid var(--laranja-borda);
  padding: 7px 18px; border-radius: 99px; }
.hero-tit { font-size: 2.6rem; font-weight: 800; color: var(--marinho); letter-spacing: -.035em; line-height: 1.08; margin: 20px 0 12px; }
.hero-sub { font-size: 1.15rem; color: var(--texto); }
.chips { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 24px; }
.chips span { background: var(--superficie); border: 1px solid var(--linha); border-radius: 12px;
  padding: 8px 18px; font-size: .98rem; color: var(--texto); }
.chips b { color: var(--tinta); font-weight: 700; }

/* ---------- Seções */
.secao { margin: 56px 0 22px; scroll-margin-top: 80px; }
.secao-cab { display: flex; align-items: center; gap: 18px; }
.secao-num { font-family: var(--mono); font-weight: 700; font-size: .92rem; color: var(--laranja);
  background: var(--laranja-suave); border: 1px solid var(--laranja-borda); border-radius: 8px; padding: 5px 12px; }
.secao-tit { font-size: 1.85rem; font-weight: 800; color: var(--tinta); letter-spacing: -.02em; }
.secao-sub { font-size: 1.05rem; color: var(--texto); margin-top: 12px; }
.estado { display: inline-flex; gap: 8px; align-items: center; font-size: .8rem; font-weight: 600; margin-top: 8px; color: var(--suave); }
.estado i { width: 8px; height: 8px; border-radius: 50%; background: var(--linha-forte); }
.estado.ok { color: var(--verde); }
.estado.ok i { background: var(--verde); }

/* ---------- Widgets nativos */
[data-testid="stWidgetLabel"] p { font-weight: 700; color: var(--tinta); }
[data-testid="stFileUploaderDropzone"] { background: var(--superficie); border: 1.5px dashed var(--linha-forte);
  border-radius: 16px; transition: border-color .15s, background .15s; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--laranja); background: var(--laranja-suave); }
.stButton button, .stDownloadButton button { border-radius: 12px; font-weight: 700; transition: background .15s, border-color .15s; }
[data-testid="stBaseButton-primary"] { background: var(--laranja); border: 1px solid var(--laranja); color: #fff; }
[data-testid="stBaseButton-primary"]:hover { background: #E94E1C; border-color: #E94E1C; color: #fff; }
.stButton [data-testid="stBaseButton-primary"] { padding: .85rem 1rem; }
.stButton [data-testid="stBaseButton-primary"] p { font-size: 1.05rem; }
[data-testid="stBaseButton-secondary"] { background: var(--superficie); border: 1px solid var(--linha-forte); color: var(--tinta); }
[data-testid="stBaseButton-secondary"]:hover { border-color: var(--laranja); color: var(--laranja); }
[data-testid="stRadio"] div[role="radiogroup"] { gap: 10px; }
[data-testid="stRadio"] div[role="radiogroup"] label { background: var(--superficie); border: 1px solid var(--linha);
  border-radius: 10px; padding: 7px 18px 7px 12px; margin: 0; transition: border-color .15s, background .15s; }
[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) { border-color: var(--laranja); background: var(--laranja-suave); }
[data-testid="stExpander"] details { background: var(--superficie); border: 1px solid var(--linha); border-radius: 16px; }
[class*="st-key-arq"] { background: var(--superficie); border: 1px solid var(--linha); border-radius: 16px; padding: 16px 20px;
  transition: border-color .15s; }
[class*="st-key-arq"]:hover { border-color: var(--laranja-borda); }
[data-baseweb="tab-list"] { gap: 6px; background: var(--superficie); padding: 6px; border-radius: 14px; border: 1px solid var(--linha); }
button[data-baseweb="tab"] { border-radius: 10px; padding: 6px 14px; }
button[data-baseweb="tab"][aria-selected="true"] { background: var(--laranja-suave); }
button[data-baseweb="tab"][aria-selected="true"] p { color: var(--laranja); }
[data-baseweb="tab-highlight"] { background: var(--laranja); }
[data-testid="stAlert"] { border-radius: 14px; }

/* ---------- Cartões */
.card { background: var(--superficie); border: 1px solid var(--linha); border-radius: 16px; padding: 22px 26px;
  height: 100%; box-shadow: var(--sombra); }
.card-tit { font-size: .78rem; text-transform: uppercase; letter-spacing: .12em; color: var(--texto); font-weight: 800; margin-bottom: 16px; }

/* ---------- Indicadores */
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 22px; }
.kpi { background: var(--superficie); border: 1px solid var(--linha); border-top: 3px solid var(--c); border-radius: 16px;
  padding: 22px 24px 24px; box-shadow: var(--sombra); }
.kpi .r { font-size: .76rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--texto); }
.kpi .v { font-size: 2.1rem; font-weight: 800; color: var(--tinta); margin: 12px 0 10px; letter-spacing: -.02em; }
.kpi .t { width: 30px; height: 4px; border-radius: 2px; background: var(--c); margin-bottom: 14px; }
.kpi .ds { font-size: .92rem; color: var(--suave); line-height: 1.5; }

/* ---------- Distribuição */
.dist { display: flex; height: 14px; border-radius: 99px; overflow: hidden; margin: 4px 0 16px; background: var(--superficie3); gap: 2px; }
.dist > div { height: 100%; }
.legenda { display: flex; flex-wrap: wrap; gap: 18px; font-size: .88rem; color: var(--texto); }
.legenda b { color: var(--tinta); }
.legenda i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 8px; vertical-align: middle; }

/* ---------- Arquivos */
.arq { display: flex; gap: 18px; align-items: center; }
.arq-idx { font-family: var(--mono); font-weight: 700; font-size: .92rem; border-radius: 10px; padding: 10px 12px; flex: none; }
.arq-idx.ne { color: var(--azul-fundo); background: #EAF5F9; border: 1px solid #B9DDEA; }
.arq-idx.e { color: var(--marinho); background: #EDEDF5; border: 1px solid #C9C9DE; }
.arq-corpo { flex: 1; min-width: 0; }
.arq-nome { font-family: var(--mono); font-size: .88rem; font-weight: 600; color: var(--tinta);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.arq-chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 6px; }
.chip { font-size: .72rem; font-weight: 700; padding: 3px 10px; border-radius: 99px; letter-spacing: .04em; }
.chip-ne { background: #EAF5F9; color: var(--azul-fundo); }
.chip-e { background: #EDEDF5; color: var(--marinho); }
.chip-camp { background: var(--superficie3); color: var(--texto); }
.chip-alerta { background: #FEF3E2; color: #B45309; }
.arq-desc { font-size: .84rem; color: var(--suave); }
.arq-qtd { text-align: right; min-width: 130px; }
.arq-qtd b { font-size: 1.45rem; font-weight: 800; color: var(--tinta); }
.arq-qtd span { display: block; font-size: .72rem; color: var(--suave); text-transform: uppercase; letter-spacing: .1em; margin-bottom: 8px; }
.mini { height: 4px; background: var(--superficie3); border-radius: 99px; overflow: hidden; }
.mini > div { height: 100%; border-radius: 99px; }

/* ---------- Listas */
.lista { display: flex; flex-direction: column; gap: 10px; }
.item { display: flex; gap: 14px; align-items: flex-start; background: var(--superficie); border: 1px solid var(--linha);
  border-radius: 12px; padding: 12px 16px; }
.item .st { font-size: .7rem; font-weight: 800; letter-spacing: .08em; padding: 4px 10px; border-radius: 8px; flex: none; }
.item .st.ok { background: #E8F6EE; color: var(--verde); }
.item .st.falha { background: #FDECEC; color: var(--vermelho); }
.item .nm { font-weight: 700; font-size: .9rem; color: var(--tinta); }
.item .dt { font-size: .82rem; color: var(--suave); }
.extrato { background: var(--superficie); border: 1px solid var(--linha); border-radius: 16px; overflow: hidden; }
.extrato div { display: flex; justify-content: space-between; padding: 12px 18px; border-bottom: 1px solid var(--superficie3);
  font-size: .95rem; color: var(--texto); }
.extrato div span:last-child { font-family: var(--mono); }
.extrato div.total { background: var(--laranja-suave); font-weight: 800; color: var(--tinta); border-bottom: none; }
.extrato .neg { color: var(--vermelho); }
.selo { display: inline-block; margin-top: 12px; font-size: .82rem; font-weight: 700; padding: 5px 14px; border-radius: 99px; }
.selo.ok { background: #E8F6EE; color: var(--verde); }
.selo.falha { background: #FDECEC; color: var(--vermelho); }
.card.info { background: #F5F7FF; border-color: #DADFF5; box-shadow: none; }
.texto-card { color: var(--texto); font-size: 1rem; line-height: 1.65; }

@media (max-width: 1100px) {
  .kpis { grid-template-columns: repeat(2, 1fr); }
  .hero { padding: 28px 24px; }
  .hero-tit { font-size: 2.1rem; }
}
@media (max-width: 640px) {
  .kpis { grid-template-columns: 1fr; }
  .arq { flex-wrap: wrap; }
  .arq-qtd { text-align: left; }
}
"""


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _html(conteudo: str, destino=st) -> None:
    # Uma única linha, sem indentação: evita que o Markdown trate trechos como código.
    destino.markdown(" ".join(l.strip() for l in conteudo.splitlines() if l.strip()), unsafe_allow_html=True)


def aplicar_estilo() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def menu_lateral(itens: list[tuple[str, bool, bool]], regras: list[str]) -> None:
    """Menu numerado com âncoras. Cada item: (rótulo, concluído, disponível).

    Destaca a primeira etapa disponível e ainda não concluída.
    """
    atual = next((i for i, (_, ok, disp) in enumerate(itens) if disp and not ok), None)

    def classe(i, ok, disp):
        if not disp:
            return "inativo"
        return "ativo" if i == atual else "ok" if ok else ""

    links = "".join(
        f'<a href="#s{i + 1}" target="_self" class="{classe(i, ok, disp)}">'
        f'<span class="n">{i + 1:02d}</span>{escape(rot)}</a>'
        for i, (rot, ok, disp) in enumerate(itens)
    )
    lista = "".join(f"<li>{r}</li>" for r in regras)
    _html(f"""
    <div class="marca"><img src="{LOGO}" alt="Olos"><b>Central de Mailings</b><span>Olos Analytics · Gerador de Mailings</span></div>
    <nav class="menu">{links}</nav>
    <div class="regras-tit">Regras aplicadas</div>
    <ul class="regras">{lista}</ul>
    <div class="privado">Os dados são processados localmente e não são enviados a nenhum serviço externo.</div>
    """, st.sidebar)


def cabecalho(chips: list[tuple[str, str]]) -> None:
    etiquetas = "".join(f"<span><b>{escape(k)}:</b> {escape(v)}</span>" for k, v in chips)
    _html(f"""
    <div class="hero">
      <img class="hero-logo" src="{LOGO}" alt="Olos">
      <span class="pilula">Olos Analytics · Central de Mailings</span>
      <div class="hero-tit">Gerador de Mailings</div>
      <div class="hero-sub">Cruza o mailing do dia com o histórico do mês e gera os cinco TXT prontos para importação.</div>
      <div class="chips">{etiquetas}</div>
    </div>
    """)


def secao(numero: int, titulo: str, subtitulo: str) -> None:
    _html(f"""
    <div class="secao" id="s{numero}">
      <div class="secao-cab"><span class="secao-num">{numero:02d}</span><span class="secao-tit">{escape(titulo)}</span></div>
      <div class="secao-sub">{escape(subtitulo)}</div>
    </div>
    """)


def estado(ok: bool, texto_ok: str, texto_pend: str) -> None:
    _html(f'<div class="estado {"ok" if ok else ""}"><i></i>{escape(texto_ok if ok else texto_pend)}</div>')


def kpis(lista: list[tuple[str, int | str, str, str]]) -> None:
    """Cada item: (rótulo, valor, cor, descrição). Valores inteiros são formatados com separador de milhar."""
    cards = "".join(
        f'<div class="kpi" style="--c:{cor};animation-delay:{i * 50}ms">'
        f'<div class="r">{escape(rot)}</div><div class="v">{fmt(v) if isinstance(v, int) else escape(v)}</div>'
        f'<div class="t"></div><div class="ds">{escape(ds)}</div></div>'
        for i, (rot, v, cor, ds) in enumerate(lista)
    )
    _html(f'<div class="kpis">{cards}</div>')


def distribuicao(segmentos: list[tuple[str, int, str]]) -> None:
    total = sum(v for _, v, _ in segmentos) or 1
    barras = "".join(
        f'<div title="{escape(r)}: {fmt(v)}" style="width:{100 * v / total:.2f}%;background:{c}"></div>'
        for r, v, c in segmentos if v
    )
    legenda = "".join(
        f'<span><i style="background:{c}"></i>{escape(r)} · <b>{fmt(v)}</b> ({100 * v / total:.1f}%)</span>'
        for r, v, c in segmentos
    )
    _html(f"""
    <div class="card" style="margin-top:22px">
      <div class="card-tit">Destino dos registros recebidos</div>
      <div class="dist">{barras}</div>
      <div class="legenda">{legenda}</div>
    </div>
    """)


def cartao_arquivo(i: int, a: dict, maximo: int, teto: int) -> None:
    ne = a["status"] == "nao_enviados"
    cor = CIANO if ne else LAVANDA
    pct = 100 * a["quantidade"] / maximo if maximo else 0
    alerta = f'<span class="chip chip-alerta">Acima de {fmt(teto)}</span>' if a["quantidade"] > teto else ""
    vazio = '<span class="chip chip-alerta">Arquivo vazio</span>' if a["quantidade"] == 0 else ""
    _html(f"""
    <div class="arq">
      <div class="arq-idx {"ne" if ne else "e"}">{i:02d}</div>
      <div class="arq-corpo">
        <div class="arq-nome" title="{escape(a['nome'])}">{escape(a['nome'])}</div>
        <div class="arq-chips">
          <span class="chip {"chip-ne" if ne else "chip-e"}">{escape(a['status_rotulo'])}</span>
          <span class="chip chip-camp">Campanha {a['campanha']} · {escape(a['prefixo'])}</span>{alerta}{vazio}
        </div>
        <div class="arq-desc">{escape(a['cenario'])} · {escape(a['criterios'])}</div>
      </div>
      <div class="arq-qtd">
        <b>{fmt(a['quantidade'])}</b><span>contatos</span>
        <div class="mini"><div style="width:{pct:.1f}%;background:{cor}"></div></div>
      </div>
    </div>
    """)


def texto_card(titulo: str, texto: str) -> None:
    _html(f'<div class="card info"><div class="card-tit">{escape(titulo)}</div>'
          f'<div class="texto-card">{escape(texto)}</div></div>')


def extrato(linhas: list[tuple[str, int]], total: tuple[str, int], reconciliado: bool) -> None:
    corpo = "".join(
        f'<div><span>{escape(r)}</span><span class="{"neg" if r.startswith("(−)") else ""}">{fmt(v)}</span></div>'
        for r, v in linhas
    )
    selo = ('<span class="selo ok">Volumes reconciliados</span>' if reconciliado
            else '<span class="selo falha">Os volumes não fecham</span>')
    _html(f'<div class="extrato">{corpo}<div class="total"><span>{escape(total[0])}</span>'
          f'<span>{fmt(total[1])}</span></div></div>{selo}')


def validacoes(lista: list[tuple[str, bool, str]]) -> None:
    itens = "".join(
        f'<div class="item"><div class="st {"ok" if ok else "falha"}">{"APROVADA" if ok else "FALHOU"}</div>'
        f'<div><div class="nm">{escape(nome)}</div><div class="dt">{escape(det)}</div></div></div>'
        for nome, ok, det in lista
    )
    _html(f'<div class="lista">{itens}</div>')
