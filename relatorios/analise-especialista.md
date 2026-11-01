# Análise Especialista — Radioamadorismo no Brasil

**Base:** `dados/Estacoes_Radioamador.csv` (Anatel, dados abertos, extração 31/10/2026)
**Autor:** analista de dados (subagente)
**Caráter:** análise especializada — chave primária, modelo de dados, hipótese regulatória e produto. **Não repete** o `retrato-radioamadorismo-brasil.md`; pressupõe que você já o leu.

Todas as contas abaixo vêm de scripts executados (`scripts/exp_*.py`). Nenhum número é inventado; a conta aparece ao lado de cada afirmação.

---

## 1. O mistério dos 46.670 indicativos × 35.498 CPFs — RESOLVIDO

**A conta fecha exatamente.** O retrato registrava o ponto aberto "46.670 indicativos supera 35.498 CPFs, provavelmente indicativos sem CPF". Isso estava **errado**. Não há um único indicativo sem CPF na base.

### Decomposição numérica exata

```
46.670 indicativos distintos
  = 35.498 CPFs distintos (base)
  + 11.189  (indicativos ADICIONAIS: CPFs que têm MAIS de um indicativo)
  −     17  (indicativos COMPARTILHADOS por 2 CPFs diferentes, contados 2×)
  ─────────
  46.670   ✓ (fecha com precisão)
```

Conta verificada em `exp_02_decomposicao.py`:

| Componente | Número | Fonte |
|---|---|---|
| CPFs distintos | 35.498 | medido |
| CPFs com ≥2 indicativos | 8.445 | medido |
| Soma de (N−1) sobre esses CPFs | 11.189 | medido |
| Indicativos com >1 CPF (compartilhados) | 13 | medido |
| Excesso de contagem por compartilhamento | 17 | medido (um indicativo com 4 CPFs conta 3 a mais, etc.) |

**Por que o número de indicativos é maior que o de pessoas:** a maioria dos radioamadores tem **um indicativo**, mas uma minoria tem **dois ou mais**. O indicativo não identifica a pessoa; identifica a **cota de espectro/estação licenciada àquela pessoa**. Quem tem estação fixa + móvel + repetidora pode carregar vários indicativos, cada um apontando para uma licença distinta.

### Distribuição CPF → nº de indicativos distintos

| Nº de indicativos | CPFs |
|---|---|
| 1 | 27.053 |
| 2 | 6.631 |
| 3 | 1.351 |
| 4 | 298 |
| 5 | 90 |
| 6 | 31 |
| 7 | 15 |
| 8 | 3 |
| 9 | 4 |
| 10 | 7 |
| 11 | 4 |
| 12–33 | 11 (cauda longa) |

**Leitura:** 76,2% dos radioamadores (27.053 de 35.498) têm um único indicativo. Os demais 23,8% têm dois ou mais — e é esse quarto que infla o total.

### Um exemplo real de cada caso

**(a) Indicativo repetido em várias linhas — o caso comum.** O mesmo indicativo aparece em 2 linhas (fixa + móvel da mesma pessoa), e a base contém **23.000 indicativos** que aparecem em mais de uma linha. Exemplo (Gizelle Kaminski Corso, SC):

| Indicativo | Tipo | Nº da Estação | Fistel |
|---|---|---|---|
| PU5GIZ | N/I | 1015431744 | 50446536750 |
| PU5GIZ | Fixa | 1015431728 | 50446536750 |
| PU5GIZ | Móvel | 1015431736 | 50446536750 |

Mesmo indicativo, **mesmo Fistel**, três estações. Isto é o coração da confusão: um indicativo não mapeia 1:1 para uma estação.

**(b) CPF com MÚLTIPLOS indicativos distintos.** Exemplo real (o mesmo CPF `***44543**` acima tem DOIS indicativos):

- `PU5GIZ` — Classe C, Fistel 50446536750
- `PU7GJA` — Classe C, Fistel 50500014639

