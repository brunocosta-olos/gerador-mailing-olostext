"""Leitura do histórico de envios (Excel, CSV ou TXT) e extração de telefones."""

from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass, field

from .leitura import ErroLeitura, decodificar, detectar_separador, ler_tabela_texto, normalizar_coluna, nome_separador
from .telefone import candidatos_em_texto, extrair_telefone_canal, normalizar_telefone

ALIASES_TELEFONE = {
    "telefone", "phone", "phonenumber", "phone_number", "fone", "celular", "numero", "numero_telefone",
    "msisdn", "destino", "destinatario", "to", "contato", "whatsapp", "wa_id", "tel",
}
ALIASES_CONVERSATION = {"conversationid", "conversation_id", "id_conversa", "conversation"}
ALIASES_TEMPLATE = {"template", "templatename", "template_name", "modelo", "hsm"}
ALIASES_CAMPANHA = {"campanha", "campaign", "campaignname", "campaign_name"}
ALIASES_QTD = {"quantidade", "qtd", "qtde", "count", "total"}


@dataclass
class LeituraHistorico:
    telefones: set[str]
    formato: str
    colunas: list[str]
    coluna_usada: str
    modo: str  # "telefone" | "conversationid" | "conteudo"
    linhas: int = 0
    linhas_sem_telefone: int = 0
    ambiguos: int = 0
    templates_distintos: int | None = None
    telefones_multiplos_templates: int | None = None
    avisos: list[str] = field(default_factory=list)


def _ler_bruto(nome_arquivo: str, dados: bytes) -> tuple[list[str], list[list[str]], str, bool]:
    """Retorna (cabeçalho, linhas, descrição do formato, veio_do_excel)."""
    nome = nome_arquivo.lower()
    if nome.endswith((".xlsx", ".xlsm", ".xls")):
        import pandas as pd

        try:
            planilhas = pd.read_excel(io.BytesIO(dados), dtype=str, sheet_name=None, header=None)
        except Exception as exc:  # noqa: BLE001
            raise ErroLeitura(f"Não foi possível ler o Excel do histórico: {exc}") from exc
        nomes = [n for n, df in planilhas.items() if not df.dropna(how="all").empty]
        if not nomes:
            raise ErroLeitura("O Excel do histórico não tem dados.")
        df = planilhas[nomes[0]].fillna("")
        linhas = [[str(c) for c in row] for row in df.values.tolist()]
        linhas = [l for l in linhas if any(c.strip() for c in l)]
        fmt = f"Excel (aba '{nomes[0]}')"
        if len(nomes) > 1:
            fmt += f" — atenção: outras abas com dados foram ignoradas: {', '.join(map(str, nomes[1:]))}"
        return _separar_cabecalho(linhas) + (fmt, True)

    texto, cod = decodificar(dados)
    sep = detectar_separador(texto)
    linhas = [l for _, l in ler_tabela_texto(texto, sep) if any(c.strip() for c in l)]
    if not linhas:
        raise ErroLeitura("O arquivo de histórico está vazio.")
    fmt = f"Texto {cod}, separador {nome_separador(sep)}"
    return _separar_cabecalho(linhas) + (fmt, False)


def _parece_telefone(v: str) -> bool:
    if extrair_telefone_canal(v) is not None:
        return True
    d, _ = normalizar_telefone(v, origem_excel=True)
    return d is not None


