# BASES.md — Mapa das bases públicas de Radioamador e Rádio do Cidadão

**Projeto:** radioamador-brasil
**Criado:** 2026-10-31
**Pesquisador:** Melhym Pereira Quemel (PY1MEL, Classe A)

Objetivo desta etapa: **adquirir, validar e documentar** as bases antes de decidir produto.

---

## 1. Quadro geral

| # | Base | Conteúdo | Registros | Status | Arquivo |
|---|---|---|---|---|---|
| A | Prestadoras de Serviços de Telecomunicações | outorga: quem é autorizado, por serviço | 277.167 linhas (BR) | **obtida** | `dados/prestadoras.zip` |
| B | Estações Licenciadas (zip mestre) | 11 CSVs, um por serviço | — | **obtida** | `dados/estacoes_licenciadas.zip` |
| B1 | → `Estacoes_Radioamador.csv` | estações de radioamador | **71.328** | **obtida + validada** | `dados/Estacoes_Radioamador.csv` |
| B2 | → `Estacoes_Banda_Larga_Fixa.csv` | estações SCM | 3,99 MB | não extraída | — |
| B3 | → `Estacoes_MMA.csv` | móvel aeronáutico | 35,8 MB | não extraída | — |
| B4 | → `Estacoes_SLE.csv` | limitado especializado | 57,7 MB | não extraída | — |
| B5 | → `Estacoes_SLP.csv` | limitado privado | **5,1 GB** | não extraída | — |
| B6 | → `Estacoes_Mosaico_STEL.csv` | mosaico STEL | **5,3 GB** | não extraída | — |
| C | Inventário de Bases da Anatel | catálogo de tudo que a agência publica | 129 linhas | **obtida** | `dados/inventario.csv` |

---

## 2. Onde baixar (caminhos que funcionam)

**Servidor direto da Anatel** — este é o caminho que funciona:

```
https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/prestadoras_servicos_telecomunicacoes.zip
https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_licenciadas.zip
```

**Inventário de bases** (catálogo oficial):

```
https://www.anatel.gov.br/dadosabertos/PDA/Bases_Publicadas/Inventario_de_Bases_de_Dados.csv
```

### Armadilhas confirmadas (todas testadas em 31/10/2026)

1. **O inventário da Anatel está desatualizado.** Ele aponta para `dados.gov.br/dataset/...`,
   endereço do portal antigo. No portal novo esses links dão **404**, tanto por HTTP quanto
   renderizados no navegador. Não confie nos links do inventário.
2. **A API pública do dados.gov.br devolve 401** (`/api/publico/conjuntos-dados/<slug>`).
   Com sessão de navegador autenticada, alguns slugs funcionam e outros dão 404 — o slug
   do portal novo difere do slug antigo.
3. **O nome do arquivo não é o esperado.** Não existe `estacoes_radioamador.zip`.
   O arquivo de estações é um **zip mestre** chamado `estacoes_licenciadas.zip`, que contém
   onze CSVs. Radioamador é um deles: `Estacoes_Radioamador.csv`.
4. **A busca do portal novo não acha esses conjuntos.** Buscar "estações radioamador" em
   `dados.gov.br/dados/busca` retorna **0 resultados**.
5. **`sistemas.anatel.gov.br` devolve 423** (acesso negado) para requisições automatizadas.
   Consulta por indicativo, um a um, só pelo navegador.

---

## 3. Base A — Prestadoras (outorga)

**Arquivo:** `prestadoras_servicos_telecomunicacoes.csv` dentro do zip (79 MB, 277.167 linhas)
**Encoding:** UTF-8 **com BOM** → ler com `utf-8-sig`
**Separador:** `;`

**Colunas (24):** Tipo de Identificação · CNPJ ou CPF · Nome Entidade Prestadora de Serviço ·
Nome Fantasia · Tipo de Entidade · Tipo de Outorga · Fistel da Outorga · Processo SEI da Outorga ·
Data Inclusão da Outorga · Serviço da Notificação · Código e Nome do Serviço da Notificação ·
Fistel da Notificação · Processo SEI da Notificação · Data Inclusão da Notificação ·
Logradouro/Número/Complemento/Bairro/CEP do Endereço Sede · Código IBGE do Município ·
Nome do Município · UF do Endereço Sede · Telefone Principal · Endereço Eletrônico

**Serviços relevantes:** 302 Radioamador · 400 Rádio do Cidadão · 401 RC Dispensa de Autorização ·
045 SCM · 019 Limitado Privado

**O que TEM:** quem é autorizado, endereço da sede, data de autorização.
**O que NÃO TEM:** indicativo, classe, validade, estação física.