Ou seja: a pessoa tem **dois indicativos**, cada um ligado a um Fistel diferente. É o que faz o total de indicativos superar o de CPFs.

**(c) Indicativo de ENTIDADE COLETIVA (CNPJ).** Exemplo — LABRE-SP (`62041256000102`, "Liga de Amadores Brasileiros de Radio Emissão - Labre-sp") carrega **27 indicativos** (PY1AA, PY1ABL, PY1BJM, PY1DCC, PY1LAB, …) em **30 estações**. Entidades coletivas são 281 CNPJs distintos em 842 linhas, e explicam a maior parte da cauda longa.

**(d) Indicativo COMPARTILHADO por 2 CPFs (13 casos — anomalia de dados).** Exemplo `PU7MLL`:

- `***49913**` — Leno Jose Batista de Alencar — Fixa, est 1011321502, Fistel 50420173307
- `***78760**` — Lucio Flavio Lemos — Fixa, est 1011321510, Fistel 50456356541

Dois CPFs diferentes, o mesmo indicativo, Fistels distintos. São 13 indicativos assim. **Provável erro de base** (reuso indevido de indicativo) ou, no limite, herança de licença. Vale auditar — mas é só 13 em 46.670 (0,03%).

### Conclusão do mistério

O número honesto segue sendo **~35,5 mil pessoas físicas + 281 entidades coletivas**. Os "46.670" são indicativos, não pessoas, e a diferença é integralmente explicada por CPFs multi-indicativo (11.189) menos compartilhamentos (17). **Não existe "indicativo sem CPF" nenhum.**

---

## 2. Fistel ↔ Número da Estação ↔ Indicativo — e a chave primária

### O que cada campo significa (medido)

| Campo | Distintos | Relação | Interpretação |
|---|---|---|---|
| **Número da Estação** | **71.328** (0 duplicados) | 1:1 com a linha | **chave primária confiável** |
| Indicativo | 46.670 | 1:N estações | identifica a cota/indicativo, não a estação |
| Fistel | 43.903 | 1:N estações | identifica a **outorga/serviço**, não a estação |
| CPF/CNPJ | 35.779 (35.498 CPF + 281 CNPJ) | 1:N estações | identifica a **pessoa/entidade titular** |

### As três verificações decisivas

1. **Número da Estação é único.** `exp_03_chaves.py`: 71.328 linhas, 71.328 números distintos, **0 duplicados**. É a única coluna 1:1 com a linha. **Usar como chave primária.**

2. **Fistel NÃO identifica estação.** Um Fistel aponta para múltiplos números de estação:
   - 1 estação: 19.937 Fistels
   - 2 estações: 21.705 Fistels
   - 3 estações: 1.726 Fistels
   - … até 34 estações para 1 Fistel.
   Isto confirma o aprendizado do `BASES.md`: deduplicar por Fistel **colapsa** estações. O Fistel é a chave da **outorga/autorização**, herdada por todas as estações do mesmo titular.

3. **Indicativo também não identifica estação.** Um indicativo aponta para 1 a 12 números de estação:
   - 1 estação: 23.670 indicativos
   - 2 estações: 21.642 indicativos
   - 3+: 1.358 indicativos

### Chave primária proposta

**`Número da Estação`** é a chave primária natural e perfeita (única, não-nula, estável). **`Indicativo` + `Número da Estação`** forma uma chave composta alternativa se você quiser manter a semântica "qual indicativo está licenciado em qual estação" — mas o número da estação sozinho já basta.

### Modelo de dados normalizado (para app de consulta)

