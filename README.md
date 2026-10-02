# Gerador de Mailings Olos

Sistema local que recebe o **mailing do dia**, o **histórico do mês** e a **quantidade de números disponíveis (1 a 4)** e entrega os **cinco TXT prontos para importação**, aplicando todas as regras do projeto "Olos Text".

Tudo roda na sua máquina. Nenhum dado de cliente é enviado para serviços externos.

## Como usar (Windows)

1. Instale o Python 3.10 ou mais recente em <https://www.python.org/downloads/> e marque **"Add Python to PATH"** durante a instalação.
2. Descompacte esta pasta em um local fixo, por exemplo `C:\Olos\gerador_mailing`.
3. Dê dois cliques em **`iniciar.bat`**.
   - Na primeira vez, ele cria o ambiente e instala as dependências (leva alguns minutos).
   - Depois, o navegador abre em `http://localhost:8501`.
4. Na tela:
   1. Envie o mailing e o histórico.
   2. Escolha os números disponíveis.
   3. Confira a data da base e clique em **Processar**.
5. Baixe o ZIP com os 5 arquivos ou cada arquivo separadamente.

No Linux ou no Mac, use `./iniciar.sh`.

Para testar sem dados reais, rode `python gerar_exemplo.py` e use os arquivos criados em `dados_exemplo/`, que são fictícios.

## O que a tela mostra

- Os cinco arquivos com campanha, status, cenário, critérios e quantidade, com botão de download.
- A reconciliação: recebidos − excluídos − pendências − duplicatas = entregues.
- As exclusões e pendências por motivo.
- Um relatório opcional em CSV com o número da linha e o motivo, sem nomes nem telefones.
- As 15 validações refeitas sobre os arquivos já gerados, lendo os bytes finais.
- Avisos, por exemplo:
  - arquivos acima de 1.000 contatos;
  - arquivos vazios;
  - linhas ambíguas no histórico;
  - telefones que só coincidem se o "55" for desconsiderado.

## Regras implementadas

| Etapa | Regra | Onde |
|---|---|---|
| Leitura | Detecta codificação (UTF-8, UTF-8 com BOM, Windows-1252), separador e cabeçalho. Telefone e customerid são lidos como texto. Colunas Envio e Template são ignoradas. | `motor/leitura.py` |
| Histórico | Aceita Excel, CSV ou TXT. Procura a coluna de telefone pelo nome; se não houver, extrai do **ConversationId** apenas quando existe um único número possível. Se nada for encontrado, detecta pelo conteúdo. A coluna pode ser escolhida manualmente. | `motor/historico.py` |
| Histórico (canal) | Valor no formato `<canal>_55` + 10 ou 11 dígitos (ex.: `whatsappcloud_5531994252095`), em coluna única ou no ConversationId: o prefixo do canal e o "55" são descartados e só DDD + número (`31994252095`) é usado na comparação. Vale só para o histórico; o mailing e os TXT finais não mudam. O resumo informa quantas linhas foram convertidas. Canal e telefone em colunas separadas continuam funcionando pela detecção normal. | `motor/telefone.py`, `motor/historico.py` |
| Telefone | Remove apenas a formatação (espaços, parênteses, hífen, "+"). Não acrescenta nem remove DDD ou código 55. Notação científica e casas decimais tornam o telefone inutilizável. | `motor/telefone.py` |
| Nome | Exclui nomes vazios, com número, com símbolos ou claramente inválidos (TESTE, NULL, XXX...). Remove espaços extras. Apóstrofo é removido e hífen vira espaço (`Ana-Clara` → `Ana Clara`). | `motor/validacao.py` |
| Idade | Exclui idade ausente e 66 anos ou mais (`66-75`, `75+`, `acima de 65`). Faixas que atravessam o corte (`60-70`) ou que não dão para interpretar viram **pendência**. | `motor/validacao.py` |
| Estrutura | Linhas com campos a mais, ponto e vírgula, tabulação ou quebra de linha dentro de um campo viram pendência. | `motor/leitura.py` |
| Deduplicação | Feita depois das exclusões e antes dos cenários. Mantém o registro mais completo; em empate, a primeira ocorrência. | `motor/pipeline.py` |
| Envio | ENVIADO = telefone presente no histórico. Uma ocorrência basta. | `motor/pipeline.py` |
| Cenários | Detalhados na seção abaixo. | `motor/cenarios.py` |
| Arquivos | Nome no formato `{prefixo}baseAAAAMMDD_{01..05}_{nao_enviados\|enviados}.txt`, com prefixos em ciclo conforme os números disponíveis. Conteúdo com 8 campos separados por `;`, UTF-8 sem BOM, CRLF, sem cabeçalho. | `motor/geracao.py` |

## Como os cenários são criados

1. **Arquivos por status.** O sistema decide quantos dos cinco arquivos ficam com os NÃO ENVIADOS e quantos com os ENVIADOS, buscando o menor "maior arquivo" possível. Em empate, dá mais arquivos aos NÃO ENVIADOS. Os dois status nunca se misturam.
2. **Critério de divisão.** Dentro de cada status, o sistema testa atraso, idade, saldo e portfólio, sozinhos ou combinados em pares, e agrupa faixas **consecutivas**. Fica com a opção de volumes mais equilibrados, preferindo critérios simples.
3. **Faixa grande demais.** Se uma faixa sozinha for maior que um arquivo, ela vira um cenário em **partes** (por exemplo, "Cenário 2 — parte 1 de 2"). As partes têm o mesmo perfil e são divididas só por volume.
4. **Nenhum contato fica de fora.** Se não for possível manter todos os arquivos com até 1.000 contatos, o sistema avisa em vez de descartar contatos.

## Estrutura

```
app.py              interface (Streamlit)
motor/              regras de negócio, independentes da interface
  leitura.py        leitura do mailing
  historico.py      leitura do histórico
  telefone.py       normalização de telefone
  validacao.py      nome e idade
  cenarios.py       divisão em cinco cenários
  geracao.py        nomes, TXT, ZIP e validações finais
  pipeline.py       orquestração e resumo
tests/              testes automáticos (python -m pytest -q)
gerar_exemplo.py    gera dados fictícios para teste
```

## Ajustes comuns

| O que ajustar | Onde |
|---|---|
| Idade de corte | `IDADE_CORTE` em `motor/validacao.py` |
| Lista de nomes inválidos | `NOMES_INVALIDOS` em `motor/validacao.py` |
| Teto preferencial por arquivo | `TETO_PREFERENCIAL` em `motor/cenarios.py` |
| Prefixos das campanhas | `CAMPANHAS` em `motor/geracao.py` |
| Nomes de coluna aceitos | `ALIASES_*` em `motor/leitura.py` e `motor/historico.py` |

Depois de qualquer ajuste, rode `python -m pytest -q` para confirmar que as regras continuam válidas.
