# Pesquisa Radioamador — Brasil

Consulta offline das estações de radioamador licenciadas pela Anatel.
Funciona sem internet, sem instalação e sem servidor — basta abrir o
`index.html` no navegador.

**71.328 estações** de todo o país, com indicativo, classe, tipo de estação,
município, datas de licenciamento e **Fistel** — o número necessário para
emitir o boleto anual.

---

## Para quem só quer usar

Baixe o pacote pronto na página de
[**Releases**](https://github.com/mpquemel/pesquisa-radioamador/releases),
descompacte em qualquer pasta e dê dois cliques em `index.html`.

Nada mais é necessário. Sem Python, sem instalação, sem cadastro.

Funciona no Windows, Linux, macOS, Android e iPhone.

---

## O que o programa faz

**Consulta** por indicativo, nome, parte visível do documento, Fistel,
município, estado, tipo de estação, classe e situação da validade. Os filtros
se somam.

**Acha o Fistel** para o boleto anual — o uso mais frequente.

**Exporta os resultados** em CSV, para abrir no Excel ou LibreOffice.

**Gera relatório resumido** com contagens por tipo, classe e estado.

**Traz o manual de uso** embutido, com explicação de cada campo.

**Traz a legislação** de referência: Lei 9.472/1997, Resolução 719/2020,
Resolução 777/2025, Resolução 449/2006, e as regras de repetidora.

**Atualiza a base** a partir do arquivo oficial da Anatel, quando você baixar
o ZIP novo e apontá-lo no seletor de arquivo.

---

## Acessibilidade

Construído com marcação HTML semântica, para uso com leitor de tela:

- Títulos hierarquizados, navegáveis por atalho de cabeçalho.
- Rótulos reais em todos os campos; nada depende de texto de exemplo.
- Grupos de filtro em `fieldset` com `legend`.
- Resultados anunciados automaticamente por `aria-live`.
- Após a busca, o foco vai para o título dos resultados.
- Nenhuma ação exige mouse.
- Contraste acima de 4,5:1 e suporte a zoom de 200%.

Testado com NVDA.

---

## Limitações conhecidas — leia antes de compartilhar

**O CPF não é pesquisável por inteiro.** A Anatel publica o documento
mascarado, mostrando apenas cinco dígitos (ex.: `***65935**`). É possível
buscar por esses cinco dígitos. O número completo não existe nesta base.

**"N/I" não significa irregular.** Em 25,7% das estações a Anatel não registra
data de validade. Apenas 362 estações aparecem explicitamente como vencidas.

**Estação móvel não tem município.** Os 38.552 móveis vêm com município e
estado como "N/A". Use o filtro de estado do titular.

**O campo de frequências está vazio em 98,3%** dos registros. Não é usado.

**A atualização automática não é possível.** Por restrição de segurança dos
navegadores, um arquivo aberto localmente não pode baixar e regravar dados
sozinhos. O botão abre o site da Anatel; você baixa o ZIP e o aponta no
seletor de arquivo.

---

## Para quem quer reproduzir ou contribuir

### Fonte dos dados

Anatel — Agência Nacional de Telecomunicações, dados abertos:

```
https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_licenciadas.zip
```

O arquivo **não** se chama `estacoes_radioamador.zip`. É o pacote mestre
`estacoes_licenciadas.zip`, que contém onze CSVs — um por serviço. O de
radioamador é `Estacoes_Radioamador.csv`.

Os catálogos oficiais da Anatel apontam para endereços que não respondem mais.
O caminho do servidor acima é o que funciona.

### Estrutura do repositório

```
index.html            aplicativo completo (HTML, CSS e JavaScript)
dados.js              base convertida para JavaScript
scripts/
  atualizar_base.py       baixa da Anatel e monta o SQLite local
  consultar.py            consulta em terminal, acessível a leitor de tela
  gerar_dados_js.py       converte o CSV em dados.js
  verificacoes_editoriais.py  reproduz todo número citado nos relatórios
  coletar_legislacao.py   baixa as normas da Anatel
legislacao/           textos dos atos normativos
relatorios/           estudos e auditorias
BASES.md              mapa das bases públicas e armadilhas de download
```

### Reconstruir a base

Requer Python 3.9 ou superior.

```bash
python3 scripts/atualizar_base.py      # baixa e monta o SQLite
python3 scripts/gerar_dados_js.py      # gera dados.js
```

### Consultar pelo terminal

```bash
python3 scripts/consultar.py -i PY1MEL
python3 scripts/consultar.py --fistel 01000257142
python3 scripts/consultar.py --resumo-uf AC
```

### Conferir os números dos relatórios

```bash
python3 scripts/verificacoes_editoriais.py
```

Todo número publicado nos relatórios nasce de um comando deste script.

---

## Licença

O código deste projeto é de uso livre, com atribuição.

Os dados são públicos, publicados pelo governo federal, e podem ser
reutilizados com atribuição à fonte, nos termos do Decreto nº 8.777/2016
(Política de Dados Abertos do Poder Executivo Federal).

Este aplicativo não substitui a consulta oficial à Anatel nem a orientação
da Agência.

---

## Autor

**Melhym Pereira Quemel** — PY1MEL, Classe A
Mestre em Direito, graduando em Engenharia de Software.
Governança algorítmica, integridade da prova digital e acessibilidade.

Contato: mpquemel@gmail.com