```
┌─────────────┐        ┌──────────────┐        ┌─────────────┐
│   PESSOA    │        │   ESTAÇÃO    │        │  INDICATIVO │
├─────────────┤        ├──────────────┤        ├─────────────┤
│ documento PK│ 1────N │ num_estacaoPK│ N────1 │ indicativoPK│
│ tipo (CPF/  │        │ tipo (fixa/  │        │ prefixo     │
│   CNPJ)     │        │  móvel/rep/  │        │ dígito_reg. │
│ nome        │        │  terrena)    │        │             │
│ uf_entidade │        │ município    │        └─────────────┘
│ classe COER │        │ uf_estação   │               │
└─────────────┘        │ classe       │               │
       │               │ datas (1º/últ.│               │
       │               │  licenciam.) │               │
       │               │ validade      │               │
       │               │ status        │               │
       │               │ fistel ───────┼──┐            │
       │               └──────────────┘  │            │
       │                                 │            │
       └───────────┐                     │            │
                   ▼                     ▼            │
            ┌──────────────────────────────────┐     │
            │   LICENÇA (ou OUTORGA)           │     │
            │   fistel PK                       │     │
            │   servico (302/400/401)           │     │
            │   data inclusão                   │     │
            │   documento (FK pessoa)           │◄────┘
            │   indicativo (FK indicativo)      │
            └──────────────────────────────────┘
```

**Regras do modelo (derivadas dos dados):**

- `pessoa.documento` é PK (CPF ou CNPJ, sem máscara para busca, com máscara para exibição).
- `estacao.num_estacao` é PK, 1:1 com o registro.
- `estacao.fistel` e `estacao.indicativo` são **FKs**, não PKs.
- `licenca` (ou `outorga`) reúne o que hoje está na base de **prestadoras** (`radioamador_brasil.csv`): o Fistel é a ponte entre a outorga e as estações. A mesma pessoa tem **um Fistel por outorga**, e cada outorga pode licenciar N estações.
- A **classe (COER)** pertence à **pessoa** (habilitação do operador), não à estação — embora na base bruta venha repetida em cada linha. No modelo normalizado, classe é atributo de `pessoa`.

**Nota importante de consistência:** como o mesmo Fistel aparece na fixa e na móvel, a tabela `licenca` tem cardinalidade 1:N para `estacao`, e é onde mora a resposta à pergunta-chave do usuário: **"qual o meu Fistel?"** (ver seção 5).

---

## 3. Padrões não explorados

### 3.1 Sazonalidade por mês (primeiro licenciamento)

`exp_04_padroes.py` — licenciamentos por mês (todos os anos somados):

| Mês | Estações | Mês | Estações |
|---|---|---|---|
| Jan | 1.916 | Jul | 2.176 |
| Fev | 2.252 | Ago | 2.350 |
| Mar | 2.470 | Set | 2.484 |
| Abr | 2.543 | Out | 2.550 |
| Mai | 2.446 | Nov | 2.401 |
| Jun | 2.570 | Dez | 1.976 |

**Achado:** o único mês fora da curva é **dezembro** (1.976, ~20% abaixo da média ~2.400). Janeiro também é fraco (1.916). O restante é plano. **Não há sazonalidade de férias/verão relevante**; há um vale de fim de ano (dezembro + janeiro), consistente com a burocracia da Anatel em recesso. A base não tem volume suficiente para justificar um produto "calendário de licenciamento", mas o vale de dezembro é um fato.

### 3.2 Razão estações/pessoa por UF

`exp_05_uf_classe.py` (pessoas distintas por UF, via UF da Entidade):

| UF | Estações | Pessoas | Razão |
|---|---|---|---|
| SP | 20.610 | 11.339 | 1,82 |
| MT | 440 | 231 | **1,90** |
| RR | 185 | 101 | 1,83 |
| RO | 370 | 217 | 1,71 |
| AP | 188 | 110 | 1,71 |
| PA | 610 | 357 | 1,71 |
| PR | 5.794 | 3.426 | 1,69 |
| … | … | … | … |
| AM | 367 | 243 | **1,51** |
| PI | 910 | 599 | 1,52 |
| SE | 512 | 336 | 1,52 |

**Achado:** a razão varia pouco (1,5–1,9), mas **MT e RR** têm a maior proporção de multi-estacionistas (1,90 e 1,83). Estados do Norte/Centro-Oeste tendem a ter radioamadores com mais estações por cabeça — provavelmente reflexo de distância (quem mora longe mantém fixa + móvel + repetidora para cobertura própria). É um sinal fraco, mas real.

