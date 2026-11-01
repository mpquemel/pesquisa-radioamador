#!/usr/bin/env python3
"""Radioamador e Radio do Cidadao - base Anatel por estado.

Fonte unica: prestadoras_servicos_telecomunicacoes.zip (Anatel, dados abertos).
Servicos: 302 (Radioamador), 400 (Radio do Cidadao), 401 (RC - Dispensa).

Saida:
  dados/radioamador_brasil.csv    todos os 302 do Brasil
  dados/radio_cidadao_brasil.csv  400 + 401
  dados/radioamador_por_uf.csv     contagem por UF
  dados/planilha_radioamador.xlsx abas: Brasil, por UF, metadados
"""
import csv, io, zipfile, collections, datetime, unicodedata, shutil, sys
from pathlib import Path
import xlsxwriter

BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "dados"
ORIGEM = BASE.parent / "provedores-acre" / "dados" / "prestadoras.zip"
ZIP = DADOS / "prestadoras.zip"
CSVNAME = "prestadoras_servicos_telecomunicacoes.csv"

# valores de "nao informado" que aparecem na base (inclui o traco)
VAZIOS = {"", "-", "--", "N/I", "NI", "n/i", "Nao informado", "Não informado", "n/a"}

SERVICOS = {
    "302": "Radioamador",
    "400": "Rádio do Cidadão",
    "401": "Rádio do Cidadão - Dispensa de Autorização",
}


def limpa(v):
    v = (v or "").strip()
    return "" if v in VAZIOS or set(v) <= {"-"} else v


def converte_data(s):
    try:
        return datetime.datetime.strptime((s or "").strip(), "%d/%m/%Y").date()
    except Exception:
        return None


