"""Testes das regras de negócio. Executar: python -m pytest -q"""

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motor import processar  # noqa: E402
from motor.cenarios import alocar_arquivos  # noqa: E402
from motor.geracao import nome_arquivo  # noqa: E402
from motor.pipeline import data_do_nome  # noqa: E402
from motor.telefone import extrair_telefone_canal, normalizar_telefone  # noqa: E402
from motor.validacao import avaliar_idade, limpar_nome  # noqa: E402

CAB = "nome;telefone;customerid;portfolio;faixa_atraso;faixa_saldo;faixa_idade;genero"


# ------------------------------------------------------------------ nomes
@pytest.mark.parametrize("entrada,esperado", [
    ("  Maria   da  Silva ", "Maria da Silva"),
    ("José Conceição", "José Conceição"),
    ("Ana-Clara", "Ana Clara"),
    ("João D'Ávila", "João DÁvila"),
    ("Luiz O’Neil", "Luiz ONeil"),
])
def test_nome_valido(entrada, esperado):
    assert limpar_nome(entrada) == (esperado, None)


@pytest.mark.parametrize("entrada", ["", "   ", "Maria 2", "J0ão", "José@", "Ana.", "TESTE", "xxx", "A", "Null"])
def test_nome_invalido(entrada):
    assert limpar_nome(entrada)[0] is None


# ------------------------------------------------------------------ idade
@pytest.mark.parametrize("faixa,situacao", [
    ("18-25", "ok"), ("56-65", "ok"), ("56 a 65", "ok"), ("até 30", "ok"), ("45", "ok"), ("<66", "ok"),
    ("66-75", "excluir"), ("75+", "excluir"), ("acima de 65", "excluir"), ("66 ou mais", "excluir"),
    ("70", "excluir"), ("", "excluir"), ("N/A", "excluir"),
    ("60-70", "pendente"), ("60+", "pendente"), ("idade?", "pendente"), ("30-20", "pendente"),
])
def test_idade(faixa, situacao):
    assert avaliar_idade(faixa)[0] == situacao


# ------------------------------------------------------------------ telefone
def test_telefone():
    assert normalizar_telefone("+55 (11) 99999-8888")[0] == "5511999998888"
    assert normalizar_telefone("11999998888")[0] == "11999998888"
    assert normalizar_telefone("5.5119E+12")[0] is None
    assert normalizar_telefone("5511999998888.0")[0] is None
    assert normalizar_telefone("5511999998888.0", origem_excel=True)[0] == "5511999998888"
    assert normalizar_telefone("abc")[0] is None
    assert normalizar_telefone("12345")[0] is None


@pytest.mark.parametrize("entrada,esperado", [
    ("whatsappcloud_5531994252095", "31994252095"),
    ("WhatsAppCloud_551140041234", "1140041234"),
    ("whatsappcloud_31994252095", None),  # sem 55: segue pelo fluxo normal
])
def test_extrair_telefone_canal(entrada, esperado):
    assert extrair_telefone_canal(entrada) == esperado


# ------------------------------------------------------------------ nomes de arquivo e datas
def test_prefixos_ciclicos_tres_numeros():
    nomes = [nome_arquivo(i, 3, "20260930", "nao_enviados") for i in range(5)]
    assert [n.split("base")[0] for n in nomes] == [
        "BOT_WPP_Massivo_", "BOT_WPP_Return_", "BOT_WPP_ATIVO_", "BOT_WPP_Massivo_", "BOT_WPP_Return_"]
    assert nomes[0] == "BOT_WPP_Massivo_base20260930_01_nao_enviados.txt"


def test_data_do_nome():
    assert str(data_do_nome("mailing_20260930.txt")) == "2026-09-30"
    assert str(data_do_nome("base 30-09-2026.txt")) == "2026-09-30"
    assert data_do_nome("mailing.txt") is None


def test_alocacao():
    assert alocar_arquivos(100, 0) == (5, 0)
    assert alocar_arquivos(0, 100) == (0, 5)
    assert alocar_arquivos(3000, 2000) == (3, 2)


# ------------------------------------------------------------------ ponta a ponta
def _hist_csv(telefones):
    return ("telefone;template\r\n" + "".join(f"{t};tpl\r\n" for t in telefones)).encode("utf-8")


def _linha(nome, tel, idade="26-35", atraso="0-30", cid="1"):
    return f"{nome};{tel};{cid};CARTAO;{atraso};Até 500;{idade};F"


def _rodar(linhas, hist, qtd=3, cabecalho=True, **kw):
    txt = ((CAB + "\r\n") if cabecalho else "") + "\r\n".join(linhas) + "\r\n"
    return processar("m.txt", txt.encode("utf-8"), "h.csv", _hist_csv(hist), qtd, "20260930", **kw)