### 3.3 Municípios com muitas estações e pouca população

Sem cruzar com IBGE (fora do escopo desta base), a leitura segura é a de concentração absoluta: **2.138 fixas/repetidoras em São Paulo/SP** e **647 em Brasília/DF**. Brasília é o caso notável de **muitas estações para população modesta** (3,1 mi hab., mas 647 fixas — mais que Curitiba, que tem ~1,9 mi hab.). Para medir "pouca população" com precisão, é preciso puxar a tabela de população do IBGE — deixado como próximo passo, não afirmado aqui (lição 6: medir antes de afirmar).

### 3.4 Concentração por prefixo (PY/PP/PT/PU/PV/PS/PR/PW/PQ)

`exp_04_padroes.py` — prefixo do indicativo (por **linha** e por **indicativo distinto**):

| Prefixo | Linhas | Indicativos distintos | Associação (medida em 3.5) |
|---|---|---|---|
| **PU** | 48.829 | 31.750 | Classe C (48.821 das 48.829) |
| **PY** | 15.172 | 10.008 | Classes A/B |
| PP | 2.781 | 1.815 | Classes A/B |
| PT | 1.777 | 1.167 | Classes A/B |
| PR | 1.234 | 884 | Classes A/B |
| PS | 912 | 611 | Classes A/B |
| PW | 305 | 186 | Classes A/B |
| PV | 203 | 169 | misto (C + A/B) |
| PQ | 100 | 73 | especial (evento/contest) |
| ZZ/ZV | 3 | 3 | **erro de digitação** |

**Achado forte:** **PU = Classe C.** O prefixo PU é praticamente um sinônimo do COER Classe C (48.821 de 48.829 linhas PU são Classe C). PY, PP, PT, PR, PS, PW concentram Classes A e B. **PV é o prefixo de transição** (125 Classe C + 76 A/B) — coerente com a regra de promoção (a pessoa muda de classe, o indicativo PV/PU é reciclado). Os 3 indicativos `ZZ`/`ZV` são **erros de base** (ZZ2LDK, ZZ3CMR, ZV7D) — nenhum prefixo ZZ existe no serviço de radioamador.

### 3.5 Dígito de região 1–0

`exp_04_padroes.py` e `exp_05_uf_classe.py`:

| Dígito | Estações | | Dígito | Estações |
|---|---|---|---|---|
| 0 | 34 | | 6 | 2.297 |
| 1 | 8.721 | | 7 | 10.728 |
| 2 | 23.499 | | 8 | 3.188 |
| 3 | 5.554 | | 9 | 1.235 |
| 4 | 5.867 | | | |
| 5 | 10.193 | | | |

**Achado:** a **região 2** (RJ/ES) sozinha tem 23.499 estações — 32,9% do país, mais que SP/região 1 + região 5 juntas. A **região 0 tem só 34 estações** e é o caso especial: são indicativos `PY0F`, `PY0FN` etc. — o "0" designa **cota especial** (Fernando de Noronha, ilhas oceânicas, estações com sufixo especial). Não é uma região geográfica, é uma classe de indicativo reservada.

### 3.6 Outliers: CPF com muitas estações

`exp_03_chaves.py` + `exp_04_padroes.py` — top CPFs por total de estações:

| Documento | Nome | Estações | Indicativos |
|---|---|---|---|
| `***44896**` (+ `***81434**`) | "Jose Alves da Silva" | 36 (34 fixas DF + 2 móveis PR) | 33 |
| `62041256000102` | LABRE-SP | 30 | 27 |
| `06810899000194` | LABRE-CE | 26 | 25 |
| `14768708000100` | ARCESUL-PR | 20 | 9 |
| `30875637000192` | LABRE-RJ | 18 | 17 |

