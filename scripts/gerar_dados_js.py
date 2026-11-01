#!/usr/bin/env python3
"""
gerar_dados_js.py — Converte o CSV da Anatel em dados.js para o app web.

FORMATO ESCOLHIDO (decidido por medicao, ver relatorios/arquitetura-web.md):
  array de arrays + dicionarios. 24,46 MB em objetos -> 10,58 MB assim.
  Carrega por <script src="dados.js">, porque fetch() em file:// e bloqueado
  por CORS no Chrome, Edge e Firefox.

ESTRUTURA DE window.DADOS:
  meta:  { gerado_em, fonte_url, csv_sha256, total, schema }
  ufs:   ["AC", "AL", ...]              indice -> sigla
  tipos: ["Fixa", "Móvel", ...]
  classes: ["Classe A", ...]
  status: ["Ativa", "Vencida", "N/I", ""]
  mun:   ["Rio Branco\u001fAC", ...]     municipio + unidade (separador \u001f)
  reg:   [[...], ...]                   os registros

ORDEM DOS CAMPOS EM reg[i]:
  0 indicativo   1 nome        2 doc (mascarado)  3 tipo_doc
  4 fistel       5 tipo_i      6 classe_i         7 mun_i
  8 uf_i         9 dt_primeiro 10 dt_ultimo      11 dt_validade
  12 status_i   13 num_estacao

Uso:
    python3 scripts/gerar_dados_js.py            # gera web/dados.js
    python3 scripts/gerar_dados_js.py --check    # so confere o existente
"""

import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(BASE, "dados", "Estacoes_Radioamador.csv")
WEB = os.path.join(BASE, "web")
SAIDA = os.path.join(WEB, "dados.js")

FONTE = ("https://www.anatel.gov.br/dadosabertos/paineis_de_dados/"
         "outorga_e_licenciamento/estacoes_licenciadas.zip")

SEP = "\x1f"  # separador interno do dicionario de municipios


def agora():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def sh256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def c(r, k):
    return (r.get(k) or "").strip()


UFS_VALIDAS = {
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB",
    "PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO",
}

NOMES_UF = {
    "ACRE":"AC","ALAGOAS":"AL","AMAPA":"AP","AMAZONAS":"AM","BAHIA":"BA",
    "CEARA":"CE","DISTRITO FEDERAL":"DF","ESPIRITO SANTO":"ES","GOIAS":"GO",
    "MARANHAO":"MA","MATO GROSSO":"MT","MATO GROSSO DO SUL":"MS",
    "MINAS GERAIS":"MG","PARA":"PA","PARAIBA":"PB","PARANA":"PR",
    "PERNAMBUCO":"PE","PIAUI":"PI","RIO DE JANEIRO":"RJ",
    "RIO GRANDE DO NORTE":"RN","RIO GRANDE DO SUL":"RS","RONDONIA":"RO",
    "RORAIMA":"RR","SANTA CATARINA":"SC","SAO PAULO":"SP","SERGIPE":"SE",
    "TOCANTINS":"TO",
}


def normalizar_uf(valor):
    """A Anatel publica UF suja em poucas linhas: 'Pr', 'mg', 'rj',
    'BAHIA'. Devolve a sigla de duas letras, ou "" se nao for UF reconhecivel.
    Nao inventa: 'N/A' e 'N/I' continuam fora do dicionario de UF."""
    v = (valor or "").strip()
    if not v:
        return ""
    vu = v.upper()
    if vu in UFS_VALIDAS:
        return vu
    plano = unicodedata.normalize("NFKD", vu)
    plano = "".join(ch for ch in plano if not unicodedata.combining(ch))
    if plano in NOMES_UF:
        return NOMES_UF[plano]
    return ""


