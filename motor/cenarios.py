"""Criação automática dos cinco cenários a partir da distribuição real da base."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from itertools import accumulate

TOTAL_ARQUIVOS = 5
TETO_PREFERENCIAL = 1000

DIMENSOES = [
    ("faixa_atraso", "Atraso"),
    ("faixa_idade", "Idade"),
    ("faixa_saldo", "Saldo"),
    ("portfolio", "Portfólio"),
]
VAZIO = "(vazio)"


@dataclass
class Arquivo:
    status: str  # "nao_enviados" | "enviados"
    cenario_id: int
    cenario: str
    criterios: str
    parte: int
    total_partes: int
    contatos: list = field(default_factory=list)


def _rotulo(v: str) -> str:
    return v.strip() or VAZIO


def chave_ordem(v: str):
    """Ordem natural das faixas: pelo primeiro número; textos depois; vazio por último."""
    if v == VAZIO:
        return (2, 0.0, "")
    t = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", v)
    m = re.search(r"\d+(?:,\d+)?", t)
    if m:
        num = float(m.group().replace(",", "."))
        if re.search(r"(^|\s)(ATE|<|MENOS|ABAIXO)", v.upper()):
            num -= 0.5
        return (0, num, v.upper())
    return (1, 0.0, v.upper())


def _particionar(tamanhos: list[int], s: int) -> list[int] | None:
    """Divide a sequência em s grupos contíguos não vazios minimizando o maior grupo.
    Retorna os índices de corte (fim exclusivo de cada grupo)."""
    m = len(tamanhos)
    if s > m or s < 1:
        return None
    pref = [0] + list(accumulate(tamanhos))
    inf = float("inf")
    dp = [[inf] * (m + 1) for _ in range(s + 1)]
    corte = [[0] * (m + 1) for _ in range(s + 1)]
    dp[0][0] = 0
    for j in range(1, s + 1):
        for i in range(j, m - (s - j) + 1):
            melhor, arg = inf, j - 1
            for t in range(j - 1, i):
                if dp[j - 1][t] == inf:
                    continue
                v = max(dp[j - 1][t], pref[i] - pref[t])
                if v < melhor:
                    melhor, arg = v, t
            dp[j][i] = melhor
            corte[j][i] = arg
    if dp[s][m] == inf:
        return None
    fins, i = [], m
    for j in range(s, 0, -1):
        fins.append(i)
        i = corte[j][i]
    return list(reversed(fins))


def _partes(tamanhos: list[int], k: int) -> list[int]:
    p = [1] * len(tamanhos)
    for _ in range(k - len(tamanhos)):
        i = max(range(len(p)), key=lambda x: (tamanhos[x] / p[x], -x))
        p[i] += 1
    return p


def _descrever(celulas: list[tuple[str, str | None]], d1: tuple[str, str], d2, todos_v2: dict[str, set]) -> str:
    ordem: list[str] = []
    v2s: dict[str, list[str]] = {}
    for v1, v2 in celulas:
        if v1 not in v2s:
            ordem.append(v1)
            v2s[v1] = []
        if v2 is not None:
            v2s[v1].append(v2)
    partes: list[str] = []
    bloco: list[str] = []  # faixas inteiras consecutivas
    for v1 in ordem:
        if d2 is None or set(v2s[v1]) == todos_v2[v1]:
            bloco.append(v1)
            continue
        if bloco:
            partes.append(f"{d1[1]}: {', '.join(bloco)}")
            bloco = []
        partes.append(f"{d1[1]} {v1} com {d2[1]}: {', '.join(v2s[v1])}")
    if bloco:
        partes.append(f"{d1[1]}: {', '.join(bloco)}")
    return "; ".join(partes)


def dividir_status(contatos: list[dict], k: int) -> list[tuple[str, list[list[dict]]]]:
    """Divide os contatos de um status em cenários ocupando k arquivos.

    Retorna lista de (descrição_do_cenário, [partes]), com soma de partes == k.
    """
    n = len(contatos)
    if k <= 0:
        return []
    if n == 0:
        return [("Sem contatos disponíveis", [[] for _ in range(k)])]

    ideal = math.ceil(n / k)
    opcoes = []
    for i1, d1 in enumerate(DIMENSOES):
        for d2 in [None] + [d for d in DIMENSOES if d != d1]:
            opcoes.append((i1, d1, d2))

    melhor = None
    for i1, d1, d2 in opcoes:
        grupos: dict[tuple, list[dict]] = {}
        for c in contatos:
            v1 = _rotulo(c[d1[0]])
            v2 = _rotulo(c[d2[0]]) if d2 else None
            grupos.setdefault((v1, v2), []).append(c)
        if d2 is None and len(grupos) < 2:
            continue
        celulas = sorted(grupos, key=lambda x: (chave_ordem(x[0]), chave_ordem(x[1]) if x[1] else (0, 0, "")))
        tamanhos = [len(grupos[c]) for c in celulas]
        todos_v2: dict[str, set] = {}
        for v1, v2 in celulas:
            todos_v2.setdefault(v1, set()).add(v2)
        for s in range(min(k, len(celulas)), 0, -1):
            fins = _particionar(tamanhos, s)
            if fins is None:
                continue
            inicios = [0] + fins[:-1]
            tam_cen = [sum(tamanhos[a:b]) for a, b in zip(inicios, fins)]
            partes = _partes(tam_cen, k)
            maior = max(math.ceil(t / p) for t, p in zip(tam_cen, partes))
            score = maior / ideal
            score += 0.12 * (k - s)          # preferir cenários distintos a partes do mesmo cenário
            score += 0.08 if d2 else 0.0      # preferir critérios simples
            score += 0.01 * i1                # desempate: atraso, idade, saldo, portfólio
            if maior > TETO_PREFERENCIAL and ideal <= TETO_PREFERENCIAL:
                score += 0.5
            if melhor is None or score < melhor[0]:
                melhor = (score, d1, d2, celulas, grupos, inicios, fins, partes, todos_v2)

    if melhor is None:
        # Perfil único em todas as dimensões: um cenário dividido em partes.
        ordenados = sorted(contatos, key=lambda c: c["_linha"])
        return [("Todos os perfis (base sem variação suficiente para segmentar)", _fatiar(ordenados, k))]

    _, d1, d2, celulas, grupos, inicios, fins, partes, todos_v2 = melhor
    resultado = []
    for (a, b), p in zip(zip(inicios, fins), partes):
        cels = celulas[a:b]
        membros = sorted((c for cel in cels for c in grupos[cel]), key=lambda c: c["_linha"])
        desc = "Todos os perfis deste status" if len(partes) == 1 else _descrever(cels, d1, d2, todos_v2)
        resultado.append((desc, _fatiar(membros, p)))
    return resultado


def _fatiar(itens: list, p: int) -> list[list]:
    base, resto = divmod(len(itens), p)
    out, i = [], 0
    for j in range(p):
        t = base + (1 if j < resto else 0)
        out.append(itens[i:i + t])
        i += t
    return out


def alocar_arquivos(n_ne: int, n_e: int, total: int = TOTAL_ARQUIVOS) -> tuple[int, int]:
    """Quantos arquivos para NÃO ENVIADOS e ENVIADOS."""
    if n_e == 0:
        return total, 0
    if n_ne == 0:
        return 0, total
    melhor = None
    for k_ne in range(1, total):
        k_e = total - k_ne
        vazios = max(0, k_ne - n_ne) + max(0, k_e - n_e)
        maior = max(math.ceil(n_ne / k_ne), math.ceil(n_e / k_e))
        chave = (vazios, maior, -k_ne)
        if melhor is None or chave < melhor[0]:
            melhor = (chave, k_ne, k_e)
    return melhor[1], melhor[2]


def montar_arquivos(nao_enviados: list[dict], enviados: list[dict]) -> list[Arquivo]:
    k_ne, k_e = alocar_arquivos(len(nao_enviados), len(enviados))
    arquivos: list[Arquivo] = []
    cid = 0
    for status, lista, k in (("nao_enviados", nao_enviados, k_ne), ("enviados", enviados, k_e)):
        for desc, partes in dividir_status(lista, k):
            cid += 1
            for i, parte in enumerate(partes, start=1):
                arquivos.append(Arquivo(
                    status=status, cenario_id=cid, cenario=f"Cenário {cid}", criterios=desc,
                    parte=i, total_partes=len(partes), contatos=parte,
                ))
    return arquivos
