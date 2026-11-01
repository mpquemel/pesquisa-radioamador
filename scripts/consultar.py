#!/usr/bin/env python3
"""
consultar.py — Consulta offline da base de radioamador (Anatel).

DESENHO DE ACESSIBILIDADE
=========================
Este app foi escrito para uso com leitor de tela NVDA, por pessoa cega total.
Decisoes que valem para todo o arquivo:

1. SAIDA LINEAR E SEMANTICA. Nada de tabelas desenhadas com tracos, colunas
   alinhadas por espaco ou arte ASCII: o NVDA le esses layouts como lixo
   sonoro. Cada registro sai como bloco de rotulo: valor, uma informacao por
   linha, na mesma ordem sempre.

2. HIERARQUIA DE CABECALHOS. Blocos longos comecam por um titulo em linha
   propria (ex.: "RESULTADO 1 DE 2"). Isso permite pular de resultado em
   resultado com as teclas de navegacao rapida do NVDA.

3. NADA DEPENDE DE MOUSE OU DE POSICAO NA TELA. Tudo por argumento de linha
   de comando ou pelo modo interativo por teclado.

4. SILENCIO UTIL. Quando nao ha resultado, o app diz o que buscou e como
   ajustar — nunca devolve pagina em branco sem explicacao.

5. COPIA FACIL. Todo resultado traz o Fistel em linha propria, isolado, para
   ser copiado com selecao de linha do terminal (Shift+setas no NVDA).

Uso rapido:
    python3 scripts/consultar.py --ajuda
    python3 scripts/consultar.py -i PY1MEL
    python3 scripts/consultar.py --fistel 01000257142
    python3 scripts/consultar.py --nome "melhym quemel"
    python3 scripts/consultar.py --cpf 12345678901
    python3 scripts/consultar.py --municipio saquarema -u RJ
    python3 scripts/consultar.py -i            # modo interativo
    python3 scripts/consultar.py -i --exportar csv
"""

import argparse
import csv
import os
import sqlite3
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "dados", "radioamador.db")

LIMITE_PADRAO = 25


# ---------------------------------------------------------------------------
# Normalizacao (espelha a usada na carga, para busca tolerante)
# ---------------------------------------------------------------------------
def sem_acento(txt):
    if not txt:
        return ""
    n = unicodedata.normalize("NFKD", txt)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.lower().split())


def so_digitos(txt):
    return "".join(c for c in (txt or "") if c.isdigit())


def _chave(txt):
    """Minusculo, sem acento, sem espaco — para comparar vocabulario fechado."""
    return sem_acento(txt).replace(" ", "").replace("-", "")


def normalizar_classe(valor):
    """Aceita 'a', 'A', 'classe a', 'Classe A'. Devolve 'Classe X' ou None."""
    k = _chave(valor).replace("classe", "")
    if k in ("a", "b", "c"):
        return f"Classe {k.upper()}"
    if k in ("na",):
        return "N/A"
    return None


def normalizar_tipo(valor):
    """Aceita movel/móvel/móvel, fixa, repetidora, terrena."""
    mapa = {"fixa": "Fixa", "movel": "Móvel", "repetidora": "Repetidora",
            "terrena": "Terrena", "espacial": "Espacial"}
    return mapa.get(_chave(valor))


def normalizar_status(valor):
    """Aceita ativa/ATIVA, vencida, n/i, ni."""
    mapa = {"ativa": "Ativa", "vencida": "Vencida",
            "ni": "N/I", "naoinformado": "N/I", "na": "N/A"}
    return mapa.get(_chave(valor))


