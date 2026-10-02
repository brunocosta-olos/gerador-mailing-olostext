"""Orquestração: do upload aos cinco TXT prontos para importação."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from .cenarios import TETO_PREFERENCIAL, montar_arquivos
from .geracao import CAMPANHAS, STATUS_ROTULO, campanha_do_arquivo, conteudo_txt, gerar_zip, nome_arquivo, validar_saida
from .historico import LeituraHistorico, ler_historico
from .leitura import CAMPOS, LeituraMailing, ler_mailing, nome_separador
from .telefone import chave_telefone, normalizar_telefone
from .validacao import avaliar_idade, limpar_nome

M_TELEFONE = "Sem telefone utilizável"
M_ESTRUTURA = "Estrutura da linha inválida"
MODOS_HISTORICO = {
    "telefone": "coluna de telefone",
    "conversationid": "telefone extraído do ConversationId",
    "conteudo": "coluna detectada pelo conteúdo",
}


@dataclass
class Resultado:
    arquivos: list[dict]
    resumo: dict
    exclusoes: Counter
    pendencias: Counter
    detalhes: list[dict]          # linha, categoria, motivos (sem dados pessoais)
    validacoes: list[tuple[str, bool, str]]
    avisos: list[str]
    zip_bytes: bytes
    leitura_mailing: LeituraMailing
    leitura_historico: LeituraHistorico
    explicacao: str = ""
    extras: dict = field(default_factory=dict)


def data_do_nome(nome_arquivo: str) -> date | None:
    """Data explícita no nome do arquivo (AAAAMMDD, AAAA-MM-DD, DD-MM-AAAA ou DDMMAAAA)."""
    padroes = [
        (r"(?<!\d)(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})(?!\d)", (0, 1, 2)),
        (r"(?<!\d)(\d{2})[-_.]?(\d{2})[-_.]?(20\d{2})(?!\d)", (2, 1, 0)),
    ]
    for rx, (ia, im, idd) in padroes:
        for m in re.finditer(rx, nome_arquivo):
            g = m.groups()
            try:
                return date(int(g[ia]), int(g[im]), int(g[idd]))
            except ValueError:
                continue
    return None


def _completude(c: dict) -> int:
    return sum(1 for campo in CAMPOS if c[campo].strip())


def processar(
    mailing_nome: str,
    mailing_bytes: bytes,
    historico_nome: str,
    historico_bytes: bytes,
    qtd_numeros: int,
    data_base: str,
    coluna_historico: str | None = None,
    equivaler_55: bool = False,
) -> Resultado:
    if qtd_numeros not in CAMPANHAS:
        raise ValueError("A quantidade de números disponíveis deve ser de 1 a 4.")
    if not re.fullmatch(r"\d{8}", data_base):
        raise ValueError("A data da base deve estar no formato AAAAMMDD.")

    lm = ler_mailing(mailing_bytes)
    lh = ler_historico(historico_nome, historico_bytes, coluna_historico)
    hist_chaves = {chave_telefone(t, equivaler_55) for t in lh.telefones}
    hist_sem_55 = {chave_telefone(t, True) for t in lh.telefones}

    exclusoes: Counter = Counter()
    pendencias: Counter = Counter()
    detalhes: list[dict] = []
    elegiveis: list[dict] = []
    total_excluidos = total_pendentes = 0

    for reg in lm.registros:
        if reg.problema_estrutura:
            pendencias[M_ESTRUTURA] += 1
            total_pendentes += 1
            detalhes.append({"linha": reg.linha, "categoria": "Pendência", "motivos": reg.problema_estrutura})
            continue

        campos = {k: v.strip() for k, v in reg.campos.items()}
        motivos_exc: list[str] = []
        motivos_pend: list[str] = []

        nome, m_nome = limpar_nome(campos["nome"])
        if m_nome:
            motivos_exc.append(m_nome)

        situacao, m_idade = avaliar_idade(campos["faixa_idade"])
        if situacao == "excluir":
            motivos_exc.append(m_idade)
        elif situacao == "pendente":
            motivos_pend.append(m_idade)

        digitos, m_tel = normalizar_telefone(campos["telefone"])
        if m_tel:
            motivos_exc.append(f"{M_TELEFONE}: {m_tel.lower()}")

        if motivos_exc:
            total_excluidos += 1
            for m in motivos_exc:
                exclusoes[m] += 1
            detalhes.append({"linha": reg.linha, "categoria": "Excluído", "motivos": "; ".join(motivos_exc + motivos_pend)})
            continue
        if motivos_pend:
            total_pendentes += 1
            for m in motivos_pend:
                pendencias[m] += 1
            detalhes.append({"linha": reg.linha, "categoria": "Pendência", "motivos": "; ".join(motivos_pend)})
            continue

        campos["nome"] = nome
        campos["_linha"] = reg.linha
        campos["_chave"] = chave_telefone(digitos, equivaler_55)
        campos["_digitos"] = digitos
        elegiveis.append(campos)

    # Deduplicação: mais completo; em empate, primeira ocorrência.
    por_chave: dict[str, dict] = {}
    for c in elegiveis:
        atual = por_chave.get(c["_chave"])
        if atual is None or _completude(c) > _completude(atual):
            por_chave[c["_chave"]] = c
    unicos = sorted(por_chave.values(), key=lambda c: c["_linha"])
    mantidos = {id(c) for c in unicos}
    duplicatas = 0
    for c in elegiveis:
        if id(c) not in mantidos:
            duplicatas += 1
            detalhes.append({"linha": c["_linha"], "categoria": "Duplicata removida", "motivos": "Telefone repetido na base"})

    nao_enviados = [c for c in unicos if c["_chave"] not in hist_chaves]
    enviados = [c for c in unicos if c["_chave"] in hist_chaves]

    avisos = list(lm.avisos) + list(lh.avisos)
    if not equivaler_55:
        potenciais = sum(1 for c in nao_enviados if chave_telefone(c["_digitos"], True) in hist_sem_55)
        if potenciais:
            avisos.append(
                f"{potenciais} telefone(s) NÃO ENVIADOS só coincidem com o histórico se '55' for considerado "
                "equivalente à ausência do código do país. Nada foi alterado; se forem o mesmo número, "
                "ative a opção correspondente nas opções avançadas e processe novamente."
            )

    # Cenários e arquivos
    blocos = montar_arquivos(nao_enviados, enviados)
    arquivos: list[dict] = []
    for i, b in enumerate(blocos):
        dados = conteudo_txt(b.contatos)
        nome_arq = nome_arquivo(i, qtd_numeros, data_base, b.status)
        cenario = b.cenario + (f" — parte {b.parte} de {b.total_partes}" if b.total_partes > 1 else "")
        arquivos.append({
            "nome": nome_arq,
            "campanha": campanha_do_arquivo(i, qtd_numeros),
            "prefixo": CAMPANHAS[campanha_do_arquivo(i, qtd_numeros)],
            "status": b.status,
            "status_rotulo": STATUS_ROTULO[b.status],
            "cenario": cenario,
            "criterios": b.criterios,
            "quantidade": len(b.contatos),
            "dados": dados,
        })

    grandes = [a for a in arquivos if a["quantidade"] > TETO_PREFERENCIAL]
    vazios = [a for a in arquivos if a["quantidade"] == 0]
    for a in grandes:
        avisos.append(
            f"{a['nome']} tem {a['quantidade']} contatos (acima da preferência de {TETO_PREFERENCIAL}): "
            "o volume elegível do status não cabe em arquivos menores sem descartar contatos."
        )
    if vazios:
        avisos.append(
            f"{len(vazios)} arquivo(s) vazio(s): não há contatos elegíveis suficientes para cinco arquivos "
            "não vazios. Nenhum contato foi duplicado e nenhuma exclusão foi relaxada."
        )

    validacoes = validar_saida(arquivos, qtd_numeros, lh.telefones, len(unicos), equivaler_55)

    recebidos = len(lm.registros)
    entregues = sum(a["quantidade"] for a in arquivos)
    resumo = {
        "recebidos": recebidos,
        "linhas_vazias_ignoradas": lm.linhas_vazias,
        "excluidos": total_excluidos,
        "pendencias": total_pendentes,
        "duplicatas": duplicatas,
        "elegiveis_unicos": len(unicos),
        "entregues": entregues,
        "nao_enviados": len(nao_enviados),
        "enviados": len(enviados),
        "reconciliado": recebidos == total_excluidos + total_pendentes + duplicatas + entregues,
        "mailing_formato": (
            f"{lm.codificacao}, separador {nome_separador(lm.separador)}, "
            f"{'com' if lm.tem_cabecalho else 'sem'} cabeçalho"
        ),
        "colunas_auxiliares": lm.colunas_auxiliares,
        "historico_formato": lh.formato,
        "historico_coluna": f"{lh.coluna_usada} ({MODOS_HISTORICO[lh.modo]})",
        "historico_linhas": lh.linhas,
        "historico_telefones_unicos": len(lh.telefones),
        "historico_templates": lh.templates_distintos,
        "historico_multiplos_templates": lh.telefones_multiplos_templates,
        "data_base": data_base,
        "qtd_numeros": qtd_numeros,
        "equivaler_55": equivaler_55,
    }

    explicacao = _explicar(arquivos, len(nao_enviados), len(enviados))
    zip_bytes = gerar_zip([(a["nome"], a["dados"]) for a in arquivos])
    detalhes.sort(key=lambda d: d["linha"])

    return Resultado(
        arquivos=arquivos, resumo=resumo, exclusoes=exclusoes, pendencias=pendencias,
        detalhes=detalhes, validacoes=validacoes, avisos=avisos, zip_bytes=zip_bytes,
        leitura_mailing=lm, leitura_historico=lh, explicacao=explicacao,
    )


def _explicar(arquivos: list[dict], n_ne: int, n_e: int) -> str:
    k_ne = sum(1 for a in arquivos if a["status"] == "nao_enviados")
    k_e = len(arquivos) - k_ne
    partes = []
    if n_ne and n_e:
        partes.append(
            f"Os {n_ne} NÃO ENVIADOS ocupam os arquivos 1 a {k_ne} (prioridade de uso) e os {n_e} ENVIADOS "
            f"ocupam os arquivos {k_ne + 1} a 5, reservados para a etapa posterior. A quantidade de arquivos "
            "por status foi escolhida para deixar o maior arquivo o menor possível."
        )
    elif n_ne:
        partes.append("Todos os contatos elegíveis são NÃO ENVIADOS; os cinco arquivos foram distribuídos dentro desse status.")
    elif n_e:
        partes.append("Todos os contatos elegíveis são ENVIADOS; os cinco arquivos foram distribuídos dentro desse status.")
    else:
        partes.append("Não há contatos elegíveis; os cinco arquivos estão vazios.")
    partes.append(
        "Dentro de cada status, os cenários agrupam faixas consecutivas da dimensão (atraso, idade, saldo ou "
        "portfólio) que produz os volumes mais equilibrados, usando a distribuição real da base. Quando um "
        "cenário precisa de mais de um arquivo, as partes têm o mesmo perfil e foram divididas apenas por volume. "
        "A divisão é operacional: não pressupõe maior probabilidade de resposta de nenhum perfil."
    )
    return " ".join(partes)
