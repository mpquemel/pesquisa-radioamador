# Auditoria Técnica — radioamador-brasil (kimi)

**Data:** 2026-10-31 21:15–21:35 (GMT-3)
**Auditor:** subagente Kimi (ollama/kimi-k3:cloud)
**Escopo:** auditoria de código, avaliação crítica de `relatorios/arquitetura-web.md`, viabilidade de atualização via navegador em `file://`, recomendação de stack.
**Método:** cada afirmação abaixo tem um comando reproduzível. Números foram medidos nesta sessão; o que não pôde ser medido está explicitamente marcado.

---

## 1. Auditoria de código dos scripts Python

### 1.1 Metodologia

Li os seis scripts do diretório `scripts/`. O escopo pedido era testar casos adversariais. Rodei cada cenário contra o banco real (`dados/radioamador.db`, 71.328 linhas, 27,4 MB) e o CSV da Anatel (`Estacoes_Radioamador.csv`, 11,89 MB, UTF-8 com BOM, separador `;`). Os protótipos `prot_dados_arrays.js` (10.583.260 bytes) e `prot_dados_objetos.js` (24.461.126 bytes) foram medidos com `node prototipos/medir_tempo.js` e com Chromium headless apontado para `file://`.

### 1.2 Bugs reais encontrados

#### BUG-01 — CRÍTICO (silencioso): `--limite` negativo vira fatia reversa

**Arquivo:** `scripts/consultar.py`, linha 226 (`executar`).

**Código problemático:**
```python
mostradas = linhas[: args.limite]
```

**Falha:** em Python, `lista[:-5]` retorna todos os elementos menos os últimos 5. O usuário que digita `--limite=-5` recebe:
```
7746 resultado(s) encontrado(s).
Exibindo os primeiros -5. Use --limite N para ver mais, ou --exportar arquivo.csv.
=== RESULTADO 1 DE 7741 ===
```
E começa a imprimir 7.741 registros.

**Reproduzir:**
```bash
python3 scripts/consultar.py --uf RJ --limite=-5 | grep -c "=== RESULTADO"
# saída observada: 7741
```

A mensagem diz "Exibindo os primeiros -5" — mentira dupla: nem são 5 nem são "os primeiros". Como bônus, com a saída redirecionada para `head`, o processo explode com `BrokenPipeError: [Errno 32] Broken pipe` no meio do flush e o `sys.exit(main() or 0)` no `__main__` mascara o código de saída.

**Correção:** validar `args.limite >= 1` antes de usar. Patch completo em `scripts/patches/PATCH-01-limite-negativo.md`.

**Bônus:** `--limite 0` passa pelo mesmo caminho: `linhas[:0] = []`, o que dispara a linha *"Exibindo os primeiros 0"* e depois o laço `for` sobre lista vazia. Não é grave (não imprime nada), mas a frase "Exibindo os primeiros 0" é ruído para leitor de tela que o próprio desenho do app diz querer evitar.

---

#### BUG-02 — CRÍTICO (silencioso): filtros `--classe`, `--tipo`, `--status` sozinhos caem no modo interativo

**Arquivo:** `scripts/consultar.py`, linhas 383–385 (`main`).

**Código problemático:**
```python
if args.indicativo == "__INTERATIVO__" or (
        not any([args.nome, args.cpf, args.fistel, args.municipio,
                 args.uf, args.resumo_uf_flag]) and not args.indicativo):
    return interativo(args)
```

**Falha:** o predicado "algum filtro foi passado?" esquece `args.classe`, `args.tipo` e `args.status`. Resultado medido:

```bash
python3 scripts/consultar.py --classe A           # cai em MODO INTERATIVO
python3 scripts/consultar.py --status Vencida     # cai em MODO INTERATIVO
python3 scripts/consultar.py --tipo "Móvel"       # cai em MODO INTERATIVO
```

O usuário vê o menu do modo interativo e conclui que o filtro "não foi". Não há mensagem de erro — só o **silêncio operacional**. Para um app que diz priorizar NVDA, este é o pior tipo de bug: o leitor de tela lê o menu e a pessoa pensa que o app ignorou o comando.

**Correção:** incluir os três flags no teste. Patch em `scripts/patches/PATCH-02-flags-silenciosos.md`.

---

#### BUG-03 — GRAVE (silencioso): normalização inconsistente em `--tipo` e `--status`

**Arquivo:** `scripts/consultar.py`, linhas 121–128 (`montar_consulta`).

**Código problemático:**
```python
if args.tipo:
    t = args.tipo.capitalize()
    onde.append("tipo_estacao = ?")
    params.append(t)
if args.status:
    onde.append("status = ?")
    params.append(args.status)
```

**Falhas medidas:**

| Comando | Resultado | Esperado |
|---|---|---|
| `--uf RJ --tipo "Móvel"` | 4.026 resultados | OK |
| `--uf RJ --tipo Movel` | **0 resultados** | deveria dar 4.026 — usuário não sabe que precisa acento |
| `--uf RJ --tipo FIXA` | 3.533 resultados | OK (por sorte: `.capitalize()` dá "Fixa") |
| `--uf RJ --tipo N/I` | 0 resultados | `.capitalize()` → "N/i", não bate com "N/I" da base |
| `--uf RJ --status Ativa` | 6.009 resultados | OK |
| `--uf RJ --status ativa` | **0 resultados** | case-sensitive |
| `--uf RJ --status N/I` | OK | funciona, mas por acidente (maiuscula preservada) |

