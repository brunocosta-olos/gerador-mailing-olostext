"""Regras de validação de nome e faixa etária."""

from __future__ import annotations

import math
import re
import unicodedata

from .leitura import sem_acento

IDADE_CORTE = 66  # 66 anos ou mais: excluir

APOSTROFOS = "'’‘`´ʼ"
HIFENS = "-‐‑‒–—"

NOMES_INVALIDOS = {
    "TESTE", "TEST", "NULL", "NONE", "NAN", "NA", "N A", "ND", "N D", "XXX", "XXXX", "SEM NOME",
    "NAO INFORMADO", "NAO INFORMADA", "DESCONHECIDO", "CLIENTE", "UNDEFINED", "ASDF", "FULANO",
}
TOKENS_INVALIDOS = {"TESTE", "TEST", "NULL", "UNDEFINED", "NAN"}

# --- Motivos (textos usados nos relatórios) ---
M_NOME_VAZIO = "Nome vazio"
M_NOME_NUMERO = "Nome contém número"
M_NOME_SIMBOLO = "Nome contém símbolos ou caracteres inválidos"
M_NOME_INVALIDO = "Nome não constitui um nome válido"
M_IDADE_AUSENTE = "Idade/faixa etária ausente"
M_IDADE_66 = "Idade de 66 anos ou mais"
P_IDADE_CRUZA = "Faixa etária atravessa o corte de 66 anos"
P_IDADE_ININTELIGIVEL = "Faixa etária impossível de interpretar"


def limpar_nome(bruto: str) -> tuple[str | None, str | None]:
    """Retorna (nome_limpo, motivo_exclusão)."""
    n = unicodedata.normalize("NFC", bruto or "")
    n = re.sub(r"\s+", " ", n).strip()
    if not n:
        return None, M_NOME_VAZIO
    if any(ch.isdigit() for ch in n):
        return None, M_NOME_NUMERO
    for c in APOSTROFOS:
        n = n.replace(c, "")
    for c in HIFENS:
        n = n.replace(c, " ")
    n = re.sub(r"\s+", " ", n).strip()
    if not n or not all(ch.isalpha() or ch == " " for ch in n):
        return None, M_NOME_SIMBOLO
    base = sem_acento(n).upper()
    letras = base.replace(" ", "")
    if (
        base in NOMES_INVALIDOS
        or any(tok in TOKENS_INVALIDOS for tok in base.split())
        or len(letras) < 2
        or len(set(letras)) == 1
    ):
        return None, M_NOME_INVALIDO
    return n, None


_AUSENTES = {
    "", "NULL", "NONE", "NAN", "N/A", "NA", "-", "--", "ND", "N/D", "SEM INFORMACAO",
    "NAO INFORMADO", "NAO INFORMADA", "DESCONHECIDO", "DESCONHECIDA", "SEM IDADE",
}


def interpretar_faixa_idade(valor: str) -> tuple[float | None, float | None]:
    """Retorna (mínimo, máximo) da faixa. (None, None) se impossível de interpretar.

    Exemplos: '18-25' -> (18, 25); '75+' -> (75, inf); 'acima de 65' -> (66, inf);
    'até 25' -> (0, 25); '<25' -> (0, 24); '40' -> (40, 40).
    """
    s = sem_acento(valor or "").upper().strip()
    s = re.sub(r"(\d+)[.,]0+\b", r"\1", s)
    if re.search(r"\d[.,]\d", s):
        return None, None
    nums = [int(x) for x in re.findall(r"\d+", s)]
    if not nums or len(nums) > 2:
        return None, None

    estrito_mais = re.search(r">(?!=)|ACIMA DE|MAIS DE|MAIOR QUE|MAIOR DE|SUPERIOR A", s)
    mais = estrito_mais or re.search(r"\+|>=|OU MAIS|ACIMA|MAIS", s)
    estrito_menos = re.search(r"<(?!=)|MENOS DE|ABAIXO DE|MENOR QUE|MENOR DE|INFERIOR A", s)
    menos = estrito_menos or re.search(r"<=|\bATE\b|ABAIXO|MENOS", s)

    if len(nums) == 2:
        if mais or menos:
            return None, None
        lo, hi = nums
        if lo > hi:
            return None, None
    else:
        n = nums[0]
        if mais and menos:
            return None, None
        if mais:
            lo, hi = (n + 1 if estrito_mais else n), math.inf
        elif menos:
            lo, hi = 0, (n - 1 if estrito_menos else n)
        else:
            lo = hi = n
    if hi < 1 or lo > 120:
        return None, None
    return lo, hi


def avaliar_idade(valor: str) -> tuple[str, str | None]:
    """Retorna (situação, motivo). Situação: 'ok' | 'excluir' | 'pendente'."""
    s = sem_acento(valor or "").upper().strip()
    if s in _AUSENTES:
        return "excluir", M_IDADE_AUSENTE
    lo, hi = interpretar_faixa_idade(valor)
    if lo is None:
        return "pendente", P_IDADE_ININTELIGIVEL
    if lo >= IDADE_CORTE:
        return "excluir", M_IDADE_66
    if hi < IDADE_CORTE:
        return "ok", None
    return "pendente", P_IDADE_CRUZA