# ---------------------------------------------------------------------------
# Conexao
# ---------------------------------------------------------------------------
def conectar():
    if not os.path.exists(DB):
        sys.exit(
            "Base nao encontrada em dados/radioamador.db.\n"
            "Rode primeiro: python3 scripts/atualizar_base.py"
        )
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def versao_da_base(con):
    try:
        m = dict(con.execute("SELECT chave, valor FROM meta").fetchall())
        return (f"Base: {int(m.get('total_estacoes', 0)):,} estacoes, "
                f"construida em {m.get('construido_em', '?')}, "
                f"schema v{m.get('schema_versao', '?')}")
    except sqlite3.Error:
        return "Base: metadados indisponiveis"


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------
def montar_consulta(args):
    """Devolve (sql, parametros, descricao_humana)."""
    onde, params, desc = [], [], []

    if args.indicativo:
        ind = sem_acento(args.indicativo).upper().replace(" ", "")
        onde.append("indicativo = ?")
        params.append(ind)
        desc.append(f"indicativo {ind}")

    if args.nome:
        partes = sem_acento(args.nome).split()
        for p in partes:
            onde.append("nome_norm LIKE ?")
            params.append(f"%{p}%")
        desc.append(f"nome contendo '{args.nome}'")

    if args.cpf:
        d = so_digitos(args.cpf)
        onde.append("doc_digitos = ?")
        params.append(d)
        desc.append(f"documento {d}")

    if args.fistel:
        f = so_digitos(args.fistel)
        onde.append("fistel = ?")
        params.append(f)
        desc.append(f"fistel {f}")

    if args.municipio:
        onde.append("municipio_norm LIKE ?")
        params.append(f"%{sem_acento(args.municipio)}%")
        desc.append(f"municipio '{args.municipio}'")

    if args.uf:
        onde.append("uf_entidade = ?")
        params.append(args.uf.upper())
        desc.append(f"UF {args.uf.upper()}")

    if args.classe:
        cl = normalizar_classe(args.classe)
        if cl is None:
            return "__ERRO__", (f"Classe invalida: '{args.classe}'. "
                                f"Use A, B ou C."), ""
        onde.append("classe = ?")
        params.append(cl)
        desc.append(f"classe {cl}")

    if args.tipo:
        t = normalizar_tipo(args.tipo)
        if t is None:
            return "__ERRO__", (f"Tipo invalido: '{args.tipo}'. "
                                f"Use Fixa, Movel, Repetidora ou Terrena."), ""
        onde.append("tipo_estacao = ?")
        params.append(t)
        desc.append(f"tipo {t}")

    if args.status:
        st = normalizar_status(args.status)
        if st is None:
            return "__ERRO__", (f"Status invalido: '{args.status}'. "
                                f"Use Ativa, Vencida ou N/I."), ""
        onde.append("status = ?")
        params.append(st)
        desc.append(f"status {st}")

    if not onde:
        return None, None, "nenhum filtro informado"

    sql = ("SELECT * FROM estacao WHERE " + " AND ".join(onde) +
           " ORDER BY nome, num_estacao")
    return sql, params, " e ".join(desc)


CAMPOS_EXPORT = [
    ("Indicativo", "indicativo"), ("Nome", "nome"), ("Documento", "doc"),
    ("Tipo de pessoa", "tipo_doc"), ("Fistel", "fistel"),
    ("Tipo de estacao", "tipo_estacao"), ("Classe", "classe"),
    ("Municipio", "municipio"), ("UF", "uf_entidade"),
    ("1o licenciamento", "dt_primeiro"), ("Ultimo licenciamento", "dt_ultimo"),
    ("Validade", "dt_validade"), ("Status", "status"),
    ("Numero da estacao", "num_estacao"),
]


def imprimir_bloco(r, indice, total):
    """Um registro em texto linear: rotulo e valor, sem colunas."""
    print(f"\n=== RESULTADO {indice} DE {total} ===")
    for rotulo, chave in CAMPOS_EXPORT:
        valor = (r[chave] or "").strip() or "nao informado"
        if chave == "fistel":
            print(f"{rotulo}:")
            print(valor)
        else:
            print(f"{rotulo}: {valor}")