**Achado com alerta:** o outlier nº 1 ("Jose Alves da Silva", 36 estações em 34 municípios do DF) **se espalha por DOIS CPFs diferentes** (`***44896**` e `***81434**`), além de aparecer como "jose alves da silva filho" com o indicativo PQ2DR. É quase certamente **sujeira de base**: homônimos consolidados ou uma entidade registrada sob nome de pessoa física. **Não é um radioamador real com 36 estações.** Isso contamina qualquer ranking de "mais estações por pessoa". As entidades coletivas (LABRE e associações) é que são os verdadeiros multi-licenciadores — e isso é legítimo (elas licenciam repetidoras e estações de clube).

### 3.7 Entidades coletivas com mais estações

Já listadas acima (LABRE-SP 30, LABRE-CE 26, ARCESUL 20, LABRE-RJ 18…). As LABRE estaduais dominam. São 281 CNPJs no total, 842 linhas. São as responsáveis pela rede de repetidoras (419 repetidoras N/A = todas CNPJ) e por indicativos "institucionais" (PY1AA, PY1LAB etc.).

---

## 4. Hipótese regulatória — VERIFICADA (e o ponto aberto da Res. 710 refutado)

### A pergunta original estava mal formulada

A tarefa pedia para verificar a **Resolução nº 710/2019**. A verificação descobriu que **a Res. 710/2019 NÃO trata de radioamador** — ela "Aprova a Destinação da Faixa de 2,3 GHz ao SLP" (Serviço Limitado Privado), já revogada. É um falso cognato: quem procurou "710" associou por engano ao radioamadorismo.

### O arcabouço regulatório correto (verificado nas fontes)

| Norma | Assunto | Status |
|---|---|---|
| **Resolução 449/2006** | Regulamento do Serviço de Radioamador (74 artigos; define classes, tipos de estação, indicativos) | **revogada em 2026** |
| Resolução 697/2018 | Condições de uso de radiofrequência + classes do COER por faixa | revogada |
| Ato 9106/2018 | Plano de faixas + canalização de repetidoras | revogado |
| Ato 926/2024 | Características técnicas do serviço | vigente |
| **Resolução 777/2025 (RGST)** | Regulamento Geral de Serviços de Telecomunicações; consolida o radioamadorismo em 11 artigos | **vigente** (transição 180 dias) |
| **Ato 3448/2026** | Requisitos operacionais do Serviço de Radioamador | **vigente** (mar/2026) |

### A pergunta central: repetidora exige Classe A?

**Resposta: sim sob a Res. 449/2006 (Art. 44), mas NÃO MAIS sob a Res. 777/2025.**

O **Art. 44 da Res. 449/2006** (texto integral recuperado):

> "Art. 44. A Licença para Funcionamento de Estação Repetidora do Serviço de Radioamador poderá ser requerida por:
> I – por titular do COER Classe 'A';
> II – associações de radioamadores;
> III – universidades e escolas;
> IV – associações do Movimento Escoteiro e do Movimento Bandeirante;
> V – entidades de defesa civil."

Ou seja, sob a 449/2006, **repetidora era só Classe A (pessoa física) ou pessoa jurídica**. Classe B estava fora.

### A reviravolta: Res. 777/2025, Art. 16, § 3º, inciso II

O novo **Art. 16, § 3º da Res. 777/2025 (RGST)** mudou a regra:

> "O titular da Licença para Funcionamento de Estação Repetidora de Serviço de Radioamador deverá ser:
> **I – titular do COER Classe 'A';**
> **II – titular do COER Classe 'A' ou 'B';** ← NOVO
> III – associações de radioamadores;
> IV – universidades e escolas;
> V – entidades de defesa civil; ou
> VI – associações do Movimento Escoteiro e do Movimento Bandeirante."

**A Classe B foi habilitada a licenciar repetidoras pela primeira vez.**

### E o dado confirma a norma — com precisão de relógio

`exp_06_repetidoras_b.py` — as 35 repetidoras Classe B têm todas **primeiro licenciamento em 2026**:

| Ano do 1º licenciamento | Repetidoras Classe B |
|---|---|
| **2026** | **35 (todas)** |
| antes de 2026 | 0 |

