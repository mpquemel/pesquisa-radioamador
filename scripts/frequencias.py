#!/usr/bin/env python3
"""
frequencias.py — Parser das frequencias de operacao das estacoes.

A coluna "Frequencias de Operacao da Estacao" da base da Anatel vem em
formatos variados. Nas repetidoras o dado e util (99,4% preenchido), mas
71 dos 1.233 registros trazem irregularidades:

  - mais de um conjunto TX/RX na mesma celula, separados por ";"
  - aspas soltas dentro e no fim do campo
  - erro de separador decimal: "145,370 / 14.477,000 MHz" (14 GHz)

Este modulo separa o joio do trigo. Nao adivinha: quando um valor nao e
uma frequencia plausivel, devolve a marcacao de suspeita em vez de
mostrar numero inventado.

FORMATO DE SAIDA por conjunto:
    {"tx": 147.360, "rx": 147.960, "offset": -0.600, "faixa": "2m",
     "origem": "147,360 / 147,960 MHz"}

Convencao adotada (conferir com o autor antes de mudar):
    A Anatel publica "A / B". Em todos os 1.162 casos limpos, A > B na
    faixa de 2 m (147,360 / 147,960) e A > B tambem em 70 cm
    (439,890 / 434,890). Em 2 m o padrao brasileiro e repetidora
    transmitindo em 147,360 e recebendo em 147,960 (shift negativo de -600).
    Logo: primeiro valor = TX (saida da repetidora), segundo = RX (entrada).
"""

import re

# Faixas de radioamador reconhecidas (MHz). Nao e para validar legislacao:
# e para rejeitar erro de digitacao como "14.477,000 MHz".
FAIXAS = [
    ("6m",   50.0,   54.0),
    ("10m",  28.0,   29.7),
    ("2m",  144.0,  148.0),
    ("1,25m", 222.0, 225.0),
    ("70cm", 430.0,  450.0),
    ("33cm", 902.0,  928.0),
    ("23cm", 1240.0, 1300.0),
]

# Pares TX/RX que aparecem repetidos em varios estados da base federal.
# Servem para reconstruir registros com separador decimal corrompido.
# Montada por medicao em 01/11/2026: cada par abaixo ocorre em 3 ou mais
# unidades federativas distintas.
PARES_NACIONAIS = {
    (145.37, 144.77): "padrao 2m nacional, presente em 15 estados",
    (147.36, 147.96): "canal 2m",
    (146.89, 146.29): "canal 2m",
    (439.89, 434.89): "canal 70cm",
    (145.45, 144.85): "canal 2m",
    (147.09, 147.69): "canal 2m",
}

RE_PAR = re.compile(
    r"(\d{1,3}(?:\.\d{3})*,\d+)\s*/\s*(\d{1,3}(?:\.\d{3})*,\d+)\s*MHz",
    re.IGNORECASE)
RE_SO = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d+)\s*MHz", re.IGNORECASE)
RE_SIMPLES = re.compile(r"^(\d{1,3}(?:\.\d{3})*,\d+)$")


