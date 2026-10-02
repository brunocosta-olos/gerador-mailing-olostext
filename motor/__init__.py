"""Motor de processamento de mailings Olos.

Todas as regras de negócio ficam aqui, isoladas da interface, para que possam ser
reaproveitadas por outra interface (ex.: API FastAPI) no futuro.
"""

from .pipeline import processar, Resultado  # noqa: F401

CAMPOS = [
    "nome", "telefone", "customerid", "portfolio",
    "faixa_atraso", "faixa_saldo", "faixa_idade", "genero",
]
