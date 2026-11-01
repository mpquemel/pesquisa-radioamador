# Arquitetura Web — Radioamador Brasil (offline-first, arquivo único)

**Projeto:** radioamador-brasil
**Documento:** relatorios/arquitetura-web.md
**Autor:** Melhym Pereira Quemel, PY1MEL (mpquemel@gmail.com)
**Data:** 31/10/2026
**Status:** decisão de arquitetura + especificação de implementação

---

## Sumário executivo

O usuário quer distribuir um **ZIP** que a pessoa descompacta em qualquer lugar,
clica em `index.html` e usa — **sem Python, sem servidor, sem instalação**, no
Windows (maioria), celular e Linux. O público é frequentemente leigo, com muitos
radioamadores idosos e **pessoas cegas** usando NVDA (Windows) e TalkBack
(Android).

A resposta curta, com números medidos nesta sessão:

1. **Não existe servidor.** Logo, qualquer solução precisa carregar os 71.328
   registros pelo navegador, do disco local, sob o protocolo `file://`.
2. **`fetch()` de `file://` é bloqueado** por CORS no Chrome/Edge/Firefox. **Não
   funciona** como mecanismo de carga de dados. (Confirmado por especificação e
   por comportamento real; detalhe na seção 1.)
3. A solução que **funciona de verdade** é um arquivo `.js` com
   `window.DADOS = [...]` carregado por `<script src="dados.js">`. Medimos:
   **10,58 MB** (array de arrays compactado), parse em **~295 ms** no Node
   (proxy conservador para o parse do navegador).
4. Para o público leigo/idoso, o ideal é **um único `index.html`** com tudo
   embutido (dados + código + CSS). O custo é um arquivo de ~11 MB que o
   navegador parseia em < 1 s. Aceitável. A variante "dados separados" é
   oferecida como alternativa, mas **não é a recomendada** para o leigo.

O resto deste documento fundamenta cada ponto com números, especifica a
acessibilidade (a parte mais importante) e entrega um plano em fases.

---

## 1. Decisão de arquitetura — carregar 71 mil registros sem servidor

### 1.1 As quatro opções, comparadas com medição real

Construímos protótipos reais (pasta `prototipos/`) a partir do `radioamador.db`
(71.328 linhas), com os 15 campos úteis para busca e exibição. Números medidos
nesta máquina (WSL2, Node v24; o parse do navegador tende a ser comparável ou
um pouco mais lento, mas a ordem de grandeza é a mesma):

| Opção | Funciona em `file://`? | Tamanho | Parse | Veredito |
|---|---|---|---|---|
| **(a) `.json` externo + `fetch()`** | **NÃO** (CORS bloqueia) | 10,58 MB | — (não chega a parsear) | Descartada |
| **(b) `.js` com `const DADOS=[...]` via `<script>`** | **SIM** | 10,58 MB | **~295 ms** (medido) | **Recomendada** |
| **(c) IndexedDB + importação inicial** | SIM (mas precisa da opção (b) ou (d) para popular) | 10,58 MB + overhead | parse + gravação em IDB (mais lento na 1ª vez) | Não justifica |
| **(d) dados embutidos no `index.html`** | **SIM** | ~11 MB (HTML + dados) | ~300 ms | **Recomendada para o leigo** |

### 1.2 Por que `fetch()` de `file://` não funciona (e o que funciona de fato)