def _separar_cabecalho(linhas: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    primeira = linhas[0]
    nomes_conhecidos = ALIASES_TELEFONE | ALIASES_CONVERSATION | ALIASES_TEMPLATE | ALIASES_CAMPANHA | ALIASES_QTD
    tem_nome = any(normalizar_coluna(c) in nomes_conhecidos for c in primeira)
    tem_tel = any(_parece_telefone(c) for c in primeira)
    if tem_nome or not tem_tel:
        cab = [c.strip() or f"coluna {i + 1}" for i, c in enumerate(primeira)]
        return cab, linhas[1:]
    ncols = max(len(l) for l in linhas)
    return [f"coluna {i + 1}" for i in range(ncols)], linhas


def _achar(cab: list[str], aliases: set[str]) -> int | None:
    for i, c in enumerate(cab):
        if normalizar_coluna(c) in aliases:
            return i
    return None


def colunas_do_historico(nome_arquivo: str, dados: bytes) -> list[str]:
    cab, _, _, _ = _ler_bruto(nome_arquivo, dados)
    return cab


def ler_historico(nome_arquivo: str, dados: bytes, coluna_forcada: str | None = None) -> LeituraHistorico:
    cab, linhas, fmt, excel = _ler_bruto(nome_arquivo, dados)
    avisos: list[str] = []

    def valor(l: list[str], i: int) -> str:
        return l[i] if i < len(l) else ""

    idx, modo = None, None
    if coluna_forcada:
        if coluna_forcada not in cab:
            raise ErroLeitura(f"A coluna '{coluna_forcada}' não existe no histórico.")
        idx = cab.index(coluna_forcada)
        n = normalizar_coluna(coluna_forcada)
        modo = "conversationid" if n in ALIASES_CONVERSATION else "telefone"
        # Coluna escolhida que não é de telefone puro: extrai de dentro do texto.
        amostra = [valor(l, idx) for l in linhas[:200] if valor(l, idx).strip()]
        if amostra and sum(_parece_telefone(v) for v in amostra) / len(amostra) < 0.5:
            modo = "conversationid"
    else:
        idx = _achar(cab, ALIASES_TELEFONE)
        modo = "telefone"
        if idx is None:
            idx = _achar(cab, ALIASES_CONVERSATION)
            modo = "conversationid"
        if idx is None:
            # Detecção pelo conteúdo: coluna com >= 80% de valores com formato de telefone.
            melhor, melhor_taxa = None, 0.0
            for i in range(len(cab)):
                amostra = [valor(l, i) for l in linhas[:500] if valor(l, i).strip()]
                if not amostra:
                    continue
                taxa = sum(_parece_telefone(v) for v in amostra) / len(amostra)
                if taxa > melhor_taxa:
                    melhor, melhor_taxa = i, taxa
            if melhor is not None and melhor_taxa >= 0.8:
                idx, modo = melhor, "conteudo"
                avisos.append(
                    f"Nenhuma coluna de telefone identificada pelo nome; usada a coluna '{cab[melhor]}' "
                    f"porque {melhor_taxa:.0%} dos valores têm formato de telefone. Confira."
                )
        if idx is None:
            raise ErroLeitura(
                "Não foi possível identificar a coluna de telefone ou ConversationId no histórico. "
                "Colunas encontradas: " + ", ".join(cab) + ". Escolha a coluna manualmente nas opções avançadas."
            )

    telefones: set[str] = set()
    sem_tel = ambiguos = canal_55 = 0
    idx_tpl = _achar(cab, ALIASES_TEMPLATE)
    tpl_por_tel: dict[str, set[str]] = {}

    for l in linhas:
        bruto = valor(l, idx)
        tel = extrair_telefone_canal(bruto)
        if tel is not None:
            canal_55 += 1
        elif modo in ("telefone", "conteudo"):
            tel, _ = normalizar_telefone(bruto, origem_excel=excel)
            if tel is None and bruto.strip():
                cands = candidatos_em_texto(bruto)
                if len(cands) == 1:
                    tel = cands[0]
                elif len(cands) > 1:
                    ambiguos += 1
                    continue
        else:
            cands = candidatos_em_texto(bruto)
            if len(cands) == 1:
                tel = cands[0]
            elif len(cands) > 1:
                ambiguos += 1
                continue
        if tel is None:
            sem_tel += 1
            continue
        telefones.add(tel)
        if idx_tpl is not None:
            t = valor(l, idx_tpl).strip()
            if t:
                tpl_por_tel.setdefault(tel, set()).add(t)

    if modo == "conversationid" and not telefones:
        raise ErroLeitura(
            f"A coluna '{cab[idx]}' não permite identificar telefones de forma inequívoca. "
            "Escolha outra coluna nas opções avançadas."
        )
    if canal_55:
        avisos.append(
            f"{canal_55} linha(s) do histórico no formato canal_55+número: prefixo e código do país "
            "removidos para comparação."
        )
    if ambiguos:
        avisos.append(
            f"{ambiguos} linha(s) do histórico com mais de um número possível no mesmo campo foram ignoradas "
            "(extração ambígua)."
        )
    if sem_tel:
        avisos.append(f"{sem_tel} linha(s) do histórico sem telefone identificável foram ignoradas.")

    info = LeituraHistorico(
        telefones=telefones,
        formato=fmt,
        colunas=cab,
        coluna_usada=cab[idx],
        modo=modo,
        linhas=len(linhas),
        linhas_sem_telefone=sem_tel,
        ambiguos=ambiguos,
        avisos=avisos,
    )
    if idx_tpl is not None:
        todos = Counter(t for s in tpl_por_tel.values() for t in s)
        info.templates_distintos = len(todos)
        info.telefones_multiplos_templates = sum(1 for s in tpl_por_tel.values() if len(s) > 1)
    return info
