"""Normalização de telefones para comparação (sem inventar dígitos)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

MIN_DIGITOS = 10  # DDD + 8 dígitos
MAX_DIGITOS = 13  # 55 + DDD + 9 dígitos

_PERMITIDOS = re.compile(r"^[\d\s+()\-.]+$")
_CIENTIFICA = re.compile(r"^[+-]?\d+(?:[.,]\d+)?[eE][+-]?\d+$")
_CANAL_55 = re.compile(r"^[A-Za-z][A-Za-z0-9]*_55(\d{10,11})$", re.IGNORECASE)


def extrair_telefone_canal(valor: str) -> str | None:
    """Histórico no formato '<canal>_55<DDD><número>' (ex.: whatsappcloud_5531994252095).

    Regra de negócio explícita: descarta o prefixo do canal e o '55' e retorna só DDD + número
    (10 ou 11 dígitos). Fora desse formato retorna None e segue o fluxo normal.
    """
    m = _CANAL_55.fullmatch((valor or "").strip())
    return m.group(1) if m else None


def normalizar_telefone(valor: str, origem_excel: bool = False) -> tuple[str | None, str | None]:
    """Retorna (dígitos, motivo_falha).

    Remove apenas formatação inequívoca (espaços, parênteses, hífens, pontos, '+').
    Não acrescenta nem remove DDD/código do país.
    """
    v = (valor or "").strip()
    if not v:
        return None, "Telefone vazio"

    if origem_excel:
        if re.fullmatch(r"\d+\.0+", v):
            v = v.split(".")[0]
        elif _CIENTIFICA.fullmatch(v):
            try:
                d = Decimal(v.replace(",", "."))
                if d == d.to_integral_value():
                    v = str(int(d))
            except InvalidOperation:
                pass

    if _CIENTIFICA.fullmatch(v):
        return None, "Telefone em notação científica (dígitos podem ter sido perdidos)"
    if re.fullmatch(r"\d+[.,]\d+", v) and not re.fullmatch(r"\d+[.,]0+", v):
        return None, "Telefone com casas decimais"
    if re.fullmatch(r"\d+[.,]0+", v):
        return None, "Telefone com casas decimais artificiais"
    if not _PERMITIDOS.fullmatch(v):
        return None, "Telefone com caracteres inválidos"

    digitos = re.sub(r"\D", "", v)
    if not (MIN_DIGITOS <= len(digitos) <= MAX_DIGITOS):
        return None, f"Telefone com quantidade de dígitos inválida ({len(digitos)})"
    return digitos, None


def chave_telefone(digitos: str, equivaler_55: bool = False) -> str:
    """Chave de comparação. Por padrão é o próprio número normalizado.

    Com equivaler_55=True (opção explícita do usuário), '55' + DDD + número e DDD + número
    são tratados como o mesmo telefone.
    """
    if equivaler_55 and digitos.startswith("55") and len(digitos) in (12, 13):
        return digitos[2:]
    return digitos


def candidatos_em_texto(texto: str) -> list[str]:
    """Sequências de dígitos com tamanho de telefone dentro de um texto (ex.: ConversationId)."""
    runs = re.findall(r"(?<!\d)\d{%d,%d}(?!\d)" % (MIN_DIGITOS, MAX_DIGITOS), texto or "")
    return list(dict.fromkeys(runs))