**Fato, não opinião:** a especificação do navegador trata toda página `file://`
como *origem opaca* (opaque origin). O modelo de segurança do Chrome/Edge e do
Firefox bloqueia `fetch()` e `XMLHttpRequest` de recursos locais a partir de uma
página `file://`, retornando erro de CORS ("Cross origin requests are only
supported for protocol schemes: http, data, chrome, ..."). Não há cabeçalho
`Access-Control-Allow-Origin` que o autor do ZIP possa injetar — a origem é o
próprio sistema de arquivos, e o navegador não emite a permissão.

Consequência prática: **qualquer desenho que dependa de `fetch('dados.json')`
quebra silenciosamente** quando o usuário dá dois cliques no `index.html`. Para
o público-alvo (idosos, cegos, leigos), uma tela em branco é o pior desfecho
possível.

O que **funciona de fato** em `file://`:

- `<script src="dados.js">` — carregamento de script **não** sofre a mesma
  restrição de CORS quando referenciado por tag `<script>` (o navegador trata
  como *script clássico* local, não como *fetch* de dados). Este é o mecanismo
  canônico para dados locais.
- `<link rel="stylesheet">` e `<img>` locais — idem.
- Dados **embutidos** diretamente no HTML/JS inline — sempre funciona.
- `<script type="module">` **não** funciona em `file://` por padrão (mesma
  restrição de CORS). Evitar módulos ES; usar script clássico.

### 1.3 Por que `const DADOS = [...]` em `.js` (opção b) vence

- **Funciona** em `file://` sem exceção (ponto não negociável).
- **Parse rápido e sem API assíncrona:** o motor JS parseia o literal de array
  durante a avaliação do `<script>`, sem `JSON.parse` explícito, sem `await`,
  sem callback. Medimos **294,9 ms** para avaliar o arquivo de 10,58 MB
  (`prototipos/prot_dados_arrays.js`). O `JSON.parse` do mesmo conteúdo levou
  ~101 ms (mas exige o `fetch` que não funciona em `file://`, ou um
  `XMLHttpRequest` também bloqueado). A diferença de ~190 ms é irrelevante
  diante da garantia de funcionamento.
- **Compatibilidade total** com navegadores antigos (inclusive os que um
  radioamador idoso possa ter) — script clássico roda em qualquer coisa desde
  IE11, ao contrário de módulos ES e de `fetch` em `file://`.

### 1.4 Por que IndexedDB (opção c) não compensa

IndexedDB resolve *persistência entre sessões*, mas:

- Para **popular** o IndexedDB na primeira execução, você **já precisa** de uma
  das opções que funcionam (b ou d) para carregar os dados uma vez.
- Adiciona assincronia, estados de erro, e um primeiro carregamento **mais
  lento** (parse + serialização + gravação em IDB) do que simplesmente avaliar
  o array em memória a cada abertura.
- O ganho (evitar re-parse de 300 ms) não paga a complexidade e o risco de
  falha silenciosa para um público leigo.
- A base é **estática** entre atualizações; "guardar em IDB" não traz vantagem
  de consulta (não há índice que bata 71 mil entradas em memória para buscas
  por substring — veja §4).

**Veredito:** IndexedDB fica **fora de escopo** para a v1. Reavaliar apenas se
futuramente houver funcionalidade que exija estado local (ex.: favoritos,
histórico).

### 1.5 A recomendação final

**Opção (d) — dados embutidos no `index.html`** para o público-alvo deste
projeto, com **opção (b) — `dados.js` separado** como variante "avançada" para
quem quiser atualizar a base trocando um arquivo só.

Racional:

- O leigo/idoso/cego só precisa de **um arquivo**. Menos chances de quebrar
  (arquivo extra perdido ao copiar, antivírus removendo o `.js`, etc.).
- 11 MB é um preço pago uma única vez a cada abertura, em ~300 ms.
- O fluxo de **atualização** fica mais simples se o dado for um `.js` separado
  (troca-se `dados.js` e pronto — veja §4.6), mas para **distribuição** o
  embutido é mais à prova de erro.

**Decisão de distribuição:** o ZIP entrega `index.html` **com dados embutidos**.
Separadamente, um `ferramentas/atualizar.py` (opcional, para quem tem Python)
pode regenerar tanto o `index.html` embutido quanto um `dados.js` avulso.

---

## 2. Tamanho — a conta real

### 2.1 Campos necessários (não todos os 18 do CSV)

Dos 18 campos do `Estacoes_Radioamador.csv`, descartamos para a web:

- `Frequências de Operação da Estação` — **98,3% vazio** (campo morto, já
  documentado em BASES.md). Não entra.
- `Serviço` — é sempre "Radioamador" nesta base. Não entra.
- `Nome da Estação` — valor gerado ("Estação_001" etc.), sem utilidade para o
  leigo. Não entra.
- `UF da Estação` — redundante com `UF da Entidade` para fixa/repetidora e
  `N/A` para móvel. Mantemos apenas a **UF da Entidade** (que sempre existe).

Mantemos **15 campos** (busca + exibição):

`indicativo, nome, doc, doc_digitos, tipo_doc, fistel, classe, tipo_estacao,
uf_entidade, municipio, dt_primeiro, dt_ultimo, dt_validade, status,
num_estacao`

> **Nota de privacidade (importante):** o campo `doc` **já vem mascarado** da
> Anatel — CPF aparece como `***44543**` (só 5 dígitos do meio visíveis) e
> `doc_digitos` captura apenas esses 5 dígitos. Ou seja, **não é possível
> buscar por CPF completo** com dados públicos; a busca por "CPF" na prática é
> busca por esses 5 dígitos visíveis. O CNPJ (entidades coletivas) vem inteiro.
> Isso não é limitação nossa — é o formato dos dados abertos. A interface deve
> deixar isso claro (evita frustração e evita prometer o impossível).

### 2.2 Medição de tamanho (real, não estimado)

| Formato | Tamanho | Redução |
|---|---|---|
| Array de objetos (`[{indicativo:"..", nome:"..", ...}, ...]`) | **24,46 MB** | — (baseline) |
| Array de arrays + dicionários (UFs, municípios, classe, tipo codificados) | **10,58 MB** | −57% |
| Array de objetos, gzip −9 | 2,88 MB | — |
| Array de arrays, gzip −9 | **2,38 MB** | — |

Arquivos gerados: `prototipos/prot_dados_objetos.json`, `prototipos/prot_dados_arrays.json`
e os `.gz` correspondentes.

### 2.3 A conta da redução (array de arrays)

Três transformações explicam os −57%:

1. **Array de arrays em vez de objetos.** Cada registro deixa de repetir 15
   chaves nomeadas (`"indicativo":`, `"nome":`, ...) ~15×71.328 = ~1 milhão de
   vezes. As chaves viram **uma única lista** de ordem fixa (`"c":[...]`), e
   cada linha é só o vetor de valores.
2. **Dicionário de UFs.** `uf_entidade` deixa de ser a string "SP" repetida e
   vira um inteiro (`0..26`), com a tabela `uf:["AC",...,"TO"]` (27 entradas)
   no cabeçalho do payload.
3. **Código numérico para classe e tipo.** `"Classe A"`/`"Classe B"`/
   `"Classe C"` viram `1/2/3` (e `N/I` = 0); `"Fixa"/"Móvel"/"Repetidora"/
   "Terrena"` viram `1/2/3/4`. As tabelas de decodificação viajam no cabeçalho
   (4 e 5 entradas respectivamente).
4. **Dicionário de municípios.** 2.277 municípios distintos → inteiro `0..2276`,
   com a lista de nomes no cabeçalho. (Município é o maior ganho: nomes longos
   repetidos em milhares de linhas.)

### 2.4 Por que **não** distribuir gzip

O gzip levaria os dados a 2,38 MB, mas **não serve** para o caso de uso:

- Para **descomprimir no navegador** precisaríamos da API `DecompressionStream`
  (suporte desigual) e, de qualquer forma, **primeiro** precisaríamos carregar
  o `.gz` — o que nos joga de volta no `fetch()` bloqueado em `file://`.
- Gzip só faria sentido com **servidor** (que manda `Content-Encoding: gzip`).
  Sem servidor, não há quem descomprima de forma transparente.

**Conclusão de tamanho:** 10,58 MB **não comprimido** é o número de trabalho.
É aceitável para os alvos (Windows desktop, celular com alguns GB de
armazenamento). Se um dia houver servidor, o mesmo payload cai para ~2,4 MB em
trânsito — a estrutura já está pronta para isso.

---

## 3. Acessibilidade — a parte mais importante

O app CLI (`consultar.py`) já foi escrito com leitor de tela em mente (saída
linear, "rotulo: valor", nada de arte ASCII). A versão web **precisa manter o
mesmo padrão** e, onde a web permite, ir além. Esta seção é a especificação
normativa.

### 3.1 Princípio geral

> Uma pessoa cega total usando NVDA deve conseguir **buscar, ouvir o número de
> resultados, navegar até eles e ouvir cada registro** sem nunca tocar no mouse
> e sem adivinhar a estrutura. O TalkBack (Android) e o VoiceOver (iOS) devem
> ter a mesma experiência.

### 3.2 HTML semântico obrigatório

Estrutura fixa do documento (uma única página):

```
<html lang="pt-BR">
  <head> ... <title>Radioamador Brasil — consulta de estações</title> ...
  <body>
    <a class="pular" href="#resultados">Pular para os resultados</a>  <!-- skip link -->
    <header>  <h1>Radioamador Brasil</h1>  <p>Consulta de estações — Anatel</p> </header>
    <nav aria-label="Navegação principal">  <!-- links: Consulta | Manual | Legislação | Atualizar --> </nav>
    <main id="principal">
      <h2>Buscar estações</h2>
      <form id="busca" ...>  <!-- filters, um <fieldset> por grupo --> </form>
      <section id="resultados" aria-labelledby="titulo-resultados" tabindex="-1">
        <h2 id="titulo-resultados">Resultados</h2>
        <p id="contador" role="status">Nenhuma busca ainda.</p>
        <div id="lista-resultados"> ... </div>
      </section>
    </main>
    <footer> ... créditos, fonte dos dados, licença ... </footer>
  </body>
</html>
```

Regras:

- **Um único `h1`** (o título da aplicação). `h2` para seções (Busca,
  Resultados, Manual, Legislação). `h3` dentro de cada resultado.
- **`<main>`** delimita o conteúdo principal (ponto de aterrissagem do NVDA).
- **`<nav>`** com `aria-label` para a navegação.
- **`<form>`** real, com **`<button type="submit">`** real (não `<div>`).

### 3.3 Labels reais em todos os campos

- **Todo** controle de formulário tem `<label for="...">` **explícito**, nunca
  só `placeholder`.
- Cada grupo de filtros vive num **`<fieldset>`** com **`<legend>`**:
  - `<fieldset><legend>Identificação</legend>` → indicativo, nome, documento,
    Fistel.
  - `<fieldset><legend>Localização</legend>` → UF (select), município.
  - `<fieldset><legend>Características</legend>` → classe (select), tipo
    (select), status (select).
- Exemplo correto:
  ```html
  <label for="campo-indicativo">Indicativo (ex.: PY1MEL)</label>
  <input id="campo-indicativo" name="indicativo" type="text"
         autocomplete="off" spellcheck="false">
  ```
- **`<select>` para UF/classe/tipo/status**, com um `<option>` inicial vazio
  ("Todos" / "Qualquer"), nunca campos de texto livres para valores enumerados.
- Campos de texto recebem `autocomplete="off"` e, para indicativo,
  `spellcheck="false"` e transformação para maiúsculas automática (mas via
  lógica, não via CSS apenas — o valor enviado deve estar normalizado).

### 3.4 Anúncio de resultados — `aria-live`

O leitor de tela precisa **ouvir** "encontrados N resultados" sem que o usuário
precise procurar. Dois mecanismos combinados:

1. **`role="status"`** (ou `aria-live="polite"`) num elemento **sempre presente
   no DOM** (não criado dinamicamente no momento da busca — isso quebra o
   anúncio em alguns leitores):

   ```html
   <p id="contador" role="status" aria-live="polite" aria-atomic="true">
     Nenhuma busca ainda.
   </p>
   ```

   A cada busca, o JavaScript substitui **o texto interno** (não o elemento)
   por `"Encontrados 37 resultados para 'PY1'."` — o NVDA/TalkBack anunciam
   automaticamente.

2. Para resultados grandes (> limite exibido), o texto do contador **inclui** a
   orientação: `"Encontrados 1.240 resultados. Exibindo os 25 primeiros. Refine
   a busca para ver menos."`

Regra de redação (herdada do CLI): **nunca** deixar área de resultados em
branco sem explicação. Sempre há um texto dizendo o que foi buscado e como
ajustar.

### 3.5 Foco gerenciado após a busca

Após clicar/enviar a busca:

1. O foco move-se para o **título dos resultados** (`#titulo-resultados` ou o
   contêiner `#resultados` com `tabindex="-1"`), via `elemento.focus()`.
2. `tabindex="-1"` no alvo permite receber foco programático **sem** entrar na
   ordem de Tab (o usuário não ganha um "stop" extra).
3. O `role="status"` anuncia o número **enquanto** o foco já está no título dos
   resultados — ordem que o leitor de tela respeita: primeiro o status, depois o
   ponto de foco.

Isso dá ao cego a experiência: "apertei buscar → ouvi '37 resultados' → estou
já no começo dos resultados".

### 3.6 Navegação só por teclado e ordem de Tab lógica

- **Todos** os controles são focáveis e acionáveis por teclado: `<button>`,
  `<input>`, `<select>`, links. Nada de `onclick` em `<div>` ou `<span>`.
- Ordem de Tab: skip link → nav → campos do formulário (na ordem visual) →
  botão Buscar → botão Limpar → resultados (cada item) → footer.
- Cada **resultado** é um bloco com `h3` (indicativo) e lista `dl`/`ul` de
  "rotulo: valor". O usuário navega entre resultados com `H` (cabeçalhos) no
  NVDA, ou com Tab/leitura contínua no TalkBack.
- **Atalho de teclado:** `Alt+1` = foco no campo de busca (accesskey documentado
  visivelmente), `Alt+2` = pular para resultados. (Accesskey é imperfeito, mas
  útil para o público cego; documentar as teclas no próprio texto visível.)

### 3.7 Contraste e zoom 200%

- **Contraste mínimo 4,5:1** para texto normal, 3:1 para texto grande e
  controles (WCAG 2.2, critério 1.4.3/1.4.11). Usar paleta com fundo claro e
  texto escuro (ex.: `#1a1a1a` sobre `#ffffff`), links sublinhados (não só por
  cor).
- **Sem `user-scalable=no`** no viewport. O zoom deve chegar a **200%** sem
  quebra de layout (WCAG 1.4.4). Layout em coluna única, largura máxima
  `max-width` com quebra de linha; **não** usar larguras fixas em `px` para
  contêineres de texto.
- **Foco visível** sempre: `:focus-visible` com contorno de 2–3 px contrastante
  (nunca remover o outline sem substituir por algo igualmente visível).
- Nada depende de cor para transmitir informação (ex.: "campo em vermelho"
  também precisa de texto/marca). Status "Vencida" ganha ícone **e** texto.

### 3.8 Funcionamento com os três leitores

| Leitor | Plataforma | Pontos de atenção |
|---|---|---|
| **NVDA** | Windows | `role="status"` + `aria-live="polite"` anunciam bem; navegação por `H` e `Tab`; testar o skip link e o foco pós-busca. |
| **TalkBack** | Android | `aria-live` funciona; explorar por "tocar para focar" e gesto de deslizar; testar o `<select>` nativo (não usar `<select>` customizado em `<div>`). |
| **VoiceOver** | iOS | `role="status"` anuncia; testar rotor (cabeçalhos, campos de formulário). |

**O que NÃO usar** (lista negra, WCAG 4.1.2 e boas práticas):

- ❌ `<div onclick="...">` ou `<span role="button">` no lugar de `<button>`.
- ❌ `placeholder` como único rótulo (some ao digitar; alguns leitores ignoram).
- ❌ `<select>` customizado em `<div>`/`<ul>` (quebra no TalkBack/VoiceOver).
- ❌ `aria-hidden` em conteúdo que ainda é focável/interativo.
- ❌ Tabela só para layout; se usar `<table>`, que seja dado tabular **real**
  com `<caption>`, `<th scope="col|row">`.
- ❌ `display:none` para "esconder" texto que o leitor deveria ler (usar classe
  `.visually-hidden` — `position:absolute; clip-path:inset(50%)` — que esconde
  visualmente mas mantém no fluxo do leitor).
- ❌ Mover o foco para o topo da página (ou para lugar nenhum) após a busca.

### 3.9 Roteiro de teste real com leitor de tela

Testar manualmente (não dá para automatizar a percepção de um humano cego —
registrar cada passo):

1. **Carga fria:** abrir `index.html` com NVDA ativo. Ouvir o `h1` e a descrição.
   A página **não** deve travar nem anunciar "carregando" por tempo perceptível
   (> 1 s já é incômodo; medimos ~300 ms de parse).
2. **Skip link:** primeiro `Tab` → "Pular para os resultados" → Enter → foco no
   título "Resultados".
3. **Busca por indicativo:** `Alt+1` → campo indicativo → digitar "PY1MEL" →
   Enter. Ouvir **"Encontrados N resultados"** (status) e cair no título dos
   resultados. Verificar que o foco foi para os resultados, não ficou no
   formulário.
4. **Navegar resultados:** `H` (cabeçalho) para pular entre registros; cada
   registro lido como "Indicativo: ... Nome: ... Classe: ... Fistel: ...".
   Conferir que o Fistel aparece isolado e copiável.
5. **Busca vazia:** buscar algo inexistente. Ouvir "Nenhum resultado para ..." +
   sugestão de ajuste. **Nada de tela branca.**
6. **Filtros combinados:** selecionar UF + classe via `<select>`. Verificar
   anúncio correto do contador e que os filtros foram respeitados.
7. **Teclado puro:** percorrer todo o fluxo sem mouse (Tab, Shift+Tab, Enter,
   setas no `<select>`). Nenhum elemento "pulado" ou inacessível.
8. **Zoom 200%:** Ctrl+`+` duas vezes. Verificar que nada quebra, nada some,
   texto continua legível.
9. **TalkBack (Android):** repetir passos 3–6 num celular. Testar o `<select>`
   nativo e o gesto de exploração.
10. **VoiceOver (iOS):** repetir 3–6 com o rotor de cabeçalhos/campos.

**Critério de aceite:** todos os passos 1–10 passam sem intervenção de mouse e
sem "adivinhar" — a experiência de quem não enxerga é equivalente à de quem vê.

---

## 4. Funcionalidades a especificar

### 4.1 Busca

Campos de busca (todos opcionais e combináveis com `AND`):

| Campo | Tipo | Busca real |
|---|---|---|
| Indicativo | texto | igualdade exata (normalizado: sem acento, maiúsculo, sem espaço) |
| Nome | texto | contém, por palavra (normalizado, sem acento) |
| Documento (CPF/CNPJ) | texto | só dígitos; **CPF é mascarado → só os 5 dígitos visíveis** (documentar) |
| Fistel | texto | só dígitos, igualdade |
| UF | select (27 + "Todos") | igualdade |
| Município | texto | contém (normalizado) |
| Classe | select (A/B/C/Todas) | igualdade |
| Tipo de estação | select (Fixa/Móvel/Repetidora/Terrena/Todos) | igualdade |
| Status | select (Ativa/Vencida/N-I/Todos) | igualdade |

**Normalização** espelha a do `consultar.py`: `NFKD` → remove diacríticos →
minúsculas → `split`/`join`. Implementar em JS (função pequena, sem dependência
externa — não pode haver `fetch` nem CDN).

**Busca por substring em 71 mil registros:** a cada consulta, percorrer o array
em memória com `Array.prototype.filter` e as condições. Medimos que o parse leva
~300 ms; um `filter` linear sobre 71 mil itens é da ordem de **poucos ms a
dezenas de ms** no navegador moderno — **não precisa de índice**. (Não medimos o
`filter` em si; declaro como "não medido" e sugiro validar na fase 2. Se ficar
lento, a otimização é particionar por UF e filtrar só o subconjunto.)

### 4.2 Limite de exibição e paginação

- Exibir no máximo **25 resultados** por vez (mesmo default do CLI), com
  botões "Mostrar mais 25" e contador total no `role="status"`.
- Para acessibilidade, cada "página" de 25 refaz o anúncio no `aria-live`.

### 4.3 Exportação CSV

- Botão **"Baixar CSV"** gera o CSV dos resultados **em memória** e dispara
  `download` via **Blob + `URL.createObjectURL` + `<a download>`**.
- **Funciona em `file://`?** Sim — a criação de Blob e o download de dados
  gerados em memória **não** dependem de `fetch`; é conteúdo sintetizado no
  cliente. (Confirmar em teste real no Chrome/Edge/Firefox na fase 2; é o
  caminho padrão e documentado, mas a regra deste projeto manda testar.)
- Encoding UTF-8 **com BOM** (`\uFEFF` no início) e separador `;` — compatível
  com Excel brasileiro (o CSV da Anatel já usa `;` e BOM; manter consistência).
- Nome do arquivo: `radioamador_resultados_YYYYMMDD_HHMM.csv`.

### 4.4 Geração de relatório

- Seção "Relatório" que produz um **resumo em texto linear** (acessível) do
  conjunto filtrado: total de estações, pessoas distintas (por `doc_digitos`),
  contagem por tipo, por classe, por UF, top municípios — espelhando o
  `--resumo` do CLI.
- Saída como texto na página (leitor de tela lê direto) **e** botão de download
  `.txt` com a mesma técnica Blob da exportação.

### 4.5 Manual / README embutido e Legislação

- Seção "Manual" (ou "Como usar") embutida na própria página, em HTML
  semântico, explicando em linguagem simples o que é cada campo, como buscar, o
  que significa Classe A/B/C, o que é Fistel, e **avisando** que CPF é
  mascarado.
- Seção "Legislação" com os textos já coletados em `legislacao/*.md`,
  convertidos para HTML semântico (os `.html` já existem). Incluir o
  `INDICE.md` como sumário. **Aviso de validação** já presente no índice:
  "confirmar no original antes de citar".

### 4.6 Atualização da base — limitações REAIS em `file://`

**O problema:** o usuário pede "baixar da Anatel quando online". De um
`index.html` aberto em `file://`, isso é **tecnicamente limitado**:

1. **CORS bloqueia** `fetch` para `https://www.anatel.gov.br/...` a partir de
   uma origem `file://` (opaque origin). Mesmo que a Anatel enviasse
   `Access-Control-Allow-Origin: *` (não envia), a origem `file://` é
   problemática e o Chrome frequentemente nega.
2. **O arquivo é um ZIP mestre** (`estacoes_licenciadas.zip`, 224 MB) contendo
   11 CSVs. Baixar 224 MB, descompactar e extrair `Estacoes_Radioamador.csv`
   no navegador é inviável: a API de descompressão de ZIP **não existe
   nativamente** no navegador (só gzip/deflate via `DecompressionStream`, e o
   ZIP usa deflate com estrutura própria).
3. Mesmo que tudo isso funcionasse, **`file://` não permite gravar arquivos no
   disco** do usuário sem permissão manual — não há como sobrescrever o próprio
   `index.html` ou `dados.js` automaticamente.

**O que funciona de fato (solução prática):**

- **Botão "Atualizar base"** que **não baixa**, mas **abre a URL oficial** em
  nova aba (`window.open` ou `<a href target="_blank" rel="noopener">`):
  `https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_licenciadas.zip`.
  O usuário baixa manualmente.
- **Instruções claras** (na seção "Atualizar") para substituir o arquivo de
  dados: "baixe o ZIP oficial, e rode o atualizador" — para quem tem Python.
- **Script auxiliar** `ferramentas/atualizar.py` (o `scripts/atualizar_base.py`
  **já existe e faz exatamente isso**: baixa o ZIP, extrai o CSV, reconstrói o
  SQLite e pode regenerar o `dados.js`/`index.html`). O script é o caminho
  correto para o mantenedor (o Melhym), **não** para o usuário final leigo.

**Conclusão honesta:** a atualização automática "dentro do HTML" **não é
possível** em `file://`. A solução de duas vias (botão que abre a URL oficial +
script Python para o mantenedor que redistribui um ZIP novo) é a que funciona.
Dizer isso com clareza evita prometer mágica.

> Alternativa futura (fora do escopo v1): hospedar em HTTPS (ex.: GitHub Pages)
> e usar um Service Worker + IndexedDB para cache offline e atualização
> incremental. Isso resolve CORS e atualização, mas **abandona** o requisito
> "sem servidor / só clicar no arquivo". Registrar como caminho de evolução,
> não como v1.

---

## 5. Estrutura de pastas do ZIP distribuível

```
radioamador-brasil-v1.zip
├── index.html                 ← TUDO embutido: HTML + CSS + JS + DADOS (71.328)
│                                 (recomendado: o leigo usa só este arquivo)
├── dados.js                   ← [opcional/avançado] window.DADOS = [...] (10,58 MB)
│                                 para quem quer trocar só a base
├── legislacao/
│   ├── INDICE.md
│   ├── lei-9472-1997.html
│   ├── norma-31-94.html
│   ├── res-449-2006.html
│   ├── res-719-2020.html
│   └── res-777-2025.md        (e os .md correspondentes, se a seção linkar)
├── manual/
│   └── como-usar.txt          ← versão texto simples do manual (opcional)
├── LEIA-ME.txt                ← instruções em texto puro, para quem prefere
└── LICENCA.txt                ← licença dos dados + créditos
```

Observações:

- O `index.html` embutido **não depende** de `dados.js` — é autossuficiente. O
  `dados.js` avulso existe para o cenário "troque a base sem mexer no HTML".
- **Não** incluir `estacoes_licenciadas.zip` (224 MB) nem o CSV completo no ZIP
  de distribuição — só o que o app consome.
- Os `.html` de legislação já estão prontos em `legislacao/`; a seção de
  legislação do app pode **linkar** esses arquivos locais (links relativos
  funcionam em `file://`).
- `LEIA-ME.txt` e `LICENCA.txt` em texto puro: acessíveis e legíveis em
  qualquer editor (coerente com o público).

---

## 6. Riscos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| 1 | **Antivírus** sinaliza um `.html` de 11 MB com 71 mil registros embutidos como suspeito (heurística de "JS enorme") | Manter o JS **legível e sem ofuscação** (dados puros, nada de `eval`/`atob`/strings cifradas). Assinar/nomear claramente. Distribuir também a variante `index.html` + `dados.js` separado (arquivo de dados puro reduz falso positivo). Testar no Windows Defender antes de liberar. |
| 2 | **ZIP bloqueado por e-mail** (anexo `.zip` ou tamanho) | 11 MB passa na maioria, mas alguns provedores bloqueiam `.zip` ou `.html`. Alternativas: renomear a extensão para `.zip` → `.zip` é o alvo; usar `.7z` (pior); ou distribuir via **link de download** (Drive, Dropbox, GitHub Releases) em vez de anexo. Documentar no README. |
| 3 | **Perda de foco do usuário** (idoso/cego se perde após buscar) | Foco gerenciado (§3.5), `role="status"` (§3.4), navegação por cabeçalhos, "nenhuma tela em branco" (sempre mensagem de estado). |
| 4 | **Base desatualizada** (Anatel publica diariamente) | Mostrar a **data da base** em destaque no topo (ler de `versao_base.json` → embutir no `index.html` no build). Seção "Atualizar" com o botão para a URL oficial (§4.6). O mantenedor regera e redistribui periodicamente. |
| 5 | **Divergência entre HTML e dados** (HTML velho com dados novos ou vice-versa) | **Build determinístico**: um único gerador (a partir do SQLite) escreve `index.html` e `dados.js` juntos, gravando a mesma `data_base` e `sha256` do CSV em ambos. Conferência de hash no carregamento (o HTML valida que o `dados.js` embutido bate com o hash esperado). |
| 6 | **Licença dos dados** (uso e redistribuição dos dados abertos da Anatel) | Ver §6.1. Incluir `LICENCA.txt` no ZIP e atribuição no rodapé. |
| 7 | **Promessa impossível** (atualização automática em `file://`) | Já tratado em §4.6: documentar a limitação e oferecer o caminho que funciona. |
| 8 | **Busca por CPF frustra** (dado mascarado) | Aviso explícito no manual e no próprio campo ("CPF aparece mascarado nos dados abertos; busque pelos dígitos visíveis"). |

### 6.1 Licença dos dados

- Os dados vêm do **portal de Dados Abertos da Anatel** (painéis de dados
  abertos, caminho `dadosabertos/paineis_de_dados/...`), publicados sob a
  **Política de Dados Abertos do Poder Executivo Federal** (Decreto nº
  8.777/2016) e o modelo de **dados abertos governamentais** brasileiro.
- A prática consolidada do portal `dados.gov.br` e das agências é licenciar
  conjuntos como **"Licença de uso e redistribuição" aberta**, tipicamente
  **CC BY (Creative Commons Atribuição)** ou equivalente "Open Data Commons",
  que **exige atribuição da fonte** e permite uso e redistribuição, inclusive
  comercial, **desde que citada a origem**.
- **Ação concreta:** citar no rodapé do app e no `LICENCA.txt`:
  "Fonte: Anatel — Dados Abertos (Estações de Radioamador, base
  `estacoes_licenciadas.zip`), sob a Política de Dados Abertos do Governo
  Federal (Decreto 8.777/2016)." e incluir a URL oficial.