def checar_gerado(argv):
    """--check: compara o dados.js existente com o que o CSV produziria.
    Nao grava nada. Sai com codigo 1 se houver divergencia."""
    if not os.path.exists(SAIDA):
        print(f"FALHA: {os.path.basename(SAIDA)} nao existe em {WEB}")
        return 1
    if not os.path.exists(CSV):
        print(f"FALHA: CSV ausente: {CSV}")
        return 1

    with open(SAIDA, encoding="utf-8") as f:
        atual = f.read()

    # O dados.js NAO e JSON puro: e um arquivo JS com comentario de cabecalho,
    # a atribuicao "window.DADOS = {...};" e chaves SEM aspas nos dicionarios.
    # Por isso nao se usa json.loads: avaliamos com node, que entende o arquivo
    # exatamente como o navegador entende.
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as tmp:
        # o dados.js faz "window.DADOS = {...}" e roda no navegador;
        # no node precisamos simular o objeto window antes de carregar.
        tmp.write("globalThis.window = globalThis;\n")
        tmp.write(atual)
        tmp.write("\nmodule.exports = globalThis.DADOS;\n")
        caminho_tmp = tmp.name
    try:
        r = subprocess.run(
            ["node", "-e",
             'const d=require(process.argv[1]);'
             'console.log(JSON.stringify({meta:d.meta,'
             'mun:d.mun,ufs:d.ufs,total:(d.reg||[]).length}));',
             caminho_tmp],
            capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(caminho_tmp)
    if r.returncode != 0:
        print("FALHA: nao consegui avaliar o dados.js com node:")
        print(r.stderr.strip()[:400])
        return 1
    dados = json.loads(r.stdout)
    dados["total_real"] = dados.get("total")

    meta_atual = dados.get("meta", {})
    total_atual = meta_atual.get("total")
    sha_atual = meta_atual.get("csv_sha256")
    sha_csv = sh256(CSV)

    print(f"dados.js : {len(atual):,} bytes, {total_atual:,} registros" if total_atual
          else f"dados.js : {len(atual):,} bytes")
    print(f"CSV      : {os.path.getsize(CSV):,} bytes")
    print(f"CSV sha256 atual : {sha_csv}")
    print(f"CSV sha256 gravado no dados.js : {sha_atual}")

    falhas = 0
    if sha_atual == sha_csv:
        print("OK   hash do CSV confere com o registrado no dados.js")
    else:
        print("DIVERGE  o CSV mudou desde a ultima geracao (dados.js desatualizado)")
        falhas += 1

    # conta as linhas do CSV e compara com o total gravado
    with open(CSV, encoding="utf-8-sig", errors="replace", newline="") as f:
        linhas = sum(1 for _ in csv.DictReader(f, delimiter=";"))
    print(f"linhas no CSV agora: {linhas:,}")
    print(f"registros no array reg: {dados.get('total_real',0):,}")
    if dados.get("total_real") == linhas:
        print("OK   total de registros confere")
    else:
        print(f"DIVERGE  dados.js tem {dados.get('total_real',0):,} registros, o CSV tem {linhas:,}")
        falhas += 1

    # checagem de coerencia interna: cada indice de municipio referencia UF valida
    mun = dados.get("mun") or []
    ufs = dados.get("ufs") or []
    if mun and ufs:
        ruins = sum(1 for e in mun if e and SEP in e and e.rsplit(SEP, 1)[1] not in ufs)
        if ruins:
            print(f"DIVERGE  {ruins} entradas de municipio com UF inexistente")
            falhas += 1
        else:
            print("OK   todos os municipios apontam para UF existente")

    if falhas:
        print(f"\nRESULTADO: {falhas} divergencia(s). Rode sem --check para regenerar.")
        return 1
    print("\nRESULTADO: dados.js consistente com o CSV. Nada a fazer.")
    return 0


def main(argv):
    if "--check" in argv:
        return checar_gerado(argv)
    if not os.path.exists(CSV):
        sys.exit(f"CSV ausente: {CSV}\nRode antes: python3 scripts/atualizar_base.py")

    os.makedirs(WEB, exist_ok=True)
    print(f"Lendo {os.path.basename(CSV)}")
    with open(CSV, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    print(f"  {len(rows):,} linhas")

    ufs, tipos, classes, status = [], [], [], []
    municipios = []
    idx_uf, idx_tipo, idx_classe, idx_status, idx_mun = {}, {}, {}, {}, {}

    def add(dic, lst, valor):
        if valor not in dic:
            dic[valor] = len(lst)
            lst.append(valor)
        return dic[valor]

    registros = []
    for r in rows:
        uf = c(r, "UF da Entidade")
        # CORRECAO 2026-11-01: o municipio e o da ESTACAO, logo a UF que o
        # qualifica tambem e a da ESTACAO. Usar "UF da Entidade" aqui pareava
        # "Sao Paulo" com "MG" quando o titular mora em outro estado.
        uf_estacao = normalizar_uf(c(r, "UF da Estação")) or uf
        mun = c(r, "Município da Estação")
        if mun in ("N/A", "N/I", ""):
            chave_mun = ""
        else:
            chave_mun = mun + SEP + uf_estacao
        registros.append([
            c(r, "Indicativo").upper(),
            c(r, "Nome da Entidade"),
            c(r, "CNPJ ou CPF"),
            c(r, "Tipo de Identificação"),
            c(r, "Fistel do Serviço da Estação"),
            add(idx_tipo, tipos, c(r, "Tipo de Estação")),
            add(idx_classe, classes, c(r, "COER")),
            add(idx_mun, municipios, chave_mun),
            add(idx_uf, ufs, uf),
            c(r, "Data do Primeiro Licenciamento"),
            c(r, "Data do Último Licenciamento"),
            c(r, "Data de Validade da Estação"),
            add(idx_status, status, c(r, "Status da Validade")),
            c(r, "Número da Estação"),
        ])

    meta = {
        "gerado_em": agora(),
        "fonte_url": FONTE,
        "fonte_arquivo": "Estacoes_Radioamador.csv (dentro de estacoes_licenciadas.zip)",
        "fonte_orgao": "Anatel - Agencia Nacional de Telecomunicacoes",
        "csv_sha256": sh256(CSV),
        "total": len(registros),
        "schema": 1,
        "campos": ["indicativo", "nome", "doc", "tipo_doc", "fistel",
                   "tipo", "classe", "municipio", "uf", "dt_primeiro",
                   "dt_ultimo", "dt_validade", "status", "num_estacao"],
    }

    print(f"  {len(ufs)} UFs, {len(municipios):,} municipios, "
          f"{len(tipos)} tipos, {len(classes)} classes")

    partes = [
        "/* ------------------------------------------------------------------",
        "   BASE DE ESTACOES DE RADIOAMADOR - DADOS ABERTOS DA ANATEL",
        "",
        "   Arquivo gerado automaticamente por scripts/gerar_dados_js.py.",
        "   NAO EDITE A MAO: a proxima geracao sobrescreve.",
        "",
        f"   Gerado em   : {meta['gerado_em']}",
        f"   Registros   : {meta['total']:,}",
        f"   Fonte       : {FONTE}",
        f"   SHA-256 CSV : {meta['csv_sha256']}",
        "",
        "   Dados publicos do governo federal (Decreto 8.777/2016).",
        "   Mantenedor: Melhym Pereira Quemel - PY1MEL - mpquemel@gmail.com",
        "   ------------------------------------------------------------------ */",
        "",
        "window.DADOS = {",
        f"meta: {json.dumps(meta, ensure_ascii=False)},",
        f"ufs: {json.dumps(ufs, ensure_ascii=False)},",
        f"tipos: {json.dumps(tipos, ensure_ascii=False)},",
        f"classes: {json.dumps(classes, ensure_ascii=False)},",
        f"status: {json.dumps(status, ensure_ascii=False)},",
        f"mun: {json.dumps(municipios, ensure_ascii=False)},",
        "reg: [",
    ]
    for i, reg in enumerate(registros):
        partes.append(json.dumps(reg, ensure_ascii=False, separators=(",", ":"))
                      + ("," if i < len(registros) - 1 else ""))
    partes.append("]")
    partes.append("};")
    partes.append("")

    conteudo = "\n".join(partes)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(conteudo)

    tamanho = os.path.getsize(SAIDA) / 1e6
    print(f"\nGerado: {SAIDA}")
    print(f"  tamanho: {tamanho:.2f} MB")
    print(f"  meta.total: {meta['total']:,}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