def main():
    if not ZIP.exists() and ORIGEM.exists():
        shutil.copy(ORIGEM, ZIP)
        print(f"base copiada de {ORIGEM}")
    raw = zipfile.ZipFile(ZIP).read(CSVNAME).decode("utf-8-sig")
    leitor = csv.DictReader(io.StringIO(raw), delimiter=";")
    linhas = list(leitor)
    print(f"linhas nacionais: {len(linhas)}")

    HOJE = datetime.date(2026, 10, 31)
    registros = {"302": [], "400": [], "401": []}

    for r in linhas:
        cod = (r["Código e Nome do Serviço da Notificação"] or "").strip()[:3]
        if cod not in registros:
            continue
        dt = converte_data(r["Data Inclusão da Notificação"])
        registros[cod].append({
            "servico": cod,
            "nome": (r["Nome Entidade Prestadora de Serviço"] or "").strip(),
            "documento": (r["CNPJ ou CPF"] or "").strip(),
            "tipo_doc": (r["Tipo de Identificação"] or "").strip(),
            "tipo_entidade": (r["Tipo de Entidade"] or "").strip(),
            "uf": (r["UF do Endereço Sede"] or "").strip(),
            "municipio": (r["Nome do Munícipio do Endereço Sede"] or "").strip(),
            "ibge": (r["Código IBGE do Munícipio do Endereço Sede"] or "").strip(),
            "logradouro": limpa(r["Logradouro do Endereço Sede"]),
            "numero": limpa(r["Número do Endereço Sede"]),
            "bairro": limpa(r["Bairro do Endereço Sede"]),
            "cep": limpa(r["CEP do Endereço Sede"]),
            "telefone": limpa(r["Telefone Principal"]),
            "email": limpa(r["Endereço Eletrônico"]),
            "fantasia": limpa(r["Nome Fantasia"]),
            "data_notificacao": (r["Data Inclusão da Notificação"] or "").strip(),
            "idade_anos": round((HOJE - dt).days / 365.25, 1) if dt else None,
            "fistel_notificacao": (r["Fistel da Notificação"] or "").strip(),
            "processo_sei": (r["Processo SEI da Outorga"] or "").strip(),
        })

    # dedup por (documento, fistel)
    for cod in registros:
        vistos = {}
        for reg in registros[cod]:
            chave = (reg["documento"], reg["fistel_notificacao"])
            vistos.setdefault(chave, reg)
        registros[cod] = list(vistos.values())
        print(f"  servico {cod} ({SERVICOS[cod]}): {len(registros[cod])} registros unicos")

    campos = ["servico", "nome", "documento", "tipo_doc", "tipo_entidade", "uf", "municipio",
              "ibge", "logradouro", "numero", "bairro", "cep", "telefone", "email", "fantasia",
              "data_notificacao", "idade_anos", "fistel_notificacao", "processo_sei"]

    def grava(nome, regs):
        regs = sorted(regs, key=lambda x: (x["uf"], x["municipio"], x["nome"]))
        with open(DADOS / nome, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
            w.writeheader()
            w.writerows(regs)
        print(f"  gravado {nome}: {len(regs)}")

    grava("radioamador_brasil.csv", registros["302"])
    grava("radio_cidadao_brasil.csv", registros["400"] + registros["401"])

    # contagem por UF
    ufs = sorted({r["uf"] for r in registros["302"] + registros["400"] + registros["401"] if r["uf"]})
    c302 = collections.Counter(r["uf"] for r in registros["302"])
    c400 = collections.Counter(r["uf"] for r in registros["400"])
    c401 = collections.Counter(r["uf"] for r in registros["401"])
    tot = collections.Counter(r["uf"] for r in registros["302"])
    tot.update(r["uf"] for r in registros["400"] if False)

    with open(DADOS / "radioamador_por_uf.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["uf", "radioamador_302", "radio_cidadao_400", "radio_cidadao_dispensa_401", "total"])
        for uf in ufs:
            w.writerow([uf, c302.get(uf, 0), c400.get(uf, 0), c401.get(uf, 0),
                        c302.get(uf, 0) + c400.get(uf, 0) + c401.get(uf, 0)])

    # ---------- planilha
    wb = xlsxwriter.Workbook(DADOS / "planilha_radioamador.xlsx")
    ft = wb.add_format({"bold": True, "bg_color": "#1F3864", "font_color": "white",
                        "border": 1, "text_wrap": True, "valign": "vcenter"})
    fc = wb.add_format({"border": 1, "valign": "top", "text_wrap": True})

    def aba(nome, regs, cols):
        ws = wb.add_worksheet(nome[:31])
        for i, (titulo, largura, chave) in enumerate(cols):
            ws.set_column(i, i, largura)
            ws.write(0, i, titulo, ft)
        for r_linha, reg in enumerate(regs, 1):
            for i, (_, _, chave) in enumerate(cols):
                v = reg.get(chave, "")
                ws.write(r_linha, i, "" if v is None else v, fc)
        ws.freeze_panes(1, 0)
        if regs:
            ws.autofilter(0, 0, len(regs), len(cols) - 1)
        return ws

    cols_radio = [
        ("UF", 6, "uf"), ("Municipio", 22, "municipio"), ("Nome", 42, "nome"),
        ("Documento", 20, "documento"), ("Tipo", 6, "tipo_doc"),
        ("Telefone", 16, "telefone"), ("E-mail", 30, "email"),
        ("Logradouro", 34, "logradouro"), ("Nº", 8, "numero"), ("Bairro", 20, "bairro"),
        ("CEP", 10, "cep"), ("Notificacao", 12, "data_notificacao"),
        ("Idade (anos)", 12, "idade_anos"), ("Fistel", 15, "fistel_notificacao"),
        ("Processo SEI", 22, "processo_sei"),
    ]

    # aba resumo
    ws0 = wb.add_worksheet("Resumo")
    ws0.set_column(0, 5, 24)
    ws0.write(0, 0, "Servico", ft)
    ws0.write(0, 1, "Registros (Brasil)", ft)
    ws0.write(1, 0, "Radioamador (302)", fc)
    ws0.write(1, 1, len(registros["302"]), fc)
    ws0.write(2, 0, "Radio do Cidadao (400)", fc)
    ws0.write(2, 1, len(registros["400"]), fc)
    ws0.write(3, 0, "RC - Dispensa (401)", fc)
    ws0.write(3, 1, len(registros["401"]), fc)
    ws0.write(5, 0, "UF", ft)
    ws0.write(5, 1, "302", ft)
    ws0.write(5, 2, "400", ft)
    ws0.write(5, 3, "401", ft)
    ws0.write(5, 4, "Total", ft)
    for i, uf in enumerate(ufs, 6):
        ws0.write(i, 0, uf, fc)
        ws0.write(i, 1, c302.get(uf, 0), fc)
        ws0.write(i, 2, c400.get(uf, 0), fc)
        ws0.write(i, 3, c401.get(uf, 0), fc)
        ws0.write(i, 4, c302.get(uf, 0) + c400.get(uf, 0) + c401.get(uf, 0), fc)

    aba("Radioamador 302", registros["302"], cols_radio)
    aba("Radio do Cidadao", registros["400"] + registros["401"], cols_radio)

    # abas por UF (somente 302)
    por_uf_302 = collections.defaultdict(list)
    for r in registros["302"]:
        por_uf_302[r["uf"]].append(r)
    for uf in sorted(por_uf_302):
        if len(por_uf_302[uf]) >= 1 and uf:
            aba(f"302 {uf}", sorted(por_uf_302[uf], key=lambda x: (x["municipio"], x["nome"])), cols_radio)

    # metadados
    wsm = wb.add_worksheet("Metodo")
    wsm.set_column(0, 0, 22)
    wsm.set_column(1, 1, 95)
    met = [
        ("Fonte", "Anatel - dados abertos: outorga e licenciamento de prestadoras de servicos de telecomunicacoes"),
        ("Arquivo", "prestadoras_servicos_telecomunicacoes.csv (dentro do .zip publicado pela Anatel)"),
        ("Atualizacao do arquivo", "30/10/2026"),
        ("Servicos filtrados", "302 Radioamador; 400 Radio do Cidadao; 401 RC Dispensa de Autorizacao"),
        ("Deduplicacao", "por documento + Fistel da Notificacao"),
        ("O QUE A BASE TEM", "nome, CPF/CNPJ, endereco da sede, data da notificacao, Fistel, processo SEI"),
        ("O QUE A BASE NAO TEM", "indicativo (PY1MEL), classe de licenca (A/B/C), validade, faixas autorizadas"),
        ("Qualidade do contato", "cerca de 99% dos registros de pessoa fisica tem telefone e e-mail preenchidos com '-'"),
        ("Onde estao os contatos", "apenas entidades coletivas (LABRE, clubes, escolas) tem telefone/e-mail uteis"),
        ("Fonte complementar", "Sistema de Consulta de Radioamadores da Anatel (por indicativo) e LABRE (associados)"),
        ("Aviso", "data 01/01/AAAA em muitos registros indica carga em bloco, nao data real de licenciamento"),
    ]
    wsm.write(0, 0, "Item", ft)
    wsm.write(0, 1, "Descricao", ft)
    for i, (k, v) in enumerate(met, 1):
        wsm.write(i, 0, k, fc)
        wsm.write(i, 1, v, fc)

    wb.close()
    print("gerado:", DADOS / "planilha_radioamador.xlsx")
    print("\nTop UF por radioamador 302:")
    for uf, n in c302.most_common(12):
        print(f"  {uf}: {n}")


if __name__ == "__main__":
    main()
