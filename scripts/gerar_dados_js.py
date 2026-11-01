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


def main():
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
        mun = c(r, "Município da Estação")
        if mun in ("N/A", "N/I", ""):
            chave_mun = ""
        else:
            chave_mun = mun + SEP + uf
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
    main()