**Achado de qualidade:** telefone e e-mail são `-` em ~99% dos registros de pessoa física.
Os únicos com contato útil são entidades coletivas (LABRE, clubes, escolas).

---

## 4. Base B1 — Estações de Radioamador ★ (a mais importante)

**Arquivo:** `Estacoes_Radioamador.csv` — 11.886.045 bytes
**Registros:** **71.328 estações**
**Encoding:** UTF-8 com BOM · Separador `;`

**Colunas (18):**
`Tipo de Identificação` · `CNPJ ou CPF` · `Nome da Entidade` · `Fistel do Serviço da Estação` ·
`Serviço` · **`Indicativo`** · **`Número da Estação`** · `UF da Entidade` · **`COER` (classe)** ·
`Nome da Estação` · **`Tipo de Estação`** · `Frequências de Operação da Estação` ·
`Município da Estação` · `UF da Estação` · **`Data do Primeiro Licenciamento`** ·
`Data do Último Licenciamento` · **`Data de Validade da Estação`** · **`Status da Validade`**

### Nulidade medida

| Campo | Vazios/NI | % |
|---|---|---|
| Indicativo | 9 | 0,0% |
| COER (classe) | 2 | 0,0% |
| Nome, CPF, UF, datas de licenciamento | 0 | 0,0% |
| Tipo de Estação | 250 | 0,4% |
| Município/UF da Estação | 149 | 0,2% |
| **Data de Validade + Status** | **18.331** | **25,7%** |
| **Frequências de Operação** | **70.095** | **98,3%** ← campo morto |

### Distribuições validadas

**Classe (COER):** Classe C 48.957 (68,6%) · Classe A 12.404 (17,4%) · Classe B 9.123 (12,8%) ·
N/A 842 (= exatamente o nº de CNPJs, ou seja, entidades coletivas)

**Tipo de Estação:** Móvel 38.552 (54%) · Fixa 31.279 (44%) · Repetidora 1.241 ·
Terrena 6 · N/I 250

**Status:** Ativa 52.635 (73,8%) · N/I 18.331 (25,7%) · **Vencida 362 (0,5%)**

### Regras de análise (aprendidas na prática)

1. **Fistel é do serviço, não da estação.** A mesma pessoa tem o mesmo Fistel na fixa e na móvel
   (caso PY1MEL: `01000257142` nas duas). Deduplicar por Fistel **colapsa estações distintas**.
   A chave correta é o **`Número da Estação`**.
2. **Estação móvel não tem município nem UF** — vem `N/A`. Para análise geográfica de móveis,
   usar **`UF da Entidade`**.
3. **"N/I" em validade não significa vencida.** Significa ausência de registro. Só 362 estações
   são explicitamente vencidas. Não afirmar irregularidade sobre os 18.331.
4. **Frequências de Operação está vazio em 98,3%** — não usar para nenhuma análise.

---

## 5. Caso de validação — PY1MEL

| | Estação Fixa | Estação Móvel |
|---|---|---|
| Indicativo | PY1MEL | PY1MEL |
| Classe | A | A |
| Município | Saquarema/RJ | N/A |
| Fistel | 01000257142 | 01000257142 |
| Número da Estação | 1011689763 | 1011689771 |
| 1º Licenciamento | 25/01/2021 | 25/01/2021 |
| Validade | N/I | N/I |
| Status | N/I | N/I |

**Contradição a resolver:** base de outorga (A) mostra autorização em **01/01/1988**;
base de estações (B1) mostra primeiro licenciamento em **25/01/2021**.
Hipótese: a outorga data da autorização do radioamador (com carga em bloco na data "01/01"),
e o licenciamento de 2021 é da estação física. Precisa confirmação antes de publicar.

---

## 6. O que ainda falta conquistar

| Base | Situação | Caminho |
|---|---|---|
| Estações de Rádio do Cidadão | **não localizada** como CSV próprio | provavelmente dentro de outro CSV do zip mestre; verificar `Estacoes_SLP` / `Estacoes_MMA` ou base separada |
| Habilitação (prova/classe) | não encontrada em aberto | `sistemas.anatel.gov.br` bloqueia (423) |
| Histórico de validade (renovações) | não existe em aberto | só a data mais recente está na base |

---

## 7. Próximos passos aprovados

1. [x] Adquirir as bases
2. [x] Validar
3. [x] Documentar (este arquivo)
4. [ ] Decidir o produto: painel de dados · informativo editorial · cartilha
5. [ ] Localizar a base de Rádio do Cidadão em formato de estações

---

## 8. Lição registrada em 01/11/2026 — o teste documentado que não existia