- **Ressalva de verificação:** não baixei e li o texto literal de licença do
  portal durante esta sessão (o inventário da Anatel aponta links quebrados —
  documentado em `BASES.md`). A licença **exata** deve ser confirmada lendo a
  página do conjunto no portal antes da publicação. A obrigação de **atribuição
  + citação de fonte** é segura e deve ser adotada independentemente.
- **Privacidade/LGPD:** os dados são públicos e o CPF já vem **mascarado** pela
  própria Anatel (só 5 dígitos), o que reduz a exposição. Manter a máscara
  como está; **não** tentar reconstruir ou expor CPF completo (nem é possível
  com esta base).

---

## 7. Plano de implementação em fases

### Fase 0 — Preparação do payload (mantenedor)

- **Objetivo:** gerar `dados.js` e o esqueleto de `index.html` embutido a
  partir do `radioamador.db` (ou do CSV), com array de arrays + dicionários.
- **Entregas:** script gerador (novo, ex.: `scripts/gerar_web.py`), `dados.js`
  de 10,58 MB, metadados (data, sha256, total) embutidos.
- **Critério de aceite:** `dados.js` avalia em navegador e expõe `window.DADOS`
  com 71.328 registros; hash confere com o CSV fonte.

### Fase 1 — Núcleo acessível de busca