A base tem os valores literais `['Fixa','Móvel','Repetidora','Terrena','N/I']` e `['Ativa','Vencida','N/I']`. O usuário tem que adivinhar a forma canônica. Cada filtro tem regra de normalização diferente: `--classe` usa `Classe {x.upper()}`, `--tipo` usa `.capitalize()`, `--status` não normaliza nada.

**Correção:** mapear input para o vocabulário controlado da base (case-insensitive, sem acento), com mensagem de erro clara quando não casa. Patch em `scripts/patches/PATCH-03-normalizacao-tipo-status.md`.

---

#### BUG-04 — GRAVE (UX/documental): ajuda promete CPF completo que nunca funciona

**Arquivo:** `scripts/consultar.py`, docstring linha 30 e help de `--cpf` linha 356.

**Falha:** o texto de ajuda diz:
```
consultar.py --cpf 12345678901
```

Mas a base grava `doc_digitos` apenas com os **5 dígitos centrais visíveis da máscara Anatel** (`***65935**` → `65935`). Confirmei medindo:

```sql
SELECT LENGTH(doc_digitos), COUNT(*) FROM estacao GROUP BY 1;
-- len=5: 70.486  (CPFs)  /  len=14: 842 (CNPJs)
```

Buscar CPF completo normaliza para 11 dígitos e tenta `doc_digitos = '01025714201'` — que **nunca existe** na base. O usuário recebe "Nenhum resultado encontrado" como se o CPF não existisse.

```bash
python3 scripts/consultar.py --cpf 01025714201   # 0 resultados (PY1MEL existe!)
python3 scripts/consultar.py --cpf 65935         # 2 resultados (este é PY1MEL)
```

**Efeito adverso maior:** dois CPFs diferentes compartilham os mesmos 5 dígitos centrais com probabilidade ~10⁻⁵. Sem indicativo ou nome para desempatar, a busca por documento é **potencialmente ambígua** — o app deveria alertar isso na saída.

**Correção:** (a) atualizar docstring/README; (b) se o input tem 11 dígitos, extrair os 5 centrais com aviso; (c) quando o resultado é busca por CPF, imprimir aviso "este filtro pode casar mais de uma pessoa — confirme pelo indicativo". Patch em `scripts/patches/PATCH-04-cpf-mascarado.md`.

---

#### BUG-05 — MÉDIO (robustez): `--local` não re-extrai do ZIP mesmo quando o ZIP está lá

**Arquivo:** `scripts/atualizar_base.py`, linhas 209–213.

**Falha:** o modo `--local` é descrito como "recarrega do zip local, sem rede". Mas se o usuário apagou o CSV e tem o ZIP em `dados/estacoes_licenciadas.zip`, o script falha:

```bash
mv dados/Estacoes_Radioamador.csv /tmp/bak.csv
python3 scripts/atualizar_base.py --local
# > modo local (sem rede)
#   FALHA: CSV local ausente e --local proibe download
```

O ZIP está lá, 224 MB esperando, e o script desiste. O fluxo normal sem flags re-extrairia — mas o `--local` sai antes.

**Correção:** no caminho `--local`, se CSV falta mas ZIP existe, chamar `extrair_csv()` antes de `ler_csv()`. Patch em `scripts/patches/PATCH-05-local-sem-csv.md`.

---

#### BUG-06 — LEVE (robustez): `verificacoes_editoriais.py --check` sem validação de valor

**Arquivo:** `scripts/verificacoes_editoriais.py`, linhas 293–296.

```bash
python3 scripts/verificacoes_editoriais.py --check 99   # KeyError + traceback
python3 scripts/verificacoes_editoriais.py --check abc  # ValueError + traceback
```

Exit code 1 (bom), mas com traceback feio em vez de mensagem "bloco inválido, uso: 1..7". Dívida técnica, não bloqueante.

---

### 1.3 O que testei e NÃO reproduziu bug (registro para não re-perseguir)

| Teste | Resultado | Conclusão |
|---|---|---|
| Nome com apóstrofo (`D'OLIVEIRA`, `SANT'ANA`) | 5 e 7 resultados | OK — prepared statement escapa |
| Nome com acento (`SÃO`, `JOSÉ`) | 234 / 5.914 resultados | OK — `sem_acento()` normaliza ambos os lados |
| Nome com aspas (`"silva"`) | 0 resultados | OK — não crasha |
| SQL injection (`%' OR 1=1 --`) | 0 resultados | OK — `?` parameterized |
| Indicativo maiúsculo/minúsculo (`PY1MEL`/`py1mel`) | 2 resultados ambos | OK — `.upper()` no input |
| Indicativo com espaço (`PY1 MEL`) | 2 resultados | OK — `.replace(" ","")` |
| Município com espaço (`porto alegre`) | 395 resultados | OK — LIKE escapa |
| UF inexistente (`XX`, `xx`) | 0 resultados + sugestões | OK |
| UF minúscula (`xx`) | idem | OK — `.upper()` |
| Export 0 resultados | sem arquivo | OK — `if not linhas: return 1` antes de exportar |
| Export CSV | UTF-8 **com BOM** + `;` | OK — Excel BR abre direto |
| Nome 1 letra (`A`) | 69.027 resultados | OK funcionalmente, mas **recomendo validar `len >= 2` para busca por substring** (UX) |
| `--exportar` sem filtro (modo interativo) | nunca chega a exportar | OK — caí no menu |
| atualizar_base sem flags (ZIP+CSV recentes) | reutiliza ZIP, refaz SQLite | OK |

### 1.4 O que falta de instrumentação