def numero(txt):
    """Converte '14.477,000' ou '147,360' em float. Formato brasileiro:
    ponto e separador de milhar, virgula e decimal."""
    t = txt.strip()
    if re.fullmatch(r"\d{1,2}\.\d{3},\d+", t):
        # "14.477,000" — ponto de milhar
        return float(t.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d+\.\d+", t) and "," not in t:
        # "14.770" — ponto decimal
        return float(t)
    return float(t.replace(".", "").replace(",", "."))


def faixa_de(mhz):
    for nome, lo, hi in FAIXAS:
        if lo <= mhz <= hi:
            return nome
    return None


def limpar(txt):
    """Remove aspas soltas e espacos repetidos."""
    t = (txt or "").replace('"', " ").replace("“", " ").replace("”", " ")
    return re.sub(r"\s+", " ", t).strip()


def parse(valor):
    """Interpreta a celula inteira.

    Devolve dict com:
      conjuntos: lista de conjuntos TX/RX validos
      suspeitas: lista de textos rejeitados, com o motivo
      vazio:     True quando nao havia dado nenhum
    """
    bruto = (valor or "").strip()
    if bruto in ("", "N/I", "N/A"):
        return {"conjuntos": [], "suspeitas": [], "vazio": True}

    texto = limpar(bruto)
    # a Anatel separa conjuntos por ";" — as vezes por "," entre conjuntos
    partes = [p.strip() for p in re.split(r"[;]", texto) if p.strip()]

    conjuntos, suspeitas = [], []

    for parte in partes:
        # Caso especial da base da Anatel: separador decimal trocado.
        # A Anatel gravou "0.147" como "0,147" (virgula no lugar do ponto).
        # Multiplicar por 1000 devolve o valor pretendido. So aplicamos
        # quando o resultado cai numa faixa de radioamador; caso contrario
        # a parte segue para o fluxo normal e sera rejeitada.
        parte_norm = re.sub(
            r"(?<![\d.,])(0,\d+)(?![\d,])",
            lambda mm: ("%.3f" % (float(mm.group(1).replace(",", ".")) * 1000))
                       .replace(".", "X").replace(",", ".").replace("X", ",")
                       if faixa_de(float(mm.group(1).replace(",", ".")) * 1000)
                       else mm.group(1),
            parte)
        corrigido = (parte_norm != parte)
        # caso "A / B MHz"
        m = RE_PAR.search(parte_norm)
        if m:
            try:
                a, b = numero(m.group(1)), numero(m.group(2))
            except ValueError:
                suspeitas.append({"texto": parte, "motivo": "numero ilegivel"})
                continue
            fa, fb = faixa_de(a), faixa_de(b)
            if not fa or not fb:
                # tenta reconstruir: o primeiro valor pode estar intacto e
                # o segundo corrompido. Se (A, B/1000) casa com um par
                # nacional conhecido, registramos como INFERIDO.
                inferido = None
                if fa and not fb:
                    # o separador decimal foi trocado; testa os divisores
                    # plausiveis e aceita o que cair em faixa E casar com um
                    # par nacional conhecido. Sem as duas condicoes, nao
                    # inferimos: 14477/100=144.77 (certo); 14477/1000 errado.
                    for div in (100.0, 1000.0):
                        cand = round(b / div, 3)
                        if (a, cand) in PARES_NACIONAIS and faixa_de(cand):
                            inferido = {
                                "tx": a, "rx": cand,
                                "offset": round(a - cand, 4),
                                "faixa": faixa_de(cand),
                                "origem": m.group(0),
                                "procedencia": "inferido",
                                "nota": ("Reconstruido: %s foi gravado como %s. %s."
                                         % (("%.3f" % cand).replace(".", ","),
                                            m.group(2),
                                            PARES_NACIONAIS[(a, cand)])),
                            }
                            break
                if inferido:
                    conjuntos.append(inferido)
                    continue
                suspeitas.append({
                    "texto": parte,
                    "motivo": "frequencia fora das faixas de radioamador",
                    "valores": [a, b],
                })
                continue
            conjuntos.append({
                "tx": a, "rx": b,
                "offset": round(a - b, 4),
                "faixa": fa if fa == fb else f"{fa}/{fb}",
                "origem": m.group(0),
                "procedencia": "corrigido" if corrigido else "limpo",
            })
            continue

        # caso de um unico valor: "147,360" ou "147,360 MHz"
        m2 = RE_SO.search(parte_norm) or RE_SIMPLES.match(parte_norm)
        if m2:
            try:
                a = numero(m2.group(1))
            except ValueError:
                suspeitas.append({"texto": parte, "motivo": "numero ilegivel"})
                continue
            fa = faixa_de(a)
            if not fa:
                suspeitas.append({
                    "texto": parte,
                    "motivo": "frequencia fora das faixas de radioamador",
                    "valores": [a],
                })
                continue
            conjuntos.append({
                "tx": a, "rx": a, "offset": 0.0, "faixa": fa,
                "origem": parte, "procedencia": "corrigido" if corrigido else "limpo",
            })
            continue

        suspeitas.append({"texto": parte, "motivo": "formato nao reconhecido"})

    return {"conjuntos": conjuntos, "suspeitas": suspeitas, "vazio": False}


def shift_do_usuario(rx):
    """Retorna (shift_mhz, rotulo) do ponto de vista de quem opera.

    Regra de canalizacao brasileira, confirmada pelo titular do projeto
    (PY1MEL, Classe A) em 01/11/2026:
      VHF 2 m : escuta abaixo de 146,999 MHz -> -0,600 MHz; acima -> +0,600
      UHF 70 cm: escuta abaixo de 440 MHz     -> -5,000 MHz; acima -> +5,000
    """
    if 144.0 <= rx <= 148.0:
        return (-0.600, "-600 kHz") if rx < 146.999 else (0.600, "+600 kHz")
    if 430.0 <= rx <= 450.0:
        return (-5.000, "-5 MHz") if rx < 440.0 else (5.000, "+5 MHz")
    if 50.0 <= rx <= 54.0:
        return (-1.000, "-1 MHz") if rx < 52.0 else (1.000, "+1 MHz")
    if 222.0 <= rx <= 225.0:
        return (-1.600, "-1,6 MHz") if rx < 223.5 else (1.600, "+1,6 MHz")
    if 902.0 <= rx <= 928.0:
        return (-25.000, "-25 MHz") if rx < 915.0 else (25.000, "+25 MHz")
    if 1240.0 <= rx <= 1300.0:
        return (-12.000, "-12 MHz") if rx < 1270.0 else (12.000, "+12 MHz")
    if 28.0 <= rx <= 29.7:
        return (-0.100, "-100 kHz") if rx < 29.0 else (0.100, "+100 kHz")
    return (0.0, "")


def descrever(valor):
    """Descricao completa de uma celula de frequencia para a tela.

    Devolve dict:
      texto     : linha principal pronta para exibir
      detalhes  : lista de linhas auxiliares (shift, procedencia)
      suspeita  : True quando nao ha frequencia confiavel
      procedencia: 'limpo' | 'corrigido' | 'inferido' | ''
    """
    r = parse(valor)
    if r["vazio"]:
        return {"texto": "", "detalhes": [], "suspeita": False,
                "procedencia": ""}
    if not r["conjuntos"]:
        return {"texto": "frequencia nao confiavel na base",
                "detalhes": [], "suspeita": True, "procedencia": ""}

    linhas, detalhes, procs = [], [], set()
    for c in r["conjuntos"]:
        procs.add(c["procedencia"])
        tx = ("%.3f" % c["tx"]).replace(".", ",")
        rx = ("%.3f" % c["rx"]).replace(".", ",")
        if abs(c["tx"] - c["rx"]) < 0.0005:
            linhas.append(f"{tx} MHz ({c['faixa']}, simplex)")
        else:
            linhas.append(f"{tx} / {rx} MHz ({c['faixa']})")
            sh, rot = shift_do_usuario(c["rx"])
            if sh:
                confere = abs(abs(sh) - abs(c["tx"] - c["rx"])) < 0.0005
                detalhes.append(
                    f"Escuta {rx}, shift {rot}" +
                    ("" if confere else "  (o par na base nao segue o padrao)"))
        if c["procedencia"] in ("corrigido", "inferido") and c.get("nota"):
            detalhes.append(c["nota"])
    if any(c["procedencia"] == "inferido" for c in r["conjuntos"]):
        detalhes.append("Valor reconstruido: conferir no ar antes de usar.")
    return {"texto": " ; ".join(linhas), "detalhes": detalhes,
            "suspeita": False,
            "procedencia": ",".join(sorted(procs))}


def resumo_curto(valor):
    """Texto pronto para a tela, em uma linha.
    Ex.: '147,360 / 147,960 MHz (2m, -600 kHz)'"""
    r = parse(valor)
    if r["vazio"]:
        return ""
    if not r["conjuntos"]:
        return "frequencia nao confiavel na base"
    itens = []
    for c in r["conjuntos"]:
        s = f"{c['tx']:.3f} / {c['rx']:.3f} MHz ({c['faixa']}"
        if c["offset"]:
            s += f", {c['offset']*1000:+.0f} kHz"
        s += ")"
        itens.append(s.replace(".", ",", 1))
    return " ; ".join(itens)


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print(repr(arg), "->", parse(arg))
