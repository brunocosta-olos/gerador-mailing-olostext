"""Leitura de arquivos: codificação, separador, cabeçalho e estrutura."""

from __future__ import annotations

import codecs
import csv
import io
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

CAMPOS = [
    "nome", "telefone", "customerid", "portfolio",
    "faixa_atraso", "faixa_saldo", "faixa_idade", "genero",
]

# Nomes de coluna aceitos para cada campo (após normalização: minúsculas, sem acento, "_").
ALIASES_MAILING = {
    "nome": {"nome", "name", "nome_cliente"},
    "telefone": {"telefone", "phone", "fone", "celular", "tel"},
    "customerid": {"customerid", "customer_id", "id_cliente", "idcliente"},
    "portfolio": {"portfolio", "portifolio", "carteira"},
    "faixa_atraso": {"faixa_atraso", "faixaatraso", "atraso"},
    "faixa_saldo": {"faixa_saldo", "faixasaldo", "saldo"},
    "faixa_idade": {"faixa_idade", "faixaidade", "idade", "faixa_etaria"},
    "genero": {"genero", "sexo", "gender"},
}


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_coluna(nome: str) -> str:
    n = sem_acento(str(nome)).strip().lower()
    n = re.sub(r"[^a-z0-9]+", "_", n)
    return n.strip("_")


def decodificar(dados: bytes) -> tuple[str, str]:
    """Retorna (texto, descrição da codificação)."""
    if dados.startswith(codecs.BOM_UTF8):
        return dados[3:].decode("utf-8", errors="strict"), "UTF-8 com BOM"
    if dados.startswith(codecs.BOM_UTF16_LE) or dados.startswith(codecs.BOM_UTF16_BE):
        return dados.decode("utf-16"), "UTF-16"
    try:
        return dados.decode("utf-8"), "UTF-8"
    except UnicodeDecodeError:
        pass
    try:
        return dados.decode("cp1252"), "Windows-1252"
    except UnicodeDecodeError:
        return dados.decode("latin-1"), "ISO-8859-1"


def detectar_separador(texto: str) -> str:
    linhas = [l for l in texto.splitlines() if l.strip()][:50]
    if not linhas:
        return ";"
    melhor, melhor_score = ";", -1.0
    for sep in [";", ",", "\t", "|"]:
        contagens = [l.count(sep) for l in linhas]
        if max(contagens) == 0:
            continue
        moda, freq = Counter(contagens).most_common(1)[0]
        if moda == 0:
            continue
        score = freq / len(linhas) + (0.01 if sep == ";" else 0)
        if score > melhor_score:
            melhor, melhor_score = sep, score
    return melhor


def nome_separador(sep: str) -> str:
    return {";": "ponto e vírgula (;)", ",": "vírgula (,)", "\t": "tabulação", "|": "barra vertical (|)"}.get(sep, sep)


def ler_tabela_texto(texto: str, sep: str) -> list[tuple[int, list[str]]]:
    """Lê linhas como listas de campos, com o número da linha original (1-based)."""
    usa_aspas = re.search(r'(^|[' + re.escape(sep) + r'])"', texto, flags=re.M) is not None
    kwargs = {"delimiter": sep}
    if usa_aspas:
        kwargs["quotechar"] = '"'
    else:
        kwargs["quoting"] = csv.QUOTE_NONE
    leitor = csv.reader(io.StringIO(texto, newline=""), **kwargs)
    linhas = []
    inicio = 1
    for linha in leitor:
        linhas.append((inicio, linha))
        inicio = leitor.line_num + 1
    return linhas


@dataclass
class RegistroMailing:
    linha: int
    campos: dict[str, str]
    problema_estrutura: str | None = None


@dataclass
class LeituraMailing:
    registros: list[RegistroMailing]
    codificacao: str
    separador: str
    tem_cabecalho: bool
    colunas_auxiliares: list[str] = field(default_factory=list)
    linhas_vazias: int = 0
    avisos: list[str] = field(default_factory=list)


class ErroLeitura(Exception):
    pass


def _mapear_cabecalho(cabecalho: list[str]) -> dict[str, int]:
    mapa: dict[str, int] = {}
    for idx, col in enumerate(cabecalho):
        n = normalizar_coluna(col)
        for campo, aliases in ALIASES_MAILING.items():
            if n in aliases and campo not in mapa:
                mapa[campo] = idx
    return mapa


def ler_mailing(dados: bytes) -> LeituraMailing:
    texto, codificacao = decodificar(dados)
    sep = detectar_separador(texto)
    linhas = ler_tabela_texto(texto, sep)

    nao_vazias = [(n, l) for n, l in linhas if any(c.strip() for c in l)]
    vazias = len(linhas) - len(nao_vazias)
    if not nao_vazias:
        raise ErroLeitura("O arquivo de mailing está vazio.")

    primeira = nao_vazias[0][1]
    mapa = _mapear_cabecalho(primeira)
    tem_cabecalho = len(mapa) >= 3
    avisos: list[str] = []

    if tem_cabecalho:
        faltando = [c for c in CAMPOS if c not in mapa]
        if faltando:
            raise ErroLeitura(
                "Cabeçalho encontrado, mas faltam os campos obrigatórios: " + ", ".join(faltando)
            )
        ncols = len(primeira)
        auxiliares = [primeira[i].strip() for i in range(ncols) if i not in mapa.values()]
        dados_linhas = nao_vazias[1:]
    else:
        contagens = Counter(len(l) for _, l in nao_vazias)
        ncols = contagens.most_common(1)[0][0]
        if ncols < 8:
            raise ErroLeitura(
                f"Arquivo sem cabeçalho com {ncols} colunas; são necessários os 8 campos "
                "nome;telefone;customerid;portfolio;faixa_atraso;faixa_saldo;faixa_idade;genero."
            )
        mapa = {campo: i for i, campo in enumerate(CAMPOS)}
        auxiliares = [f"coluna {i + 1}" for i in range(8, ncols)]
        if auxiliares:
            avisos.append(
                f"Arquivo sem cabeçalho com {ncols} colunas: as 8 primeiras foram lidas na ordem "
                f"padrão e {len(auxiliares)} coluna(s) excedente(s) foram tratadas como auxiliares e ignoradas."
            )
        dados_linhas = nao_vazias

    max_idx_obrig = max(mapa.values())
    registros: list[RegistroMailing] = []
    for num, cel in dados_linhas:
        problema = None
        if len(cel) > ncols and any(c.strip() for c in cel[ncols:]):
            problema = (f"Linha com {len(cel)} campos (esperado {ncols}); possível ponto e vírgula "
                        "dentro de um campo")
        elif len(cel) <= max_idx_obrig:
            problema = f"Linha com {len(cel)} campos (esperado {ncols}); campos obrigatórios ausentes"
        cel = list(cel) + [""] * max(0, ncols - len(cel))
        campos = {campo: cel[idx] for campo, idx in mapa.items()}
        if problema is None:
            for campo, valor in campos.items():
                if "\n" in valor or "\r" in valor:
                    problema = f"Quebra de linha dentro do campo {campo}"
                    break
                if "\t" in valor.strip():
                    problema = f"Tabulação dentro do campo {campo}"
                    break
                if ";" in valor:
                    problema = f"Ponto e vírgula dentro do campo {campo}"
                    break
        registros.append(RegistroMailing(linha=num, campos=campos, problema_estrutura=problema))

    return LeituraMailing(
        registros=registros,
        codificacao=codificacao,
        separador=sep,
        tem_cabecalho=tem_cabecalho,
        colunas_auxiliares=auxiliares,
        linhas_vazias=vazias,
        avisos=avisos,
    )