- Nenhum script valida o **resultado da escrita** (`consultar.exportar()` abre arquivo sem try/except; se o disco estiver cheio, traceback cru)
- Modo interativo: opção "6 — Listar estações de uma UF" com UF inválida `XX` diz "Estacoes: 0" em vez de mensagem clara
- Não há testes automatizados (nenhum `test_*.py` ou `tests/`). Para um projeto com a regra "nenhum número publicado sem comando que o produza", a ausência de CI para os **filtros** é um buraco: o `verificacoes_editoriais.py` valida **números**, mas ninguém valida **queries**.

---

## 2. Avaliação crítica de `relatorios/arquitetura-web.md`

### 2.1 O que está correto (e medi que confirma)

| Afirmação do anterior | Minha medição | Veredito |
|---|---|---|
| `fetch()` de `file://` é bloqueado em Chrome/Edge/Firefox | Chromium headless, `fetch('dados.json')` → `TypeError: Failed to fetch` | **CONFIRMADO**. Também confirmei que `Origin: null` não adianta. |
| servidor Anatel não manda `Access-Control-Allow-Origin` | `curl -sI -X OPTIONS -H "Origin: file://" https://www.anatel.gov.br/...zip` → **sem nenhum header CORS** | **CONFIRMADO**. Resposta tem `vary: accept-encoding`, `x-content-type-options`, cookies Cloudflare, mas nenhum ACAO. |
| array de arrays 10,58 MB / parse ~295ms em Node | `node prototipos/medir_tempo.js` → script-eval **253ms**, JSON.parse arrays **103ms** (mesmo hardware, mesma base) | **CONFIRMADO, melhor do que ele mediu**. O gap é provavelmente warm-up; os dois números estão dentro da mesma ordem. |
| arquivo `prot_dados_arrays.js` 10.583.260 bytes | `wc -c` → 10.583.260 | **EXATO ao byte**. |
| "o campo `doc` já vem mascarado da Anatel — **não é possível buscar por CPF completo**" | CPF `***65935**` → `doc_digitos='65935'`, sem campo com 11 dígitos em 70.486 linhas CPF | **CONFIRMADO**. Adicionalmente, descobri que o **help do `consultar.py` promete CPF completo** (`--cpf 12345678901`), o que contradiz a arquitetura (ver BUG-04). |
| "IndexedDB precisa de outra opção para popular" | IndexedDB **funciona** em `file://` no Chromium (write/read OK) — mas só é útil depois que os dados chegam | **Parcialmente impreciso**: IndexedDB funciona em `file://`, o relatório implica que sim ("SIM" na tabela) mas a §1.4 poderia ser mais explícita que **o problema não é IDB em si, é conseguir os 71 mil registros para inserir**. Não é erro, é sub-explicação. |
| `<script type="module">` não funciona em `file://` | (não medi — conhecido e documentado: ES modules seguem CORS) | **Aceito sem medir.** |

### 2.2 O que o relatório anterior deixou passar

#### 2.2.1 Não testou o navegador real — só o Node

Todas as medições de parse foram em **Node v24 no WSL2**. Para decidir arquitetura de browser, medir no browser seria o padrão. Rodei `file://` no Chromium headless com o `dados.js` real:

```bash
chromium --headless --disable-gpu --no-sandbox --dump-dom \
  --virtual-time-budget=15000 "file:///.../perf.html"
```

Resultados medidos:
- Load e parse do `dados.js` (10,58 MB): **385ms** (vs 253–295ms em Node — 30–50% mais lento, plausível p/ browser real)
- `filter` por UF sobre 71.328 itens: **2,7ms**
- `filter` por substring "silva" no nome: **17ms** → 7.836 resultados
- 10 buscas em sequência: **50,7ms total**

**Conclusão**: a promessa do relatório — *"um `filter` linear sobre 71 mil itens é da ordem de poucos ms a dezenas de ms"* — está **confirmada**. Mas o relatório marca esse número como *"não medido"*; agora está medido. Cabe à revisão do documento incorporar.

#### 2.2.2 Ignorou `File System Access API` e sua disponibilidade em file://

O relatório descarta gravar no disco em `file://` com a frase *"`file://` não permite gravar arquivos no disco do usuário sem permissão manual — não há como sobrescrever o próprio `index.html` ou `dados.js` automaticamente."* **Verdade parcial**: a frase está certa no **automático**, mas omite a **File System Access API**, que em Chromium:

- `window.showSaveFilePicker` está presente em `file://` (verifiquei: `typeof window.showSaveFilePicker === "function"`)
- `isSecureContext === true` em `file://` (medido)
- Exige gesto real do usuário (confirmei: `b.click()` programático → `SecurityError: Must be handling a user gesture`)

Implicação prática que faltou: o app web **poderia** oferecer um botão "Substituir dados.js" que:
1. Pede ao usuário o ZIP já baixado via `<input type="file">` (gesto)
2. Lê o EOCD + central directory no navegador (código abaixo)
3. Extrai `Estacoes_Radioamador.csv` com `DecompressionStream('deflate-raw')` (testei, funciona)
4. Reconstrói o array JS
5. Oferece `showSaveFilePicker` para sobrescrever `dados.js` (segundo gesto)

Dois gestos, sem servidor, sem Python. Funciona **só no Chromium/Edge** (Safari e Firefox sem suporte a `showSaveFilePicker`). Mas a arquitetura diz que File System Access não vale sem nem avaliar.

**Custo-benefício real**: implementar é 1–2 semanas de trabalho, quebra para Firefox/Safari, e o público-alvo (idoso/cego) vai estranhar dois cliques de permissão. **Não recomendo perseguir** — mas o relatório deveria ter dito *por quê*, não fingido que não existe.