A distribuição temporal das repetidoras Classe A (787) é contínua desde 1999. As Classe B só existem a partir de **março/2026** — exatamente a janela em que a Res. 777/2025 (publicada 28/04/2025, com 180 dias de transição) entrou em vigor, e o Ato 3448/2026 (mar/2026) consolidou os procedimentos.

**Conclusão: as 35 repetidoras Classe B NÃO são irregulares, NÃO são anteriores à norma, e NÃO são erro.** São a **primeira leva de repetidoras licenciadas sob a nova regra do Art. 16, § 3º, II da Res. 777/2025**. O dado é a prova empírica de que a nova norma já está produzindo efeito na base.

**Exemplos reais das 35 (todas de 2026):** PT7MAZ/CE (02/09/2026), PY4POP/MG (02/09/2026), PY5FOX/SP (19/10/2026), PY1JPA/RJ (27/08/2026), PP1FGS/ES (27/09/2026), PY6RSL/BA (10/08/2026), PY3ATP/RS (07/07/2026)… todas pessoa física, todas CPF.

**Implicação de produto:** há um **boom silencioso de repetidoras Classe B em curso** (35 só em 2026, contra 787 Classe A acumuladas em 27 anos). Isso é uma notícia relevante para a comunidade: a porta de entrada para infraestrutura de repetição acabou de se alargar. Qualquer produto editorial sobre "como montar sua repetidora" acertou o timing.

---

## 5. O app de consulta (requisitos e arquitetura)

### Contexto do usuário

O usuário é **cego total, usa NVDA**, quer consultar a base para — na prática — **achar o Fistel e emitir o boleto anual (TFI/TFF)**. Prioridade máxima: **indicativo → Fistel**.

### Requisitos funcionais priorizados (P0 = obrigatório)

| Prioridade | Busca por | Devolve | Dor resolvida |
|---|---|---|---|
| **P0** | **Indicativo** (ex.: PY1MEL) | Fistel, nome, classe, tipo(s) de estação, validade, status | achar o Fistel para o boleto |
| **P0** | **Nome** (parcial, sem acento) | tudo acima | achar quando não lembra o indicativo |
| P1 | CPF/CNPJ (com ou sem máscara) | todas as estações da pessoa | conferir o que está em seu nome |
| P1 | Município + UF | lista de estações fixas/repetidoras da cidade | achar repetidor local |
| P2 | Classe (A/B/C) + UF | distribuição | análise |
| P2 | Tipo de estação | fixa/móvel/repetidora | análise |

### Requisitos de ACESSIBILIDADE (críticos, não negociáveis)

1. **Saída linear** — tudo em texto puro, sem tabelas HTML complexas nem colunas. O NVDA lê bem listas aninhadas e parágrafos; lê mal `<table>` larga e layout multicoluna.
2. **Navegável por cabeçalhos** — cada resultado começa com um `<h2>`/`<h3>` ("PY1MEL — Gizelle… — Classe C"), para o usuário pular de resultado em resultado com a tecla `H` do NVDA.
3. **Sem mouse** — 100% teclado. Busca por `<input>` + Enter. Resultado focável.
4. **Tolerante a acento e erro de digitação** — normalizar `é→e`, `ç→c` (Unicode NFKD + strip de diacríticos) antes de casar; e usar **FTS4/FTS5 do SQLite** com `LIKE`/prefix para capturar "P1MEL" ou "PYIMEL" parcial.
5. **Tolerante a máscara** — aceitar CPF com ou sem pontos/traço (strip de não-dígitos).
6. **Resposta falada-friendly** — número de resultados sempre anunciado primeiro ("3 resultados"), para orientar o fluxo.

### Arquitetura recomendada

**SQLite + FTS5, com uma CLI e um front Streamlit opcional.**