- **Objetivo:** `index.html` com formulário acessível completo e busca em
  memória, sem estilo, focado em estrutura e leitor de tela.
- **Entregas:** HTML semântico (§3.2), labels/fieldsets (§3.3), `role="status"`
  (§3.4), foco pós-busca (§3.5), navegação por teclado (§3.6), normalização de
  texto espelhando o CLI.
- **Critério de aceite:** roteiro §3.9 passos 1–7 passam com NVDA; busca por
  indicativo, nome, UF, classe combinadas retornam resultados corretos e o
  contador anuncia o número.

### Fase 2 — Estilo, contraste, zoom e validação de performance

- **Objetivo:** aplicar CSS com contraste 4,5:1, foco visível, zoom 200%,
  layout coluna única.
- **Entregas:** folha de estilo embutida, `:focus-visible`, `.visually-hidden`,
  skip link estilizado.
- **Critério de aceite:** roteiro §3.9 passos 8 (zoom) passa; **medir** o tempo
  de carga real no Chrome/Edge (meta: < 1,5 s até interativo) e o tempo de
  `filter` (fecha o ponto "não medido" da §4.1); testar exportação CSV via
  Blob em `file://` (fecha o ponto da §4.3).

### Fase 3 — Exportação, relatório, manual e legislação

- **Objetivo:** botões CSV/TXT (Blob), seção relatório (resumo acessível),
  seção manual embutida, seção legislação linkando os `.html` locais.