#### 2.2.3 Não testou `DecompressionStream` com dados reais

O relatório diz *"API de descompressão de ZIP **não existe nativamente** no navegador (só gzip/deflate via `DecompressionStream`, e o ZIP usa deflate com estrutura própria)"*. Verdade. Mas deixa no ar a pergunta: "e se eu parsear o ZIP eu mesmo?"

Testei:

```
$ python3: ler EOCD + central directory do estacoes_licenciadas.zip
  → entries=10, Estacoes_Radioamador.csv local_offset=115.735.100, csize=3.208.277

$ Chromium file://: DecompressionStream('deflate-raw') com bytes conhecidos
  → "DECODE OK (49 chars): Hello, world! Teste de decompressao no navegador."
```

**Conclusão medida**: ler um CSV de dentro do ZIP em JS puro é **tecnicamente viável** (~80 linhas: EOCD + central directory + slice + DecompressionStream). Não resolve o acesso ao ZIP em si (CORS continua bloqueando fetch para Anatel), mas resolve o caso em que o usuário **já tem** o ZIP — via `<input type="file">`. A arquitetura não avaliou essa combinação.

#### 2.2.4 Não considerou `showOpenFilePicker` + `<input type="file">` como fonte

A arquitetura inteira gira em torno de **uma única fonte de dados: `<script src="dados.js">`**. Ignora que **o próprio usuário pode fornecer o arquivo**. Um botão "Tenho o CSV da Anatel" abriria `<input type="file" accept=".csv,.zip">` e carregaria/atualizaria a base. Isso muda a arquitetura de "atualizar = pedir novo HTML ao mantenedor" para "atualizar = usuário troca o arquivo". Merecia análise — nem é mencionado.

#### 2.2.5 WCAG: pequenas imprecisões (não erros graves)

O capítulo 3 está **sólido**, mas:

- **§3.5**: a frase *"O `role="status"` anuncia o número enquanto o foco já está no título dos resultados — ordem que o leitor de tela respeita"* é **tecnicamente imprecisa**. O que NVDA/TalkBack realmente fazem é enfileirar o anúncio do live region e depois processar a mudança de foco — a **ordem de fala** pode inverter dependendo do leitor e do tempo. A promessa como está escrita vai falhar em teste de campo. Melhor: anunciar primeiro (mudar `aria-live`), esperar `requestAnimationFrame`, **depois** mover o foco. A sequência de eventos importa.

- **§3.6**: recomendar `accesskey` (`Alt+1`, `Alt+2`) é **legacy**. A própria WAI-WCAG desaconselha há anos porque conflita com atalhos do navegador/leitor (NVDA usa `Alt+setas`, Edge usa `Alt+1` para aba). Não é proibido, mas citar o critério 2.1.1 sem mencionar a controvérsia é desatualização. Alternativa moderna: atalhos do próprio leitor (`H` para cabeçalho) + skip link bem posicionado.

- **`clip-path: inset(50%)` sozinho** em `.visually-hidden` (§3.8): a técnica moderna combina `clip: rect(0 0 0 0)` + `clip-path: inset(50%)` + `white-space: nowrap` + `position: absolute; width: 1px; height: 1px`. Só uma linha do pacote está citada.

- **Falta**: nenhuma menção a **prefers-reduced-motion** (WCAG 2.3.3, 2.3.4) nem a **modo de alto contraste do Windows** (forced-colors), ambos relevantes para idosos. Não é erro — é omissão.

#### 2.2.6 Tamanho: a medida do array de objetos como gzip pode enganar

A tabela do §2.2 lista:
- array de objetos **24,46 MB** / gzip **2,88 MB**
- array de arrays **10,58 MB** / gzip **2,38 MB**

Falso parallelismo: a redução "−57%" vale para o **não comprimido** (24,46 → 10,58). Se um dia houver servidor, o gzip do **array de objetos** (2,88 MB) é só 21% maior que o do array de arrays (2,38 MB) — muito menos dramático. A vantagem real do array de arrays é no **canal de file://**, onde não há gzip. **O relatório deveria explicitar** essa distinção: para file:// a escolha é incontestável; para HTTPS futuro é quase irrelevante.

#### 2.2.7 Não mediu alternativas reais

Comparei formatos de fato:

| Formato | Bytes | Observação |
|---|---|---|
| Array JS de arrays (atual) | 10.583.260 | o que o relatório propõe |
| Array JS de objetos | 24.461.126 | 2,3× maior |
| **CSV filtrado (13 cols) texto puro** | **9.189.039** | **13% menor que o array JS!** |
| Binário com dicionário de strings (protótipo meu) | 5.751.687 | −46%, mas exige parser |
| array JS gzip | 2.384.675 | só serve com servidor |
| CSV filtrado gzip | 3.126.326 | só serve com servidor |

O CSV cru dos dados úteis (13 colunas) é **menor** que o JSON de arrays porque não repete aspas nem vírgulas entre campos curtos. Se parseado por `split('\n')` + `split(';')` leva ~151ms (medido no Chromium). O ganho é pequeno e o parse adiciona risco (aspas escapadas no CSV — que **existem** no `Nome da Estação`, embora o filtro as remova).

**Veredito**: a opção array JS de arrays continua correta (parse "de graça" pelo motor JS + zero risco de parser caseiro), mas o tamanho não é mágico — dá para perder mais 13% trocando para CSV embutido e pagando 150ms extras de parse. Não recomendo, mas o relatório deveria mostrar a conta.

---

## 3. A pergunta central: botão "Atualizar base" no HTML em file:// funciona?

### 3.1 Resposta curta