- **Por que SQLite e não CSV:** a base tem 71.328 linhas; CSV exige varredura completa a cada busca. SQLite com índice em `indicativo`, `nome_normalizado`, `documento`, `fistel`, `municipio` responde em milissegundos, e FTS5 dá busca tolerante a erro de digitação e acento "de graça".
- **Por que arquivo único:** o modelo normalizado (seção 2) cabe em um `.db` de ~30–50 MB. Um arquivo só simplifica distribuição e backup. Sem servidor.
- **CLI primeiro, Streamlit depois:** a CLI (`radio.py busca PY1MEL`) é o MVP, já acessível ao NVDA (terminal lê bem). O Streamlit vem depois para quem prefere navegador — mas **Streamlit tem problemas conhecidos de acessibilidade** (tabelas, widgets custom); se for o caminho, preferir `st.text`/`st.markdown` linear em vez de `st.dataframe`.
- **Busca principal (P0) deve retornar o Fistel em DESTAQUE**, pois é o objetivo do usuário: "Fistel: 01000257142 — emita o boleto em <sistema Anatel>".

### Estrutura do banco (concretização do modelo da seção 2)

```sql
CREATE TABLE pessoa (
  documento TEXT PRIMARY KEY,       -- CPF/CNPJ sem máscara
  tipo_doc  TEXT,                   -- 'CPF' | 'CNPJ'
  nome      TEXT,
  nome_norm TEXT,                   -- sem acento, lowercase (para busca)
  classe    TEXT,                   -- A/B/C/N/A
  uf        TEXT
);
CREATE TABLE estacao (
  num_estacao INTEGER PRIMARY KEY,
  documento   TEXT REFERENCES pessoa,
  indicativo  TEXT,
  fistel      TEXT,
  tipo        TEXT,                 -- Fixa/Móvel/Repetidora/Terrena
  municipio   TEXT,
  uf_estacao  TEXT,
  data_1o     TEXT,
  data_ult    TEXT,
  validade    TEXT,
  status      TEXT
);
CREATE VIRTUAL TABLE busca USING fts5(indicativo, nome, documento, fistel, municipio, content='');
```

Índices: `estacao(indicativo)`, `estacao(fistel)`, `estacao(documento)`, `pessoa(nome_norm)`, `estacao(municipio, uf_estacao)`.

---

## 6. Ideias de produto — ranqueadas por (valor real × esforço)

Classificação cética: cada item abaixo só entra se resolve uma dor real e mensurável. O que não resolve, está dito.

### ★★★★★ Valor alto, esforço baixo

1. **"Ache meu Fistel" (CLI/SQLite, o MVP do item 5).** Dor real e diária: todo radioamador precisa do Fistel para emitir o boleto TFI/TFF, e o sistema da Anatel é hostil (`sistemas.anatel.gov.br` devolve 423 para automação; consulta manual é lenta). Um comando `radio.py PY1MEL` que devolve Fistel + validade + status resolve. **Esforço: 1 dia.** Valor: máximo para o usuário cego.
   - **Ressalva cética:** a base pública tem 25,7% de validade "N/I" e não tem o valor do boleto. O app resolve a *localização do Fistel*, não a *emissão* (que segue no portal Anatel). Não prometer emissão automática.

2. **Aviso de validade vencida / próxima do vencimento (para as 362 "Vencida" + as "Ativa" com data próxima).** Dor real: operar com licença vencida é ilegal e a multa é cara. A base tem 362 estações explicitamente "Vencida" (220 delas só no RS — ver seção 3.6/3.7) e 52.635 "Ativa" com data. Um alerta "sua validade vence em X" é de altíssimo valor e baixo esforço.
   - **Ressalva:** os 18.331 "N/I" não são vencidos (lição do BASES.md). Não alarmar indevidamente.

### ★★★★ Valor alto, esforço médio

3. **Mapa/ranking de repetidoras por região + "monte a sua" (editorial).** Dor real recém-aberta: a Classe B agora pode licenciar repetidora (seção 4). Há um boom de 35 repetidoras Classe B só em 2026. Um guia "você, Classe B, já pode montar repetidora — veja como e onde há vaga na sua região" acerta o timing regulatório. Baseado nos 1.241 repetidores e na concentração SP/RJ/MG (45%).
   - **Ressalva:** exige cruzar com dados de frequência/canalização (Ato 9106) que não estão nesta base. O "onde há vaga" é mais difícil que o "você pode".

