#!/usr/bin/env python3
"""
atualizar_base.py — Baixa a base da Anatel e reconstroi o SQLite local.

Separa COLETA de CONSULTA: este script cuida da rede e do parsing; o app
consulta so le o SQLite, funciona offline e nunca toca a internet.

Uso:
    python3 scripts/atualizar_base.py             # baixa se necessario e recarrega
    python3 scripts/atualizar_base.py --force     # rebaixa mesmo se hash igual
    python3 scripts/atualizar_base.py --local     # recarrega do zip local, sem rede
    python3 scripts/atualizar_base.py --status    # mostra versao instalada

Saida:
    dados/radioamador.db          banco SQLite com indices
    dados/versao_base.json        metadados da versao instalada
"""

import csv
import hashlib
import io
import json
import os
import sqlite3
import sys
import time
import unicodedata
import urllib.request
import zipfile
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(BASE, "dados")
ZIP = os.path.join(DADOS, "estacoes_licenciadas.zip")
CSV_RADIO = os.path.join(DADOS, "Estacoes_Radioamador.csv")
DB = os.path.join(DADOS, "radioamador.db")
VERSAO = os.path.join(DADOS, "versao_base.json")

URL = ("https://www.anatel.gov.br/dadosabertos/paineis_de_dados/"
       "outorga_e_licenciamento/estacoes_licenciadas.zip")
ARQUIVO_INTERNO = "Estacoes_Radioamador.csv"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

SCHEMA_VERSAO = 1


# ---------------------------------------------------------------------------
def agora():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def sem_acento(txt):
    """Normaliza para busca: minusculo, sem acento, sem pontuacao excessiva."""
    if not txt:
        return ""
    n = unicodedata.normalize("NFKD", txt)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.lower().split())


def so_digitos(txt):
    return "".join(c for c in (txt or "") if c.isdigit())


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# ---------------------------------------------------------------------------
def baixar_zip(force=False):
    """Baixa o zip mestre da Anatel. Devolve True se o arquivo local serve."""
    if os.path.exists(ZIP) and not force:
        idade_h = (time.time() - os.path.getmtime(ZIP)) / 3600
        print(f"  zip local: {os.path.getsize(ZIP)/1e6:.1f} MB, "
              f"{idade_h:.1f}h de idade — reutilizando")
        return True
    print(f"  baixando {URL}")
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    tmp = ZIP + ".part"
    try:
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            total = 0
            while True:
                bloco = r.read(1 << 20)
                if not bloco:
                    break
                f.write(bloco)
                total += len(bloco)
        os.replace(tmp, ZIP)
        print(f"  baixado: {total/1e6:.1f} MB")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FALHA no download: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return os.path.exists(ZIP)


def extrair_csv():
    if not os.path.exists(ZIP):
        print("  zip ausente — nada a extrair")
        return False
    with zipfile.ZipFile(ZIP) as z:
        nomes = z.namelist()
        if ARQUIVO_INTERNO not in nomes:
            print(f"  ATENCAO: {ARQUIVO_INTERNO} nao esta no zip. "
                  f"Arquivos: {nomes}")
            return False
        data = z.read(ARQUIVO_INTERNO)
    with open(CSV_RADIO, "wb") as f:
        f.write(data)
    print(f"  csv extraido: {len(data)/1e6:.1f} MB")
    return True


# ---------------------------------------------------------------------------
def ler_csv():
    with open(CSV_RADIO, encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f, delimiter=";"))