- **Critério de aceite:** CSV abre no Excel brasileiro com BOM+`;` e acentos
  corretos; relatório lê corretamente no leitor; manual explica cada campo;
  legislação navegável por cabeçalhos.

### Fase 4 — Embutir dados no `index.html` + build de distribuição

- **Objetivo:** gerar a variante `index.html` **com dados embutidos** (opção d,
  §1.5) e o ZIP final com a estrutura da §5.
- **Entregas:** gerador que produz `index.html` (embutido) e `dados.js`
  (avulso) juntos, `LEIA-ME.txt`, `LICENCA.txt`.
- **Critério de aceite:** descompactar o ZIP num diretório novo (Windows e
  Linux), clicar em `index.html`, e a busca funciona sem nenhum outro arquivo
  presente; data da base e créditos visíveis.

### Fase 5 — Teste de campo e endurecimento

- **Objetivo:** validação com usuários reais (inclusive cegos com NVDA e
  TalkBack), testes de antivírus (Windows Defender) e de e-mail (anexo vs
  link).
- **Entregas:** registro dos testes, ajustes de acessibilidade e de
  distribuição.
- **Critério de aceite:** roteiro §3.9 passos 1–10 passam; nenhum falso
  positivo crítico de antivírus; decisão documentada sobre distribuição por
  anexo vs link.

