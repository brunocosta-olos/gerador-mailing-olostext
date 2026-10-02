"""Interface web (Streamlit) do Gerador de Mailings Olos.

Executar:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import interface as ui
from motor import processar
from motor.cenarios import TETO_PREFERENCIAL
from motor.geracao import CAMPANHAS
from motor.historico import colunas_do_historico
from motor.leitura import ErroLeitura
from motor.pipeline import data_do_nome

st.set_page_config(page_title="Gerador de Mailings Olos", page_icon=":material/mail:", layout="wide")
ui.aplicar_estilo()

# O cabeçalho fica no topo, mas é preenchido no fim, quando o estado já é conhecido.
topo = st.empty()

REGRAS = [
    "<b>Exclui:</b> nome vazio, com número, com símbolos ou inválido; idade ausente; "
    "<b>66 anos ou mais</b>; telefone inutilizável.",
    "<b>Pendência:</b> faixa etária que atravessa 66 anos ou é ininteligível; linha com estrutura quebrada.",
    "<b>Limpa:</b> espaços extras; hífen e apóstrofo em nomes.",
    "<b>Deduplica</b> por telefone (registro mais completo; em empate, o primeiro).",
    "<b>ENVIADO</b> = telefone presente no histórico do mês.",
    "<b>5 arquivos</b>, NÃO ENVIADOS primeiro, status nunca misturados.",
    "Layout: 8 campos, <b>;</b>, UTF-8 sem BOM, CRLF, sem cabeçalho.",
]

# ---------------------------------------------------------------- 1. Bases
ui.secao(1, "Bases", "Envie o mailing do dia e o histórico do mês.")
col1, col2 = st.columns(2)
with col1:
    up_mailing = st.file_uploader("Mailing do dia (TXT/CSV)", type=["txt", "csv"])
    ui.estado(up_mailing is not None, "Mailing carregado", "Aguardando o mailing do dia")
with col2:
    up_hist = st.file_uploader("Histórico do mês (Excel, CSV ou TXT)", type=["xlsx", "xlsm", "xls", "csv", "txt"])
    ui.estado(up_hist is not None, "Histórico carregado", "Aguardando o histórico do mês")
pode = up_mailing is not None and up_hist is not None

# ---------------------------------------------------------------- 2. Configuração
ui.secao(2, "Configuração", "Quantidade de números, data da base e opções de cruzamento.")
col3, col4 = st.columns(2)
with col3:
    qtd = st.radio(
        "Números disponíveis", [1, 2, 3, 4], index=2, horizontal=True,
        help="Define quais campanhas/prefixos são usados, em ciclo.",
    )
    st.caption("Campanhas usadas: " + " · ".join(f"`{CAMPANHAS[i]}`" for i in range(1, qtd + 1)))
with col4:
    data_detectada = data_do_nome(up_mailing.name) if up_mailing else None
    data_base = st.date_input(
        "Data da base", value=data_detectada or date.today(), format="DD/MM/YYYY",
    )
    if up_mailing:
        st.caption("Data encontrada no nome do arquivo." if data_detectada else
                   "Nenhuma data no nome do arquivo: usando a data de hoje.")

coluna_hist = None
equivaler_55 = False
with st.expander("Opções avançadas"):
    if up_hist:
        try:
            cols = colunas_do_historico(up_hist.name, up_hist.getvalue())
            escolha = st.selectbox(
                "Coluna do histórico com o telefone (ou ConversationId)",
                ["Detectar automaticamente"] + cols,
            )
            coluna_hist = None if escolha == "Detectar automaticamente" else escolha
        except ErroLeitura as e:
            st.error(str(e))
    else:
        st.caption("Envie o histórico para escolher a coluna manualmente.")
    equivaler_55 = st.checkbox(
        "Considerar '55' + DDD + número igual a DDD + número",
        value=False,
        help="Desligado por padrão: o sistema não acrescenta nem remove o código do país por suposição. "
             "Ative apenas se você sabe que as duas bases usam formatos diferentes para o mesmo número.",
    )

# ---------------------------------------------------------------- 3. Processamento
ui.secao(3, "Processamento", "Higieniza, deduplica, cruza com o histórico e monta os cinco arquivos.")
if st.button("Processar mailing", type="primary", disabled=not pode, width="stretch"):
    with st.spinner("Processando..."):
        try:
            st.session_state["res"] = processar(
                up_mailing.name, up_mailing.getvalue(), up_hist.name, up_hist.getvalue(),
                int(qtd), data_base.strftime("%Y%m%d"), coluna_hist, equivaler_55,
            )
            st.session_state["erro"] = None
        except (ErroLeitura, ValueError) as e:
            st.session_state["res"] = None
            st.session_state["erro"] = str(e)
res = st.session_state.get("res")

if not pode:
    st.info("Envie o mailing e o histórico, escolha a quantidade de números e clique em **Processar mailing**.")

if st.session_state.get("erro"):
    st.error(st.session_state["erro"])


def mostrar_resultado(res) -> bool:
    """Desenha o resultado e devolve se todas as validações passaram."""
    r = res.resumo
    aprovadas = sum(ok for _, ok, _ in res.validacoes)
    todas_ok = aprovadas == len(res.validacoes) and r["reconciliado"]
    recebidos = r["recebidos"]

    def parte(v: int) -> str:
        return f"{100 * v / recebidos:.1f}% dos registros recebidos".replace(".", ",") if recebidos else "—"

    # ------------------------------------------------ 4. Resultado
    ui.secao(4, "Resultado", "Volumes consolidados do processamento e status das validações.")
    if todas_ok:
        st.success("Arquivos gerados e validados. Todas as checagens passaram.")
    else:
        st.error("Alguma validação falhou. Confira a aba de validações antes de importar.")

    ui.kpis([
        ("Recebidos", recebidos, ui.LARANJA, "Volume total do mailing do dia"),
        ("Entregues", r["entregues"], ui.VERDE, "Contatos únicos nos arquivos · " + parte(r["entregues"])),
        ("Não enviados", r["nao_enviados"], ui.CIANO, "Prioridade de uso · " + parte(r["nao_enviados"])),
        ("Enviados", r["enviados"], ui.LAVANDA, "Já presentes no histórico · " + parte(r["enviados"])),
        ("Excluídos", r["excluidos"], ui.VERMELHO, "Fora das regras de elegibilidade · " + parte(r["excluidos"])),
        ("Pendências", r["pendencias"], ui.AMBAR, "Requerem revisão manual · " + parte(r["pendencias"])),
        ("Duplicatas", r["duplicatas"], ui.AZUL, "Telefones repetidos removidos"),
        ("Validações", f"{aprovadas}/{len(res.validacoes)}", ui.VERDE if todas_ok else ui.VERMELHO,
         "Checagens aprovadas nos arquivos gerados"),
    ])
    ui.distribuicao([
        ("Não enviados", r["nao_enviados"], ui.CIANO),
        ("Enviados", r["enviados"], ui.LAVANDA),
        ("Excluídos", r["excluidos"], ui.VERMELHO),
        ("Pendências", r["pendencias"], ui.AMBAR),
        ("Duplicatas", r["duplicatas"], ui.AZUL),
    ])

    # ------------------------------------------------ 5. Arquivos
    ui.secao(5, "Arquivos", "NÃO ENVIADOS primeiro; ENVIADOS reservados para a etapa posterior.")
    st.download_button(
        "Baixar os 5 arquivos (ZIP)", res.zip_bytes,
        file_name=f"mailings_base{r['data_base']}.zip", mime="application/zip", type="primary",
        width="stretch",
    )

    maximo = max((a["quantidade"] for a in res.arquivos), default=0)
    for i, a in enumerate(res.arquivos, start=1):
        with st.container(key=f"arq{i}"):
            ca, cb = st.columns([8, 1.4], vertical_alignment="center")
            with ca:
                ui.cartao_arquivo(i, a, maximo, TETO_PREFERENCIAL)
            with cb:
                st.download_button(
                    "Baixar", a["dados"], file_name=a["nome"], mime="text/plain", key=f"dl{i}",
                    width="stretch",
                )

    st.write("")
    ui.texto_card("Divisão escolhida", res.explicacao)
    for aviso in res.avisos:
        st.warning(aviso)

    # ------------------------------------------------ 6. Detalhes
    ui.secao(6, "Detalhes", "Reconciliação, motivos, validações e leitura das bases.")
    abas = ["Reconciliação", "Motivos", "Validações", "Tabela de entrega", "Leitura das bases"]
    if res.detalhes:
        abas.append("Linhas fora dos arquivos")
    tabs = st.tabs(abas)

    with tabs[0]:
        ui.extrato([
            ("Registros recebidos", recebidos),
            ("(−) Excluídos", r["excluidos"]),
            ("(−) Pendências", r["pendencias"]),
            ("(−) Duplicatas removidas", r["duplicatas"]),
        ], ("(=) Contatos únicos entregues", r["entregues"]), r["reconciliado"])
        if r["linhas_vazias_ignoradas"]:
            st.caption(f"{r['linhas_vazias_ignoradas']} linha(s) totalmente vazia(s) ignorada(s), fora do total recebido.")

    with tabs[1]:
        linhas = [("Exclusão", k, v) for k, v in res.exclusoes.most_common()]
        linhas += [("Pendência", k, v) for k, v in res.pendencias.most_common()]
        if linhas:
            st.dataframe(
                pd.DataFrame(linhas, columns=["Tipo", "Motivo", "Linhas"]), hide_index=True, width="stretch",
                column_config={"Linhas": st.column_config.ProgressColumn(
                    "Linhas", format="%d", min_value=0, max_value=max(v for *_, v in linhas))},
            )
            st.caption("Uma linha com vários motivos aparece em cada motivo, mas é contada uma única vez no total.")
        else:
            st.success("Nenhuma exclusão ou pendência.")

    with tabs[2]:
        ui.validacoes(res.validacoes)

    with tabs[3]:
        tabela = pd.DataFrame([{
            "Arquivo": a["nome"], "Campanha": a["campanha"], "Status": a["status_rotulo"],
            "Cenário": a["cenario"], "Critérios": a["criterios"], "Contatos": a["quantidade"],
        } for a in res.arquivos])
        st.dataframe(tabela, hide_index=True, width="stretch")

    with tabs[4]:
        st.markdown(f"- **Mailing:** {r['mailing_formato']}")
        if r["colunas_auxiliares"]:
            st.markdown(f"- **Colunas auxiliares ignoradas:** {', '.join(r['colunas_auxiliares'])}")
        st.markdown(f"- **Histórico:** {r['historico_formato']}")
        st.markdown(f"- **Chave do histórico:** {r['historico_coluna']}")
        st.markdown(f"- **Linhas no histórico:** {ui.fmt(r['historico_linhas'])} · **telefones únicos:** "
                    f"{ui.fmt(r['historico_telefones_unicos'])}")
        if r["historico_templates"] is not None:
            st.markdown(f"- **Templates distintos:** {r['historico_templates']} · telefones com mais de um template: "
                        f"{r['historico_multiplos_templates']}")

    if res.detalhes:
        with tabs[5]:
            st.caption("Número da linha e motivo, sem dados pessoais.")
            det = pd.DataFrame(res.detalhes).rename(
                columns={"linha": "Linha no arquivo", "categoria": "Categoria", "motivos": "Motivos"})
            st.dataframe(det, hide_index=True, width="stretch", height=300)
            st.download_button(
                "Baixar relatório (CSV)", det.to_csv(index=False, sep=";").encode("utf-8-sig"),
                file_name=f"relatorio_exclusoes_base{r['data_base']}.csv", mime="text/csv",
            )
    return todas_ok


validado = mostrar_resultado(res) if res else False

if not pode:
    status = "Aguardando bases"
elif res is None:
    status = "Pronto para processar"
else:
    status = "Validado" if validado else "Revisar validações"

with topo.container():
    ui.cabecalho([("Data da base", data_base.strftime("%d/%m/%Y")), ("Campanhas", str(qtd)), ("Status", status)])

tem_res = res is not None
ui.menu_lateral(
    [("Bases", pode, True), ("Configuração", pode, True), ("Processamento", tem_res, True),
     ("Resultado", validado, tem_res), ("Arquivos", validado, tem_res), ("Detalhes", validado, tem_res)],
    REGRAS,
)