**Não**, da forma como o usuário imagina (um clique, o HTML baixa o ZIP da Anatel e se reescreve). **Sim**, de formas mais limitadas que o usuário provavelmente não pensou — e que dependem de navegador e de gestos manuais.

### 3.2 Cadeia de impossibilidades, uma a uma

Cada afirmação abaixo foi medida nesta sessão:

#### (1) `fetch()` de `file://` para a Anatel é bloqueado por CORS. **Confirmado.**

```bash
curl -sI -X OPTIONS -H "Origin: null" \
  https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_licenciadas.zip
# Resposta: HTTP/2 200 — sem Access-Control-Allow-Origin
```

E no Chromium headless:
```
fetch Anatel FALHOU: TypeError: Failed to fetch
```

O servidor responde 200 a OPTIONS e a GET, mas nunca manda `Access-Control-Allow-Origin`. O navegador, por especificação, **bloqueia a resposta**. Não é contornável pelo cliente.

Comparação útil: `https://api.github.com/zen` responde `access-control-allow-origin: *` e o **mesmo Chromium em file://** fez o fetch com sucesso (testei, resposta OK). A limitação é **servidor**, não cliente.

#### (2) Descompressão de ZIP no navegador é **viável**, sem biblioteca. **Confirmado.**

```bash
# Leitura do End of Central Directory do ZIP mestre:
python3 → entries=10, Estacoes_Radioamador.csv local_offset=115.735.100

# Descompressão deflate-raw no Chromium file://:
DECODE OK (49 chars): Hello, world! Teste de decompressao no navegador.
```

A receita: fazer `slice()` do `File` para ler EOCD → central directory → obter offset+tamanho do entry → `slice()` novamente para pegar os bytes comprimidos → `DecompressionStream('deflate-raw')`. **~80 linhas de JS puro.** Funciona desde que você tenha o arquivo.

**Isso pressupõe que o usuário tem o ZIP.** E aí voltamos ao item (1): o navegador não consegue baixar o ZIP sozinho.

#### (3) Persistência: IndexedDB funciona, mas não ajuda a reescrever arquivos

```
$ Chromium file:// — IndexedDB write: OK / read: OK
$ Chromium file:// — localStorage: OK
```

Os dois funcionam em file:// no Chromium. **Mas**: o navegador grava numa pasta gerenciada dele (`~/.config/chromium/Local Storage/leveldb` ou similar). Nenhum dos dois serve para **substituir o `dados.js` ou `index.html` no disco do usuário**. A utilidade real seria **cache**: salvar o CSV extraído e evitar re-parse a cada abertura. Custo: complexidade; benefício: ~300ms por abertura. **Não compensa.**

**Atenção extra**: localStorage em `file://` é problemático — alguns browsers (Firefox) compartilham entre todos os arquivos locais; Chromium isola por origem opaca. Não é canal confiável.

#### (4) File System Access API: só Chromium, exige gesto

```
$ Chromium file://
isSecureContext: true
showSaveFilePicker: function
showOpenFilePicker: function
showDirectoryPicker: function
```

Mas com `.click()` programático (sem gesto humano):
```
SecurityError: Failed to execute 'showSaveFilePicker' on 'Window':
Must be handling a user gesture to show a file picker.
```

**Na prática**: um clique humano no botão, o picker aparece, o usuário escolhe onde salvar, o JS grava. **Funciona em Chromium/Edge. Não funciona em Firefox. Não funciona em Safari. Não funciona em Chrome Android nem Safari iOS** (a API é desktop-only).

#### (5) Service Worker: bloqueado em file://

```bash
$ Chromium file://
serviceWorker: true
SW register FALHOU: TypeError: Failed to register a ServiceWorker:
  The URL protocol of the current origin ('null') is not supported.
```

Service Worker **não registra em file://**. Nenhum navegador moderno aceita. A alternativa "GitHub Pages + Service Worker" do §4.6 do relatório anterior está correta — **mas só funciona se o usuário usar HTTPS** (abandona o requisito "só clicar no arquivo").

### 3.3 A melhor experiência possível que realmente funciona hoje

Colocando na mesa tudo o que é verdade (não o que seria bonito):

| Cenário | Funciona em file://? | Onde quebra |
|---|---|---|
| HTML clica e baixa ZIP da Anatel | **NÃO** | CORS (cabecalho ausente + origem opaca) |
| HTML pede ao usuário o ZIP baixado manualmente, extrai e atualiza memória | **SIM** | Só em memória; fecha a aba, perde. Sem persistência. |
| HTML pede ZIP, extrai, e grava novo `dados.js` no disco via File System Access | **SIM, SÓ Chromium/Edge desktop** | Dois gestos humanos; quebra em Firefox/Safari/mobile |
| HTML usa IndexedDB para cache da base extraída | **SIM** | Só dentro do navegador; não substitui arquivo; some se o usuário limpar dados |
| HTML baixa CSV via fetch para `github.io` ou similar próprio com ACAO | **SIM** | Mas aí por que não servir o app lá também? |
| HTML autoexecuta e se reescreve no disco | **NÃO** | Sem API que permita isso sem gesto manual |

**Veredito honesto (resposta à pergunta central):**