def exportar(linhas, destino):
    ext = destino.rsplit(".", 1)[-1].lower() if "." in destino else "csv"
    if ext == "csv":
        with open(destino, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([c[0] for c in CAMPOS_EXPORT])
            for r in linhas:
                w.writerow([r[c[1]] for c in CAMPOS_EXPORT])
    elif ext == "txt":
        with open(destino, "w", encoding="utf-8") as f:
            for i, r in enumerate(linhas, 1):
                f.write(f"=== RESULTADO {i} DE {len(linhas)} ===\n")
                for rotulo, chave in CAMPOS_EXPORT:
                    if chave == "fistel":
                        f.write(f"{rotulo}:\n{r[chave]}\n")
                    else:
                        f.write(f"{rotulo}: {(r[chave] or '').strip() or 'nao informado'}\n")
                f.write("\n")
    else:
        print(f"Formato '{ext}' nao suportado. Use csv ou txt.")
        return
    print(f"\nExportado: {destino} ({len(linhas)} registros)")


def executar(args):
    con = conectar()
    sql, params, desc = montar_consulta(args)
    print(versao_da_base(con))

    if sql == "__ERRO__":
        # params carrega a mensagem de erro neste caso
        print(f"\n{params}")
        con.close()
        return 2
    if sql is None:
        print("\nNenhum filtro informado. Use --ajuda para ver as opcoes.")
        con.close()
        return 2

    print(f"Busca: {desc}")
    linhas = con.execute(sql, params).fetchall()
    con.close()

    if not linhas:
        print("\nNenhum resultado encontrado.")
        print("Sugestoes: confira a grafia, tente so o primeiro nome,")
        print("ou busque pelo indicativo ou pelo Fistel.")
        return 1

    limite = args.limite
    if limite is None or limite <= 0:
        print(f"\nAVISO: --limite {limite} invalido; usando {LIMITE_PADRAO}.")
        limite = LIMITE_PADRAO
        args.limite = limite

    mostradas = linhas[:limite]
    print(f"\n{len(linhas)} resultado(s) encontrado(s).")
    if len(linhas) > limite:
        print(f"Exibindo os primeiros {limite}. "
              f"Use --limite N para ver mais, ou --exportar arquivo.csv.")

    if args.resumo:
        print("\n=== RESUMO ===")
        print(f"Total de estacoes: {len(linhas)}")
        print(f"Pessoas distintas: "
              f"{len({r['doc_digitos'] for r in linhas})}")
        tipos = {}
        for r in linhas:
            tipos[r["tipo_estacao"] or "nao informado"] = (
                tipos.get(r["tipo_estacao"] or "nao informado", 0) + 1)
        for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
            print(f"{t}: {n}")
        return 0

    for i, r in enumerate(mostradas, 1):
        imprimir_bloco(r, i, len(mostradas))

    if args.exportar:
        exportar(linhas, args.exportar)
    return 0


# ---------------------------------------------------------------------------
# Modo interativo (por teclado, sem mouse)
# ---------------------------------------------------------------------------
MENU = """
MODO INTERATIVO — digite o numero da opcao e Enter.
  1  Buscar por indicativo
  2  Buscar por nome
  3  Buscar por CPF ou CNPJ
  4  Buscar por Fistel (para o boleto)
  5  Buscar por municipio
  6  Listar estacoes de uma UF
  7  Resumo de uma UF
  0  Sair
"""


def interativo(args):
    con = conectar()
    print(versao_da_base(con))
    con.close()
    while True:
        print(MENU)
        try:
            op = input("Opcao: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaindo.")
            return 0
        if op == "0":
            print("Saindo.")
            return 0
        mapa = {"1": "indicativo", "2": "nome", "3": "cpf",
                "4": "fistel", "5": "municipio", "6": "uf", "7": "resumo_uf"}
        if op not in mapa:
            print("Opcao invalida.")
            continue
        try:
            valor = input("Termo: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaindo.")
            return 0
        if not valor:
            print("Termo vazio.")
            continue
        sub = argparse.Namespace(**vars(args))
        for k in ("indicativo", "nome", "cpf", "fistel", "municipio", "uf"):
            setattr(sub, k, None)
        sub.resumo = False
        if op == "6":
            sub.uf = valor
        elif op == "7":
            sub.uf = valor
            sub.resumo = True
        else:
            setattr(sub, mapa[op], valor)
        executar(sub)


def resumo_uf(args):
    con = conectar()
    print(versao_da_base(con))
    uf = args.uf.upper()
    linhas = con.execute(
        "SELECT * FROM estacao WHERE uf_entidade = ? ORDER BY nome", (uf,)
    ).fetchall()
    con.close()
    if not linhas:
        print(f"\nNenhuma estacao na UF {uf}.")
        return 1
    from collections import Counter
    print(f"\n=== RESUMO DA UF {uf} ===")
    print(f"Estacoes: {len(linhas)}")
    print(f"Pessoas distintas: {len({r['doc_digitos'] for r in linhas})}")
    print("\nPor tipo de estacao:")
    for t, n in Counter(r["tipo_estacao"] or "nao informado"
                        for r in linhas).most_common():
        print(f"  {t}: {n}")
    print("\nPor classe:")
    for c, n in Counter(r["classe"] or "nao informado"
                        for r in linhas).most_common():
        print(f"  {c}: {n}")
    print("\nMunicipios com mais estacoes:")
    for m, n in Counter(r["municipio"] or "nao informado"
                        for r in linhas if (r["municipio"] or "") not in
                        ("N/A", "N/I", "")).most_common(10):
        print(f"  {m}: {n}")
    return 0


# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        prog="consultar.py",
        description="Consulta offline de estacoes de radioamador (Anatel). "
                    "Saida em texto linear, otimizada para leitor de tela NVDA.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""exemplos:
  consultar.py -i PY1MEL
  consultar.py --fistel 01000257142
  consultar.py --nome "melhym" -u RJ
  consultar.py --municipio saquarema
  consultar.py -i --exportar meus_dados.csv
  consultar.py --resumo-uf RJ

acessibilidade:
  - Toda saida e texto linear, rotulo: valor, sem tabelas ou arte ASCII.
  - Cada resultado comeca com "=== RESULTADO N DE M ===".
  - O Fistel sai em linha propria e isolada, para copiar com selecao de linha.
  - Use --exportar para gerar arquivo e ler no editor de sua preferencia.
""")
    p.add_argument("-i", "--indicativo", nargs="?", const="__INTERATIVO__",
                   help="indicativo (ex.: PY1MEL). Sem valor, abre modo interativo")
    p.add_argument("--nome", help="nome ou parte do nome do titular")
    p.add_argument("--cpf", help="parte visivel do CPF/CNPJ mascarado pela Anatel (a base traz apenas 5 digitos, ex.: 65935). CPF completo NAO e pesquisavel")
    p.add_argument("--fistel", help="numero do Fistel (para emitir boleto)")
    p.add_argument("--municipio", help="municipio da estacao")
    p.add_argument("-u", "--uf", help="UF do titular (ex.: RJ)")
    p.add_argument("--classe", help="A, B ou C")
    p.add_argument("--tipo", help="Fixa, Movel, Repetidora, Terrena")
    p.add_argument("--status", help="Ativa, Vencida ou N/I")
    p.add_argument("--limite", type=int, default=LIMITE_PADRAO,
                   help=f"maximo de resultados exibidos (padrao {LIMITE_PADRAO})")
    p.add_argument("--resumo", action="store_true",
                   help="mostra apenas contagens, sem listar registros")
    p.add_argument("--resumo-uf", dest="resumo_uf_flag", metavar="UF",
                   help="resumo completo de uma UF")
    p.add_argument("--exportar", metavar="ARQUIVO",
                   help="grava resultados em .csv ou .txt")
    p.add_argument("--ajuda", action="store_true", help="mostra esta ajuda")

    args = p.parse_args()
    if args.ajuda:
        p.print_help()
        return 0
    tem_filtro = any([args.nome, args.cpf, args.fistel, args.municipio,
                      args.uf, args.classe, args.tipo, args.status,
                      args.resumo_uf_flag])
    if args.indicativo == "__INTERATIVO__":
        return interativo(args)
    if not tem_filtro and not args.indicativo:
        return interativo(args)
    if args.resumo_uf_flag:
        return resumo_uf(argparse.Namespace(uf=args.resumo_uf_flag))
    return executar(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
