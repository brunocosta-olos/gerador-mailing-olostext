"""Nomes, prefixos, conteúdo dos TXT e validações finais."""

from __future__ import annotations

import io
import zipfile

from .leitura import CAMPOS
from .telefone import chave_telefone, normalizar_telefone
from .validacao import avaliar_idade, limpar_nome

CAMPANHAS = {
    1: "BOT_WPP_Massivo_",
    2: "BOT_WPP_Return_",
    3: "BOT_WPP_ATIVO_",
    4: "BOT_ATIVO_RETURN_",
}
STATUS_ROTULO = {"nao_enviados": "NÃO ENVIADO", "enviados": "ENVIADO"}


def campanha_do_arquivo(indice: int, qtd_numeros: int) -> int:
    """indice começa em 0. Distribuição cíclica entre as campanhas disponíveis."""
    return (indice % qtd_numeros) + 1


def nome_arquivo(indice: int, qtd_numeros: int, data_base: str, status: str) -> str:
    prefixo = CAMPANHAS[campanha_do_arquivo(indice, qtd_numeros)]
    return f"{prefixo}base{data_base}_{indice + 1:02d}_{status}.txt"


def conteudo_txt(contatos: list[dict]) -> bytes:
    linhas = [";".join(c[campo] for campo in CAMPOS) for c in contatos]
    texto = "".join(l + "\r\n" for l in linhas)
    return texto.encode("utf-8")  # UTF-8 sem BOM


def gerar_zip(arquivos: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, dados in arquivos:
            z.writestr(nome, dados)
    return buf.getvalue()


def validar_saida(
    arquivos: list[dict], qtd_numeros: int, telefones_historico: set[str], total_elegiveis: int,
    equivaler_55: bool,
) -> list[tuple[str, bool, str]]:
    """Relê os bytes gerados e confere as regras. Retorna [(checagem, ok, detalhe)]."""
    checks: list[tuple[str, bool, str]] = []
    hist = {chave_telefone(t, equivaler_55) for t in telefones_historico}
    erros = {k: [] for k in [
        "bom", "crlf", "campos", "cabecalho", "nome", "idade", "tel_arquivo", "status",
        "prefixo", "contagem", "vazias", "tab",
    ]}
    vistos_global: dict[str, str] = {}
    repetidos_entre = 0
    soma = 0
    prefixos_validos = {CAMPANHAS[i] for i in range(1, qtd_numeros + 1)}

    if len(arquivos) != 5:
        checks.append(("Exatamente cinco arquivos", False, f"{len(arquivos)} arquivos gerados"))
    else:
        checks.append(("Exatamente cinco arquivos", True, "5 arquivos"))

    for idx, arq in enumerate(arquivos):
        nome, dados = arq["nome"], arq["dados"]
        if dados.startswith(b"\xef\xbb\xbf"):
            erros["bom"].append(nome)
        texto = dados.decode("utf-8")
        if texto.replace("\r\n", "").count("\n") or texto.replace("\r\n", "").count("\r"):
            erros["crlf"].append(nome)
        if texto and not texto.endswith("\r\n"):
            erros["crlf"].append(nome)
        linhas = texto.split("\r\n")[:-1] if texto else []
        if len(linhas) != arq["quantidade"]:
            erros["contagem"].append(f"{nome} ({len(linhas)} linhas, anunciado {arq['quantidade']})")
        soma += len(linhas)
        esperado_prefixo = CAMPANHAS[campanha_do_arquivo(idx, qtd_numeros)]
        if not nome.startswith(esperado_prefixo) or not any(nome.startswith(p) for p in prefixos_validos):
            erros["prefixo"].append(nome)
        vistos_arquivo: set[str] = set()
        for n_linha, linha in enumerate(linhas, start=1):
            if not linha.strip():
                erros["vazias"].append(f"{nome}:{n_linha}")
                continue
            if "\t" in linha:
                erros["tab"].append(f"{nome}:{n_linha}")
            partes = linha.split(";")
            if len(partes) != 8:
                erros["campos"].append(f"{nome}:{n_linha}")
                continue
            if [p.strip().lower() for p in partes] == CAMPOS:
                erros["cabecalho"].append(nome)
            nome_ok, _ = limpar_nome(partes[0])
            if nome_ok is None or nome_ok != partes[0]:
                erros["nome"].append(f"{nome}:{n_linha}")
            situacao, _ = avaliar_idade(partes[6])
            if situacao != "ok":
                erros["idade"].append(f"{nome}:{n_linha}")
            dig, _ = normalizar_telefone(partes[1])
            chave = chave_telefone(dig, equivaler_55) if dig else partes[1]
            if chave in vistos_arquivo:
                erros["tel_arquivo"].append(f"{nome}:{n_linha}")
            elif chave in vistos_global:
                repetidos_entre += 1
            vistos_arquivo.add(chave)
            vistos_global.setdefault(chave, nome)
            enviado = chave in hist
            if enviado != (arq["status"] == "enviados"):
                erros["status"].append(f"{nome}:{n_linha}")

    def add(rotulo, chave, detalhe_ok="OK"):
        lst = erros[chave]
        checks.append((rotulo, not lst, detalhe_ok if not lst else f"{len(lst)} ocorrência(s): " + ", ".join(lst[:5])))

    add("UTF-8 sem BOM", "bom")
    add("Quebras de linha CRLF (Windows)", "crlf")
    add("Exatamente oito campos por linha", "campos")
    add("Sem cabeçalho", "cabecalho")
    add("Sem linhas vazias", "vazias")
    add("Sem tabulações", "tab")
    add("Nomes válidos conforme as regras", "nome")
    add("Sem idade ausente, 66+ ou faixa ambígua", "idade")
    add("Sem telefone repetido dentro do arquivo", "tel_arquivo")
    checks.append((
        "Sem telefone repetido entre arquivos", repetidos_entre == 0,
        "OK" if repetidos_entre == 0 else f"{repetidos_entre} repetição(ões)",
    ))
    add("Um único status de envio por arquivo", "status")
    add("Prefixos compatíveis com a quantidade de números", "prefixo")
    add("Linhas de cada arquivo = volume anunciado", "contagem")
    checks.append((
        "Soma dos arquivos = total de elegíveis únicos", soma == total_elegiveis,
        f"{soma} entregues / {total_elegiveis} elegíveis únicos",
    ))
    return checks