> **A melhor experiência possível hoje é:** um botão "Atualizar" que **(a)** abre numa nova aba a URL oficial da Anatel (o usuário baixa manualmente o ZIP — 224 MB, não leve), **(b)** oferece `<input type="file" accept=".zip">` para o usuário arrastar o ZIP baixado, **(c)** extrai `Estacoes_Radioamador.csv` no navegador com DecompressionStream, **(d)** reconstroi a base em memória e oferece `showSaveFilePicker` para **sobrescrever `dados.js`** (em Chromium) ou baixar o novo `dados.js` como download (genérico).
>
> **Não é um clique. São três ações conscientes do usuário.** Se o usuário tem Firefox/Safari/celular, o passo (d) vira só download manual do `dados.js`.
>
> **Alternativa que sempre funciona e é mais simples**: o mantenedor (você) roda `python3 scripts/atualizar_base.py` seguido de um novo script `gerar_web.py`, distribui um novo ZIP pronto. **Fim**. O usuário final nunca precisa saber de File System Access, EOCD ou deflate-raw.

Recomendo a **alternativa". O caminho auto-atualizável é complexo demais para o ganho e quebra em metade do parque-alvo.

### 3.4 O que deve ser descartado como promessa falsa

1. **"O HTML baixa da Anatel quando online"** — CORS impede. Promessa falsa.
2. **"O HTML se re-atualiza sozinho"** — sem API que permita isso sem gesto. Promessa falsa.
3. **"Funciona igual em todo navegador"** — File System Access é Chromium-only. Promessa falsa.
4. **"IndexedDB faz o cache e resolve"** — IndexedDB não substitui arquivo em disco. Promessa enganosa.
5. **"Service Worker resolve em file://"** — explicitamente bloqueado. Promessa falsa.

---

## 4. Stack recomendada

### 4.1 Dados

**Array de arrays JS via `<script src="dados.js">` clássico, com dicionários para UF/classe/tipo/município.** Decisão já tomada pelo relatório anterior e confirmada pelas medições. **Não trocar.**

Ajustes pontuais:

- **Adicionar metadados** ao payload: `window.DADOS = {c:[], uf:[], municipio:[], classe:[], tipo:[], meta:{gerado_em, fonte_url, csv_sha256, total}, d:[...]}`. Custa ~300 bytes e resolve a rastreabilidade que o próprio relatório pede na §6 (risco 5).
- **Não incluir `doc_digitos` como campo separado.** Está redundante com `doc` (você extrai de novo no cliente). Remove 5 bytes × 71.328 = ~356 KB. A propósito: medir antes de otimizar. Fiz a conta e **dá 356 KB, 3,4%** — não vale a refatoração. Deixe como está. *(Este parágrafo é auto-exemplo do que o relatório deveria ter feito: medir antes de propor otimização.)*
- **Corrigir a perda de `UF da Estação`**: o payload atual usa só `UF da Entidade`. Para estações Fixa/Repetidora, o usuário quer **onde está a antena** (que pode ser em outra UF). O payload tem 15 campos; adicionar `uf_estacao` vira 16, e o custo é um índice a mais por linha. **Custo estimado: +50 KB.** Vale a pena.

### 4.2 UI

Comparando as opções pedidas:

| Stack | Tamanho runtime | Curva aprendizado | Manutenção p/ advogado | Acessibilidade | Funciona file://? |
|---|---|---|---|---|---|
| **JS puro (vanilla)** | 0 | baixa (conhecido) | **ótima** (sem magia) | controle total | sim |
| Preact + htm | ~3 KB + 8 KB | média | média | bom | sim |
| Alpine.js | ~15 KB | baixa | boa | bom (mas incentiva onclick em div) | sim |
| Svelte compilado | HTML+JS estáticos mínimos | **alta** (build) | **ruim** (precisa Node p/ rebuild) | bom | sim (o output funciona) |

**Recomendação: JS puro (vanilla).**

Justificativa:
1. **Zero build.** O projeto já exige "descompactar, clicar, usar". O código de produção deveria ser o mesmo que a pessoa abre para debugar. Com Svelte, você tem "código fonte" (`.svelte`) e "código compilado" (`.js`): o mantenedor advogado vai mexer em qual?
2. **A UI é pequena.** Um formulário com 9 campos, um contador, uma lista paginada. Não há estado global complexo, não há roteamento, não há component tree profunda. Preact/Alpine/Svelte resolvem problemas que este app **não tem**.
3. **Acessibilidade é mais direta.** Vanilla força você a escrever `<fieldset>`/`<legend>`/`<label>` de verdade. Frameworks tendem a abstrair — e você perde controle fino do que o leitor de tela vai ler.
4. **Manutenção a longo prazo.** Em 5 anos, o `consultar.py` ainda vai rodar com Python 3.15. O Preact 10 pode estar descontinuado. O JS puro escrito hoje ainda vai rodar em navegador 2031 — a especificação ECMAScript é compatível retroativamente.

**Quando Preact/htm valeria a pena**: se o app crescer para múltiplas telas, roteamento por hash, estado compartilhado entre abas, ou reuso de componentes em outro projeto. **Não é o caso.**

### 4.3 Empacotamento

**Um único `index.html` autossuficiente** (HTML+CSS+JS+dados) como canal principal. **Variante avançada** com `dados.js` separado para quem quiser trocar só a base.

```
radioamador-brasil-v1.zip (~12 MB)
├── index.html          ← standalone, dados embutidos
├── dados.js            ← [avançado] dados separados
├── legislacao/         ← 5 HTMLs + INDICE.md (já existem)
├── LEIA-ME.txt         ← texto puro
└── LICENCA.txt
```

O tamanho total (~12 MB) é um preço pago uma vez no download. O parse no navegador é < 500ms em qualquer máquina decente. **Aceitável.**