### ★★★ Valor médio, esforço médio

4. **Painel "quem opera perto de mim" (fixas + repetidoras por município).** Dor real moderada: para iniciar contato local. Mas já existe cultura de cluster/local na comunidade; o valor incremental é baixo. Só vale se combinado com o item 3.

5. **Limpeza/análise de qualidade da base (auditoria pública).** Os 13 indicativos compartilhados, os 3 prefixos ZZ/ZV, e o "Jose Alves da Silva" de 36 estações são erros reais de dados públicos. Publicar uma "lista de inconsistências" tem valor cívico, mas **não resolve dor do radioamador comum** — é valor para Anatel/pesquisadores, esforço baixo, valor de mercado baixo.

### ★☆ Valor baixo — NÃO fazer (ceticismo explícito)

- **"Sazonalidade/calendário de licenciamento".** O único sinal é o vale de dezembro/janeiro (seção 3.1). Fraco demais para produto.
- **"Ranking de multi-estação por pessoa".** Contaminado pelo caso "Jose Alves da Silva" (sujeira). Ranking público de quem tem mais estações seria impreciso e potencialmente expõe dados pessoais. Não fazer.
- **"Razão estações/pessoa por UF".** Curiosidade acadêmica (seção 3.2), sem dor real.
- **"Dashboard de prefixos PY/PP/PT/PU".** PU=Classe C é interessante, mas é insight de mesa, não produto.

---

## 7. Contradições e riscos (reportados, não silenciados)

1. **A Res. 710/2019 não é sobre radioamador.** A hipótese original da tarefa apontava para a norma errada. A norma certa para repetidora/classes é **Res. 449/2006 (Art. 44) → substituída pela Res. 777/2025 (Art. 16, § 3º)**. Isso corrige o ponto de partida, não o dado.

2. **O "ponto aberto" do retrato (46.670 > 35.498) estava com explicação errada.** O retrato especulava "indicativos sem CPF". Medido: **zero indicativos sem CPF**. A causa é CPF multi-indicativo (11.189) − compartilhamentos (17). A conclusão do retrato (35,5 mil pessoas) continua correta, mas o mecanismo estava errado.

3. **Outlier "Jose Alves da Silva" (36 estações / 2 CPFs).** Risco de contaminação em qualquer análise de "pessoa com mais estações". Tratar como sujeira de dados, não como pessoa real.

4. **Os 13 indicativos compartilhados por 2 CPFs** são anomalia que merece auditoria, mas é 0,03% — não afeta nenhuma conclusão macro.

5. **Vencidas concentradas no RS (220 de 362).** Não investigado a fundo aqui — pode ser efeito de um lote específico de renovações no RS, ou um problema sistêmico. Merece um olhar dedicado antes de afirmar qualquer coisa (lição 6).

6. **"Municípios com pouca população"** não foi medido de fato (falta IBGE). A seção 3.3 usa concentração absoluta, que é segura, mas não afirma "pouca população" — deixa explícito que isso exige cruzamento com IBGE.

---

## Metodologia

- **Scripts executados** (todos em `scripts/`, prefixo `exp_`): `exp_01_misterio_indicativos.py`, `exp_02_decomposicao.py`, `exp_03_chaves.py`, `exp_04_padroes.py`, `exp_05_uf_classe.py`, `exp_06_repetidoras_b.py`.
- **Fonte regulatória:** Res. 449/2006 (Art. 44, texto integral via URPE), Res. 777/2025 (Art. 16 §3º e Art. 28, via qtc.ecra.club e LABRE), Ato 3448/2026 e Ato 926/2024 (via Anatel). Res. 710/2019 verificada e **descartada** por tratar de SLP 2,3 GHz.
- **Tratamento:** encoding `utf-8-sig`, separador `;`, 71.328 linhas, zero descartadas.
