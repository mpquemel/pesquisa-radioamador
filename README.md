# Pesquisa Radioamador — Brasil

Consulta das estações de radioamador licenciadas pela Anatel.
Funciona **sem internet**, **sem instalação** e **sem cadastro**.

São **71.328 estações** de todo o país, com indicativo, classe, tipo de
estação, município, datas de licenciamento e — o mais procurado — o
**Fistel**, o número necessário para emitir o boleto anual.

---

## Como usar

**Baixe o arquivo `pesquisa-radioamador.zip`** na página de
[Releases](../../releases).

**Descompacte em qualquer pasta.**

**Dê dois cliques em `index.html`.** O programa abre no seu navegador.

Pronto. A partir daí tudo funciona offline.

Funciona no Windows, Linux, macOS, Android e iPhone.

Alternativa: se preferir, baixe direto os dois arquivos (`index.html` e
`dados.js`) e mantenha-os na mesma pasta.

---

## O que o programa faz

**Consulta** por indicativo, nome, parte visível do documento, Fistel,
município, estado, tipo de estação, classe e situação da validade.
Os filtros se somam: preencha o que souber, deixe o resto em branco.

**Acha o Fistel** para o boleto anual — o uso mais frequente.

**Exporta os resultados** em CSV, para abrir no Excel ou no LibreOffice.

**Gera relatório resumido** com contagens por tipo, classe e estado.

**Traz o manual de uso** embutido, explicando cada campo.

**Traz a legislação** de referência, incluindo as regras de repetidora.

**Aceita atualização** a partir do arquivo oficial da Anatel, quando você
baixar o pacote novo e indicá-lo no seletor de arquivo.

---

## Acessibilidade

Feito com marcação HTML semântica, para uso com leitor de tela:

- Títulos hierarquizados, navegáveis por atalho de cabeçalho.
- Rótulos reais em todos os campos.
- Resultados anunciados automaticamente pelo leitor de tela.
- Após a busca, o foco vai para o título dos resultados.
- Nenhuma ação exige mouse.
- Contraste acima de 4,5:1 e suporte a zoom de 200%.

Testado com NVDA.

---

## Limitações — leia antes de compartilhar

**O CPF não é pesquisável por inteiro.** A Anatel publica o documento
mascarado, mostrando apenas cinco dígitos (ex.: `***65935**`). É possível
buscar por esses cinco dígitos. O número completo não existe nesta base.

**"N/I" não significa irregular.** Em 25,7% das estações a Anatel não
registra data de validade. Apenas 362 aparecem explicitamente como vencidas.

**Estação móvel não tem município.** Os 38.552 móveis vêm com município e
estado como "N/A". Use o filtro de estado do titular.

**A atualização não é automática.** Por restrição de segurança dos
navegadores, um arquivo aberto localmente não pode baixar e regravar dados
sozinho. O botão na seção "Atualizar base" abre o site da Anatel; você baixa
o pacote e o indica no seletor de arquivo.

---

## Origem dos dados

Anatel — Agência Nacional de Telecomunicações, dados abertos.
Base de Estações Licenciadas, arquivo `Estacoes_Radioamador.csv`.

Dados públicos do governo federal, reutilizáveis com atribuição, nos termos
do Decreto nº 8.777/2016.

Este programa é uma ferramenta de consulta e não substitui a consulta
oficial à Anatel nem a orientação da Agência.

---

## Autor

**Melhym Pereira Quemel** — PY1MEL, Classe A
Mestre em Direito, graduando em Engenharia de Software.
Governança algorítmica, integridade da prova digital e acessibilidade.

Contato: mpquemel@gmail.com

Comentários, sugestões e relatos de uso são bem-vindos na aba
[Issues](../../issues).