**O que aconteceu.** O `dados.js` publicado no v1.0 pareava o município com a
UF da entidade em vez da UF da estação. Quando o titular mora num estado e tem
estação noutro, o par saía impossível. Medido no arquivo publicado: **599
entradas erradas em 2.890** — "São Paulo/MG", "Curitiba/SP", "Aracaju/RS",
"Aracaju/BA", "Aracaju/DF". O app funcionava sem erro, sem aviso, mostrando
dado falso.

**Por que o bug passou.** A docstring do `gerar_dados_js.py` documentava desde
a primeira versão:

    python3 scripts/gerar_dados_js.py --check    # só confere o existente

Mas não havia uma linha de código que lesse argumento algum. O `main()` não
recebia `argv`. O comando existia na documentação e não existia no programa.

**O caminho que teria pegado.** Com o `--check` implementado, a primeira
execução acusaria três coisas de uma vez: hash do CSV, contagem de registros e
coerência dos índices de município. A checagem de coerência é justamente a que
encontra UF inexistente. Ele teria falhado antes de o arquivo ir para o ar.

**Quando ficou visível.** Só quando três modelos independentes leram o código
e um deles (deepseek-v4-pro) rastreou o pareamento até a linha do gerador.

**Regra que fica.** Documentação não é teste. Um comando que aparece na
docstring e não no código é pior que um comando ausente: cria confiança falsa
em quem mantém o projeto. Toda flag documentada tem de existir, e todo teste
que promete pegar erro de dado tem de rodar antes da publicação, não depois.

**Corolário.** Ao revisar código próprio, ler a docstring e conferir se cada
promessa tem implementação é o teste mais barato que existe — e o que eu não
fiz.

---

## 9. Dado sujo confirmado na coluna "UF da Estação"

Na correção do item anterior apareceu lixo que não estava documentado.
A coluna "UF da Estação" contém, além das 27 siglas:

| Valor | Ocorrências | Tratamento |
|---|---|---|
| `N/A` | 38.552 | estação móvel, sem município — correto |
| `N/I` | 149 | não informado — correto |
| `Pr` | 2 | normalizado para `PR` |
| `mg` | 1 | normalizado para `MG` |
| `rj` | 1 | normalizado para `RJ` |
| `BAHIA` | 1 | normalizado para `BA` |

O `normalizar_uf()` do gerador aceita sigla em qualquer caixa e nome de estado
por extenso. O que não reconhece (`N/A`, `N/I`, vazio) fica fora do dicionário,
porque não é UF — não se inventa estado para preencher campo.

---

## 10. Lição registrada em 01/11/2026 — ZIP64 só existe no arquivo que se mede

**O que aconteceu.** O leitor de ZIP do navegador tinha uma guarda contra
ZIP64 escrita na mesma sessão em que eu medi o pacote da Anatel e concluí:
"nenhuma entrada usa ZIP64". A medição estava correta — para *aquele* arquivo.
Horas depois o Melhym baixou o pacote de novo, do servidor da Anatel, e o app
recusou com a mensagem da guarda.

**Por que o arquivo mudou.** O pacote oficial passou a incluir dois CSVs
gigantes: `Estacoes_Mosaico_STEL.csv` (5.278.660.441 bytes) e
`Estacoes_SLP.csv` (5.118.867.810 bytes). Ambos passam do limite de 4 GB do
formato clássico, o que força o ZIP **inteiro** ao formato de 64 bits. O
`Estacoes_Radioamador.csv`, que é o que interessa, tem apenas 11.888.045 bytes.

**Os dois arquivos medidos.**

| Arquivo | Bytes do ZIP | SHA-256 do pacote |
|---|---|---|
| `dados/` (31/10 19:49) | 224.894.007 | `c1a5cb8f…` |
| `Downloads/` (01/11 13:16) | 224.891.060 | `2600c966…` |

Pacotes diferentes, com **o mesmo conteúdo de radioamador**: o CSV extraído de
ambos tem 11.888.045 bytes e SHA-256 `a0b44a5c…`. Mudou o empacotamento, não o
dado.

**Regra que fica.** Medir um arquivo publicado por terceiro não autoriza
afirmar nada sobre a próxima versão dele. Anatel republica o mesmo dado em
embalagem nova sem avisar. Toda conclusão sobre formato tem de carregar a data
e o hash do arquivo medido, para que a próxima sessão saiba do que ela fala.

**Corolário operacional.** A guarda de ZIP64 que eu chamei de "blindagem
hipotética" foi o que impediu o app de ler 4.294.967.295 como tamanho e
produzir lixo. Guarda que avisa é melhor que parser que adivinha. Mas guarda
que substitui solução é melhor ainda: a resposta correta era implementar
ZIP64, não apenas recusar.

---

## 11. Leitor ZIP64 do navegador — o que foi implementado e como foi provado

**Algoritmo**, em `extrairDoZip()` no `web/index.html`:

1. Localiza o EOCD (`0x06054b50`) varrendo os últimos 66 KB do arquivo.
2. Se os campos de 32 bits estiverem saturados, procura 20 bytes antes do
   EOCD o **ZIP64 End of Central Directory Locator** (`0x07064b50`) e, no
   deslocamento que ele aponta, o registro **ZIP64 EOCD** (`0x06064b50`), de
   onde vêm o total real de entradas e o deslocamento real do diretório
   central, ambos em 64 bits.
3. No diretório central, cada entrada saturada tem o campo extra `0x0001`,
   lido na ordem: tamanho descomprimido, tamanho comprimido, deslocamento.
4. A guarda antiga continua, mas só dispara quando o valor realmente não pode
   ser resolvido.

**Prova, não afirmação.** O teste compara o resultado do leitor do navegador,
executado no Node, com a biblioteca `zipfile` do Python, sobre o pacote real
de 225 MB:

    arquivo: estacoes_licenciadas.zip 224.9 MB
    bytes extraidos: 11886045
    sha256         : a0b44a5c1687c2646caf40c5a5410493aaf32835dcb7ace07780dc4c0180e776
    OK  bate com o oraculo do Python

Hash idêntico ao do oráculo. É o critério observável que faltava: não "extraiu
algo", mas "extraiu exatamente o mesmo que a ferramenta de referência".

---

## 12. Atualização da base pelo navegador

**Por que IndexedDB e não localStorage.** O `dados.js` tem 9,8 MB. O
`localStorage` costuma limitar a 5 MB e recusa em silêncio. O IndexedDB não
estoura e funciona em `file://`.

**O que a atualização faz:**

- extrai o CSV do pacote (`extrairDoZip`)
- calcula o **SHA-256 no próprio navegador** com `crypto.subtle`, o mesmo
  hash que o Python calcula, para que os dois lados acertem ou falhem juntos
- reconstrói a base com o **mesmo critério do gerador**: UF da Estação e
  frequência das repetidoras
- identifica arquivo **idêntico pelo hash** e diz "nada foi alterado" em vez
  de fingir atualização
- guarda em IndexedDB e mostra data/hash no **topo** da página
- permite baixar o `dados.js` regenerado e voltar à base original

**O defeito que isso consertou.** O `reconstruirDados()` do navegador estava
duas versões atrás do gerador: usava UF da Entidade e não calculava
frequência. Quem atualizasse pelo botão perderia a correção de UF e o campo
novo, sem aviso — enquanto quem não atualizasse continuaria correto. Bug que
depende de quem usa é pior que bug único.

---

## 13. Estado de publicação em 01/11/2026

| Release | Situação |
|---|---|
| `v1.0` | primeira publicação, contém o bug de UF. Não usar |
| `v1.1` | publicada por engano de madrugada, incompleta. Texto avisa para não usar |
| `v1.2` | **atual**. Repetidoras com frequência, cartão pessoal, ZIP64, atualização |

ZIP da v1.2: 3.098.779 bytes,
`sha256 7649d77833c3b1a49290c35bf978b5cc3486df18540437a608539657a9a82e14`,
com 4 arquivos (`index.html` 79.173 · `dados.js` 9.807.801 · `README.md` ·
`LICENCA.md`).

**O que fica fora do Git, de propósito:** `dados/` (305 MB brutos,
rebaixáveis), `prototipos/`, `revisao/`, `__pycache__/`.

---

## 14. Número confirmado pelo `--check` (01/11/2026)

    dados.js : 9,804,238 bytes, 71,328 registros
    CSV sha256 atual : a0b44a5c1687c2646caf40c5a5410493aaf32835dcb7ace07780dc4c0180e776
    OK   hash do CSV confere com o registrado no dados.js
    OK   total de registros confere
    OK   todos os municipios apontam para UF existente
    schema do dados.js: 2
    repetidoras no CSV: 1,241 | com frequencia no dados.js: 1,233
    OK   99.4% das repetidoras com frequencia

Distribuição por faixa: 2 m 848 · 70 cm 384 · 1,25 m 39 · 10 m 16 · 6 m 9 ·
33 cm 4 · 23 cm 3. A soma passa de 1.233 porque as 67 multibanda entram em
mais de uma faixa.

---

## 15. Pendências abertas em 01/11/2026

1. **Ano de 1988 (autorização original)** — cruzar a base de outorga com a de
   estações. **Não medido.** Não há número a reportar ainda.
2. **Base de Rádio do Cidadão** — ainda não localizada como CSV próprio.
3. **Histórico de renovações** — não existe em aberto; só a data mais recente.
4. **Mapa de estações** — impossível sem coordenadas na base; quebraria a
   promessa de funcionar sem internet.