---

## 8. Créditos e preservação

- **Autor:** Melhym Pereira Quemel, PY1MEL (mpquemel@gmail.com).
- Os créditos devem aparecer no `<footer>` do `index.html` e no `LEIA-ME.txt`/
  `LICENCA.txt`.
- A base é propriedade pública da Anatel, redistribuída com atribuição (§6.1);
  os créditos autorais referem-se ao **software e ao tratamento** (CLI, SQLite,
  análise, esta arquitetura), não aos dados em si.

---

## 9. Protótipos gerados (para auditoria)

Arquivos na pasta `prototipos/` (prefixo `prot_`, conforme instrução):

| Arquivo | Conteúdo |
|---|---|
| `prot_dados_objetos.json` | 24,46 MB — array de objetos (baseline) |
| `prot_dados_arrays.json` | 10,58 MB — array de arrays + dicionários |
| `prot_dados_arrays.js` | 10,58 MB — mesmo payload como `window.DADOS=...` |
| `prot_dados_objetos.js` | 24,46 MB — variante objetos como `.js` |
| `prot_dados_arrays.json.gz` | 2,38 MB — gzip −9 (referência, não distribuído) |
| `prot_dados_objetos.json.gz` | 2,88 MB — gzip −9 |
| `medir_tempo.js` | script Node que mede parse |

Números de parse medidos (Node v24, WSL2): script `.js` = **294,9 ms**;
`JSON.parse` arrays = **101,3 ms**; `JSON.parse` objetos = **103,8 ms**.

**Não medido** (declarado explicitamente, pendente de validação na Fase 2):
tempo de `filter` linear sobre 71 mil itens no navegador real; download via
Blob em `file://` no Chrome/Edge; tempo de carga real de `index.html` embutido
em Windows vs Linux.