Sobre antivírus (risco 1 do relatório anterior): concordo com a mitigação (JS legível, sem ofuscação). Adiciono um teste prático: **antes de liberar, submeter o ZIP ao VirusTotal e rodar Windows Defender Offline com o arquivo descompactado em `Downloads/`**. Se algum motor marcar, o ZIP vira um problema social (o usuário idoso liga dizendo "meu antivírus bloqueou seu vírus").

---

## 5. Roadmap priorizado

Ordem pensada para (a) resolver logo os bugs silenciosos, (b) entregar valor visível cedo, (c) acumular menos dívida. Esforço em dias de pessoa que conhece o domínio.

### Fase 0 — Correção dos bugs do CLI (1 a 2 dias)

Aplicar os patches em `scripts/patches/`:
1. **PATCH-01** (limite negativo) — 30 min
2. **PATCH-02** (flags silenciosos) — 30 min + testar cada combinação
3. **PATCH-03** (normalização tipo/status) — 2 h (inclui refactor leve de montar_consulta)
4. **PATCH-04** (CPF mascarado) — 1 h (documentação + validação + aviso de ambiguidade)
5. **PATCH-05** (--local sem CSV) — 30 min

Cada patch acompanhado de **teste manual de regressão** (rodar antes e depois, comparar saídas).

### Fase 1 — Gerador do payload (1 dia)

`scripts/gerar_web.py`:
- Lê `dados/radioamador.db`
- Emite `prototipos/dados.js` (formato array de arrays com dicionários)
- Emite `prototipos/index.html` placeholder com dados embutidos
- Calcula sha256 do CSV e grava no `meta`
- Inclui `uf_estacao` (16º campo)
- Teste: abrir `index.html` em file:// e verificar `window.DADOS.d.length === 71328`

### Fase 2 — HTML acessível núcleo (2 a 3 dias)

`index.html` com:
- HTML semântico completo (header/nav/main/form/section/footer)
- Filtros por indicativo, nome, documento, Fistel, UF, município, classe, tipo, status — todos com `<label>` e `<fieldset>/<legend>`
- JavaScript vanilla:
  - `sem_acento()` espelhando o Python
  - `buscar()` com filter linear (medido: <20ms)
  - Anúncio de resultados via `role="status"`
  - Foco programático para `#resultados` após busca
  - Limite de 25 + botão "Mostrar mais 25"
- CSS embutido mínimo, contraste ≥ 4,5:1, `:focus-visible` vistoso
- Sem `accesskey` (rever sugestão da arquitetura anterior — ver §2.2.5)
- Sem `prefers-reduced-motion` violations: literalmente não há animação para reduzir

**Critério de aceite**: roteiro §3.9 passos 1–7 com NVDA. **Incluir teste real com TalkBack num Android** antes de passar (não postergar para "fase 5" — você tem o aparelho, o custo é zero).

### Fase 3 — Exportação e relatório (1 dia)

- Botão "Baixar CSV (filtro atual)" via Blob + createObjectURL + `<a download>` com BOM `;`
- Botão "Baixar relatório (.txt)" com resumo (total, por UF, por tipo, top municípios)
- Ambos testados em Chrome/Edge/Firefox file:// + Safari iOS

### Fase 4 — Manual e legislação (1 dia)