def test_fluxo_completo():
    linhas = [_linha(f"Cliente {chr(65 + i % 26)}{chr(65 + i // 26 % 26)}", f"55119{i:08d}",
                     atraso=["0-30", "31-60", "61-90"][i % 3]) for i in range(300)]
    linhas += [
        _linha("Maria 2", "5511888880001"),
        _linha("Velho Pinto", "5511888880002", idade="75+"),
        _linha("Cruza Corte", "5511888880003", idade="60-70"),
        _linha("Sem Fone", ""),
        _linha("Cliente AA", "5511900000000", cid=""),  # duplicata menos completa do primeiro
    ]
    r = _rodar(linhas, hist=[f"55119{i:08d}" for i in range(0, 300, 4)])
    assert all(ok for _, ok, _ in r.validacoes), r.validacoes
    s = r.resumo
    assert s["recebidos"] == 305
    assert s["excluidos"] == 3 and s["pendencias"] == 1 and s["duplicatas"] == 1
    assert s["entregues"] == 300 and s["enviados"] == 75 and s["nao_enviados"] == 225
    assert s["reconciliado"]
    assert len(r.arquivos) == 5
    status = [a["status"] for a in r.arquivos]
    assert status == sorted(status, key=lambda x: x != "nao_enviados")  # não enviados primeiro
    dados = r.arquivos[0]["dados"]
    assert not dados.startswith(b"\xef\xbb\xbf") and b"\r\n" in dados
    assert b"nome;telefone" not in dados


def test_sem_cabecalho_com_colunas_auxiliares():
    linhas = [_linha(f"Pessoa {chr(65 + i)}", f"55219{i:08d}") + ";ENVIO;TPL" for i in range(10)]
    r = _rodar(linhas, hist=[], cabecalho=False)
    assert r.resumo["entregues"] == 10
    for a in r.arquivos:
        for l in a["dados"].decode().split("\r\n")[:-1]:
            assert len(l.split(";")) == 8


def test_poucos_contatos_gera_arquivos_vazios():
    r = _rodar([_linha("Ana Lima", "5511911111111"), _linha("Bia Lima", "5511922222222")], hist=[])
    assert len(r.arquivos) == 5
    assert sum(a["quantidade"] for a in r.arquivos) == 2
    assert sum(1 for a in r.arquivos if a["quantidade"] == 0) == 3
    assert all(ok for _, ok, _ in r.validacoes)


def test_base_grande_ultrapassa_1000_sem_descartar():
    linhas = [_linha(f"Cliente {chr(65 + i % 26)}{chr(65 + i // 26 % 26)}{chr(65 + i // 676 % 26)}",
                     f"55119{i:08d}", atraso=["0-30", "31-60"][i % 2]) for i in range(7000)]
    r = _rodar(linhas, hist=[])
    assert r.resumo["entregues"] == 7000
    assert any(a["quantidade"] > 1000 for a in r.arquivos)
    assert any("acima da preferência" in a for a in r.avisos)


def test_linha_com_ponto_e_virgula_extra_vira_pendencia():
    linhas = [_linha("Ana Lima", "5511911111111"), "Ana;Lima;5511922222222;1;CARTAO;0-30;Até 500;26-35;F"]
    r = _rodar(linhas, hist=[])
    assert r.resumo["pendencias"] == 1 and r.resumo["entregues"] == 1


def test_historico_excel_conversationid():
    df = pd.DataFrame({"ConversationId": ["CMP1_5511911111111_ab", "CMP2_5511911111111_cd"],
                       "Template": ["a", "b"]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    txt = (CAB + "\r\n" + _linha("Ana Lima", "5511911111111") + "\r\n" + _linha("Bia Lima", "5511922222222") + "\r\n")
    r = processar("m.txt", txt.encode(), "h.xlsx", buf.getvalue(), 2, "20260930")
    assert r.resumo["enviados"] == 1 and r.resumo["nao_enviados"] == 1
    assert r.resumo["historico_multiplos_templates"] == 1


def test_aviso_codigo_pais_sem_alterar():
    r = _rodar([_linha("Ana Lima", "11911111111")], hist=["5511911111111"])
    assert r.resumo["nao_enviados"] == 1
    assert any("55" in a for a in r.avisos)
    r2 = _rodar([_linha("Ana Lima", "11911111111")], hist=["5511911111111"], equivaler_55=True)
    assert r2.resumo["enviados"] == 1


def _rodar_hist_bruto(linhas, hist_txt):
    txt = CAB + "\r\n" + "\r\n".join(linhas) + "\r\n"
    return processar("m.txt", txt.encode("utf-8"), "h.csv", hist_txt.encode("utf-8"), 1, "20260930")


def test_historico_canal_55_sem_cabecalho():
    r = _rodar_hist_bruto([_linha("Ana Lima", "31994252095")], "136;whatsappcloud_5531994252095;2\r\n")
    assert r.resumo["enviados"] == 1 and r.resumo["nao_enviados"] == 0
    assert any("canal_55+número" in a for a in r.avisos)
    assert b"31994252095" in r.arquivos[0]["dados"] and b"5531994252095" not in r.arquivos[0]["dados"]


def test_historico_canal_e_telefone_em_colunas_separadas():
    r = _rodar_hist_bruto([_linha("Ana Lima", "31994252095")], "136;whatsappcloud_55;31994252095;2\r\n")
    assert r.resumo["enviados"] == 1 and r.resumo["nao_enviados"] == 0


def test_mailing_windows_1252():
    txt = CAB + "\r\n" + _linha("José Conceição", "5511911111111") + "\r\n"
    r = processar("m.txt", txt.encode("cp1252"), "h.csv", _hist_csv([]), 1, "20260930")
    assert "José Conceição".encode("utf-8") in r.arquivos[0]["dados"]