def construir_db(linhas):
    tmp = DB + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);

        CREATE TABLE estacao (
            num_estacao     TEXT PRIMARY KEY,
            indicativo      TEXT,
            nome            TEXT,
            nome_norm       TEXT,
            doc             TEXT,
            doc_digitos     TEXT,
            tipo_doc        TEXT,
            fistel          TEXT,
            servico         TEXT,
            classe          TEXT,
            tipo_estacao    TEXT,
            nome_estacao    TEXT,
            uf_entidade     TEXT,
            municipio       TEXT,
            municipio_norm  TEXT,
            uf_estacao      TEXT,
            dt_primeiro     TEXT,
            dt_ultimo       TEXT,
            dt_validade     TEXT,
            status          TEXT
        );
    """)

    def campo(r, k):
        return (r.get(k) or "").strip()

    registros = []
    for r in linhas:
        registros.append((
            campo(r, "Número da Estação"),
            campo(r, "Indicativo").upper(),
            campo(r, "Nome da Entidade"),
            sem_acento(campo(r, "Nome da Entidade")),
            campo(r, "CNPJ ou CPF"),
            so_digitos(campo(r, "CNPJ ou CPF")),
            campo(r, "Tipo de Identificação"),
            campo(r, "Fistel do Serviço da Estação"),
            campo(r, "Serviço"),
            campo(r, "COER"),
            campo(r, "Tipo de Estação"),
            campo(r, "Nome da Estação"),
            campo(r, "UF da Entidade"),
            campo(r, "Município da Estação"),
            sem_acento(campo(r, "Município da Estação")),
            campo(r, "UF da Estação"),
            campo(r, "Data do Primeiro Licenciamento"),
            campo(r, "Data do Último Licenciamento"),
            campo(r, "Data de Validade da Estação"),
            campo(r, "Status da Validade"),
        ))

    cur.executemany(
        "INSERT OR REPLACE INTO estacao VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", registros)

    cur.executescript("""
        CREATE INDEX idx_indicativo   ON estacao(indicativo);
        CREATE INDEX idx_nome_norm    ON estacao(nome_norm);
        CREATE INDEX idx_doc_digitos  ON estacao(doc_digitos);
        CREATE INDEX idx_fistel       ON estacao(fistel);
        CREATE INDEX idx_municipio    ON estacao(municipio_norm);
        CREATE INDEX idx_uf           ON estacao(uf_entidade);
        CREATE INDEX idx_tipo         ON estacao(tipo_estacao);
        CREATE INDEX idx_classe       ON estacao(classe);
        CREATE INDEX idx_status       ON estacao(status);
    """)

    meta = {
        "schema_versao": str(SCHEMA_VERSAO),
        "total_estacoes": str(len(registros)),
        "construido_em": agora(),
        "fonte": URL,
        "csv_sha256": sha256_arquivo(CSV_RADIO),
    }
    cur.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", meta.items())
    con.commit()

    cur.execute("SELECT COUNT(*) FROM estacao")
    n = cur.fetchone()[0]
    con.close()
    os.replace(tmp, DB)
    print(f"  sqlite construido: {n:,} estacoes, "
          f"{os.path.getsize(DB)/1e6:.1f} MB")
    return meta


def gravar_versao(meta):
    with open(VERSAO, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)


def status():
    if not os.path.exists(VERSAO):
        print("Base nao instalada. Rode: python3 scripts/atualizar_base.py")
        return
    with open(VERSAO, encoding="utf-8") as f:
        m = json.load(f)
    idade_h = (time.time() - os.path.getmtime(DB)) / 3600
    print("Base instalada")
    print(f"  estacoes   : {int(m['total_estacoes']):,}")
    print(f"  construida : {m['construido_em']} ({idade_h:.1f}h atras)")
    print(f"  schema     : v{m['schema_versao']}")
    print(f"  banco      : {DB} ({os.path.getsize(DB)/1e6:.1f} MB)")
    print(f"  csv sha256 : {m['csv_sha256'][:16]}...")


def main():
    args = sys.argv[1:]
    if "--status" in args:
        status()
        return

    os.makedirs(DADOS, exist_ok=True)
    print(f"Atualizador da base de radioamador — {agora()}")

    if "--local" in args:
        print("> modo local (sem rede)")
        if not os.path.exists(CSV_RADIO):
            # patch 05: tentar extrair do zip local antes de desistir
            if os.path.exists(ZIP):
                print("  CSV ausente; extraindo do zip local")
                if not extrair_csv():
                    sys.exit(1)
            else:
                print("  FALHA: nem CSV nem ZIP local disponiveis")
                sys.exit(1)
    else:
        print("> 1/3 download")
        if not baixar_zip(force="--force" in args):
            print("  FALHA: sem zip para trabalhar")
            sys.exit(1)
        print("> 2/3 extracao")
        if not extrair_csv():
            sys.exit(1)

    print("> 3/3 construcao do SQLite")
    linhas = ler_csv()
    print(f"  linhas lidas: {len(linhas):,}")
    meta = construir_db(linhas)
    gravar_versao(meta)
    print("\nPronto. Consulte com: python3 scripts/consultar.py --ajuda")


if __name__ == "__main__":
    main()