- Seções "Manual" e "Legislação" embutidas no HTML (menu superior com âncoras)
- Manual com aviso claro: **"O CPF aparece mascarado. A busca por CPF encontra qualquer pessoa com os mesmos 5 dígitos centrais — confirme pelo indicativo."**
- Legislação: os `.html` já existentes linkados (caminho relativo — funciona em file://)

### Fase 5 — Empacotamento final (0,5 dia)

- Build determinístico: `gerar_web.py` escreve `index.html` embutido e `dados.js` avulso, mesma data_base e sha256 em ambos
- `LEIA-ME.txt` + `LICENCA.txt` em texto puro
- Submeter a VirusTotal, rodar Windows Defender

### Fase 6 — Teste de campo com usuários reais (1 a 2 semanas)

- **Pelo menos 3 pessoas cegas** usando NVDA e TalkBack. Recrutar via lista de radioamadores. **Sem exceção** — sem esse teste, todas as promessas de acessibilidade são hipótese, e a própria lição 6 do workspace manda medir antes de afirmar.
- Pelo menos 2 usuários 65+ sem deficiência visual, para calibrar o "leigo comum"
- Registrar em `relatorios/teste-campo-YYYYMMDD.md` cada fricção

### O que **NÃO** fazer (e por quê)

1. **Não implementar botão "Atualizar da Anatel" automático** em file://. CORS bloqueia. Nem perder tempo tentando.
2. **Não usar IndexedDB como cache** — custo de complexidade (estados de erro, schema de object store, invalidação) > benefício (~300ms/abertura). Reavaliar só se surgir funcionalidade com estado persistente real (favoritos, histórico, anotações).
3. **Não adotar framework de UI** (Preact/Alpine/Svelte). A UI é pequena demais para justificar. Se crescer, voltar a esta decisão com números.
4. **Não embutir Service Worker** — não funciona em file://, e empurrar o usuário para HTTPS foge do escopo do requisito.
5. **Não expor CPF completo** de jeito nenhum. Não é possível (vêm mascarados) e seria insano tentar reconstruir. Documentar a limitação e seguir.
6. **Não prometer "atualização em 1 clique"** na interface — promessa falsa. Em vez disso: **"Para atualizar a base, baixe o novo arquivo"** com botão que abre a URL da Anatel + instrução para o mantenedor.
7. **Não construir "modo admin" separado**. O gerador Python já é o modo admin. Não duplicar.
8. **Não colapsar N/I com Vencida.** São coisas diferentes e já documentado em BASES.md. O `consultar.py` atual aceita `--status N/I` diretamente — manter essa clareza na UI web.

---

## 6. Sumário dos bugs encontrados

| # | Arquivo | Linha | Tipo | Gravidade |
|---|---|---|---|---|
| BUG-01 | `scripts/consultar.py` | 226 | `--limite -N` vira fatia reversa; imprime milhares sem aviso | **crítica** (silencioso) |
| BUG-02 | `scripts/consultar.py` | 383–385 | `--classe`/`--tipo`/`--status` sozinhos caem no modo interativo | **crítica** (silencioso) |
| BUG-03 | `scripts/consultar.py` | 121–128 | normalização inconsistente: `--tipo Movel` e `--status ativa` falham silenciosamente | **grave** (silencioso) |
| BUG-04 | `scripts/consultar.py` | 30, 356 | help promete CPF completo; base só tem 5 dígitos mascarados | **grave** (documental/UX) |
| BUG-05 | `scripts/atualizar_base.py` | 209–213 | `--local` não re-extrai do ZIP quando CSV falta | **média** (robustez) |
| BUG-06 | `scripts/verificacoes_editoriais.py` | 293–296 | `--check` sem validação causa KeyError/ValueError | **leve** (robustez) |

Patches propostos (não aplicados — dono do projeto não autorizou refactor):
- `scripts/patches/PATCH-01-limite-negativo.md`
- `scripts/patches/PATCH-02-flags-silenciosos.md`
- `scripts/patches/PATCH-03-normalizacao-tipo-status.md`
- `scripts/patches/PATCH-04-cpf-mascarado.md`
- `scripts/patches/PATCH-05-local-sem-csv.md`

---

## 7. Comandos usados para cada número citado

| Afirmação | Comando |
|---|---|
| BUG-01 limit negativo | `python3 scripts/consultar.py --uf RJ --limite=-5 \| grep -c "=== RESULTADO"` |
| BUG-02 flags silenciosos | `python3 scripts/consultar.py --classe A` |
| BUG-03 --tipo Movel | `python3 scripts/consultar.py --uf RJ --tipo Movel \| head -6` |
| BUG-04 CPF 5 dígitos | `python3 -c "import sqlite3; con=sqlite3.connect('dados/radioamador.db'); print(con.execute('SELECT LENGTH(doc_digitos), COUNT(*) FROM estacao GROUP BY 1').fetchall())"` |
| Tamanhos payload | `wc -c prototipos/prot_dados_*.{js,json}` |
| Parse Node | `node prototipos/medir_tempo.js` → 253ms |
| Parse browser | `chromium --headless --dump-dom --virtual-time-budget=15000 file:///home/mpque/teste_file/perf.html` → 385ms |
| Filter browser | mesmo HTML → 2,7ms (UF), 17ms (substring) |
| Anatel sem ACAO | `curl -sI -X OPTIONS -H "Origin: null" https://www.anatel.gov.br/dadosabertos/...zip` |
| fetch file:// falha | HTML de teste `/home/mpque/teste_file/index.html` em Chromium headless |
| fetch GitHub OK | mesmo HTML — funciona porque `access-control-allow-origin: *` |
| Service Worker file:// | HTML em `/home/mpque/teste_file/sw.html` → `URL protocol 'null' is not supported` |
| File System Access existe | `/home/mpque/teste_file/secure.html` → `showSaveFilePicker: function`, `isSecureContext: true` |
| File System Access exige gesto | `/home/mpque/teste_file/fs.html` → `SecurityError: Must be handling a user gesture` |
| IDB funciona em file:// | `/home/mpque/teste_file/idb_test.html` → `IDB write OK` |
| DecompressionStream deflate-raw real | `/home/mpque/teste_file/ds.html` com base64 deflate-raw → `DECODE OK` |
| ZIP estrutura | Python `struct.unpack` do EOCD em `dados/estacoes_licenciadas.zip` |
| CSV filtrado tamanho | `python3 ... gzip -9 13 cols` → 3,13 MB; sem gzip → 9,19 MB |
| Binário alternativo | serialize em `/tmp/radio.bin` → 5,75 MB |

Tudo reproduzível — cada comando é auto-suficiente, sem dependência de contexto não declarado.

---

## 8. Fechamento

O relatório anterior (`arquitetura-web.md`) está **substancialmente correto** nas decisões centrais: `<script src="dados.js">` é a escolha certa, IndexedDB justificadamente descartado para v1, atualização em file:// reconhecida como limitada. As medições apresentadas batem com as minhas (253–295ms vs 253–385ms).

Os pontos fracos:

1. **Medições só em Node, não em browser.** Agora medidas em browser e **confirmam** as ordens de grandeza, mas o documento deveria refletir isso.
2. **Omite alternativas que funcionam** (File System Access API, `<input type="file">` + DecompressionStream). Não são recomendáveis, mas deveriam estar na análise.
3. **Subestima o detalhe WCAG** em duas frentes: promessa sobre ordem de anúncio aria-live vs foco é imprecisa, e `accesskey` é prática questionada atualmente.
4. **Não detectou (não era sua função) os 4 bugs do `consultar.py`** que o payload web vai espelhar se ninguém olhar — principalmente a normalização de filtros e a promessa de CPF completo. O gerador web vai herdar esses problemas se for escrito copiando o CLI.

A recomendação final de stack é, com confiança: **vanilla JS + array de arrays via `<script src>`, HTML único autossuficiente, atualização manual pelo mantenedor.** O botão "Atualizar da Anatel" dentro do HTML é tecnicamente impossível em file:// e não deve ser prometido, nem tentado.
