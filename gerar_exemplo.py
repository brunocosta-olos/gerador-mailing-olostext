"""Gera dados FICTÍCIOS para testar o sistema (nenhum dado real).

Uso: python gerar_exemplo.py
Cria dados_exemplo/mailing_exemplo_20260930.txt e dados_exemplo/historico_exemplo.xlsx
"""

import random
from pathlib import Path

import pandas as pd

random.seed(42)
PASTA = Path(__file__).parent / "dados_exemplo"
PASTA.mkdir(exist_ok=True)

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elaine", "Fábio", "Gisele", "Heitor", "Íris", "João",
         "Kátia", "Luís", "Márcia", "Nélson", "Otávio", "Paula", "Quésia", "Rafael", "Sônia", "Túlio"]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Pereira", "Lima", "Gonçalves", "Araújo",
              "Conceição", "D'Ávila", "Moura-Leite", "Assunção"]
ATRASOS = ["0-30", "31-60", "61-90", "91-180", "181-360", "360+"]
SALDOS = ["Até 500", "501-1.000", "1.001-5.000", "5.001+"]
IDADES = ["18-25", "26-35", "36-45", "46-55", "56-65", "66-75", "75+"]
PESOS_IDADE = [12, 25, 25, 18, 12, 5, 3]
PORTFOLIOS = ["CARTAO", "EMPRESTIMO", "VAREJO"]


def telefone():
    return "55" + random.choice(["11", "21", "31", "41", "51", "61", "71", "81"]) + "9" + "".join(
        random.choice("0123456789") for _ in range(8))


linhas = ["nome;telefone;customerid;portfolio;faixa_atraso;faixa_saldo;faixa_idade;genero;Envio;Template"]
telefones = []
for i in range(4800):
    nome = f"{random.choice(NOMES)} {random.choice(SOBRENOMES)}"
    tel = telefone()
    telefones.append(tel)
    linhas.append(";".join([
        nome, tel, f"{random.randint(1, 99999999):010d}", random.choice(PORTFOLIOS),
        random.choices(ATRASOS, [30, 20, 15, 15, 12, 8])[0], random.choice(SALDOS),
        random.choices(IDADES, PESOS_IDADE)[0], random.choice(["M", "F"]), "", "",
    ]))

# Casos de borda
casos = [
    ";5511900000001;0000000001;CARTAO;0-30;Até 500;26-35;F;;",            # nome vazio
    "Maria 2;5511900000002;0000000002;CARTAO;0-30;Até 500;26-35;F;;",     # número no nome
    "José @Silva;5511900000003;0000000003;CARTAO;0-30;Até 500;26-35;M;;",  # símbolo
    "TESTE;5511900000004;0000000004;CARTAO;0-30;Até 500;26-35;M;;",       # conteúdo inválido
    "Pedro Alves;5511900000005;0000000005;CARTAO;0-30;Até 500;;M;;",      # idade ausente
    "Rita Gomes;5511900000006;0000000006;CARTAO;0-30;Até 500;60-70;F;;",  # cruza o corte
    "Lia Prado;5511900000007;0000000007;CARTAO;0-30;Até 500;idade?;F;;",  # ininteligível
    "Caio Reis;;0000000008;CARTAO;0-30;Até 500;26-35;M;;",                # sem telefone
    "Beto Luz;5.5119E+12;0000000009;CARTAO;0-30;Até 500;26-35;M;;",       # notação científica
    "Nina   Paz;5511900000010;0000000010;CARTAO;0-30;Até 500;26-35;F;;",  # espaços extras
    "Nina Paz;5511900000010;;CARTAO;0-30;Até 500;26-35;F;;",              # duplicata menos completa
    "Ana-Clara O'Neil;5511900000011;0000000011;VAREJO;31-60;501-1.000;18-25;F;;",
]
linhas += casos
# Duplicatas simples
for tel in random.sample(telefones, 40):
    linhas.append(f"Duplicado Teixeira;{tel};0000000999;CARTAO;0-30;Até 500;26-35;M;;")
linhas.insert(2500, "")  # linha vazia no meio

(PASTA / "mailing_exemplo_20260930.txt").write_bytes(("\r\n".join(linhas) + "\r\n").encode("utf-8"))

# Histórico do mês: ~35% dos telefones, com repetições e vários templates
hist = []
for tel in random.sample(telefones, 1700):
    for _ in range(random.choice([1, 1, 2, 3])):
        hist.append({
            "Campanha": random.choice(["BOT_WPP_Massivo", "BOT_WPP_Return"]),
            "ConversationId": f"CMP{random.randint(100, 999)}_{tel}_{random.randint(10000, 99999):x}",
            "Template": random.choice(["cobranca_v1", "cobranca_v2", "acordo_facil"]),
            "Quantidade": 1,
        })
pd.DataFrame(hist).to_excel(PASTA / "historico_exemplo.xlsx", index=False)
print(f"Mailing: {len(linhas) - 1} linhas | Histórico: {len(hist)} linhas")
