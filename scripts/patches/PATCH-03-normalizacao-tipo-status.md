# PATCH-03 — Bug grave: --tipo e --status não normalizam acentos; --status não normaliza case
#
# Arquivo: scripts/consultar.py
# Linha: 121-128 (montar_consulta)
#
# Defeitos de normalização inconsistentes entre filtros:
#
#   --tipo Móvel   → matches "Móvel"   OK
#   --tipo Movel   → matches "Movel"   NÃO BATE → 0 resultados sem aviso
#   --tipo FIXA    → "Fixa" via .capitalize()  OK por acidente
#   --tipo N/I     → .capitalize() dá "N/i"  NÃO BATE
#   --status Ativa → matches "Ativa"   OK
#   --status ativa → matches "ativa"   NÃO BATE (case-sensitive)
#   --status N/I   → matches "N/I"    OK
#   --status n/i   → NÃO BATE
#
# A base tem os valores literais: ['Fixa','Móvel','Repetidora','Terrena','N/I']
# e ['Ativa','Vencida','N/I']. O usuário não tem como adivinhar a forma.
#
# Reproduzir:
#   python3 scripts/consultar.py --uf RJ --tipo Movel    -> 0 resultados
#   python3 scripts/consultar.py --uf RJ --tipo "Móvel"  -> 4026 resultados
#   python3 scripts/consultar.py --uf RJ --status ativa  -> 0 resultados
#   python3 scripts/consultar.py --uf RJ --status Ativa  -> 6009 resultados
#
# Correção: normalizar o input do usuário para o vocabulário da base
# (case-insensitive e sem acento), com mensagem de erro se não casar.

# --- ANTES (em montar_consulta) ---
#     if args.tipo:
#         t = args.tipo.capitalize()
#         onde.append("tipo_estacao = ?")
#         params.append(t)
#         desc.append(f"tipo {t}")
#
#     if args.status:
#         onde.append("status = ?")
#         params.append(args.status)
#         desc.append(f"status {args.status}")

# --- DEPOIS ---
#     TIPOS = {"fixa":"Fixa","movel":"Móvel","móvel":"Móvel",
#              "repetidora":"Repetidora","terrena":"Terrena",
#              "n/i":"N/I","ni":"N/I"}
#     STATUS = {"ativa":"Ativa","vencida":"Vencida","n/i":"N/I","ni":"N/I"}
#
#     if args.tipo:
#         chave = args.tipo.strip().lower()
#         if chave not in TIPOS:
#             print(f"Tipo invalido: '{args.tipo}'. "
#                   f"Use: Fixa, Movel, Repetidora, Terrena ou N/I.")
#             return None, None, ""
#         t = TIPOS[chave]
#         onde.append("tipo_estacao = ?")
#         params.append(t)
#         desc.append(f"tipo {t}")
#
#     if args.status:
#         chave = args.status.strip().lower()
#         if chave not in STATUS:
#             print(f"Status invalido: '{args.status}'. "
#                   f"Use: Ativa, Vencida ou N/I.")
#             return None, None, ""
#         s = STATUS[chave]
#         onde.append("status = ?")
#         params.append(s)
#         desc.append(f"status {s}")
#
# Nota: `executar` já trata `sql is None`. O return com descricao vazia precisa
# ser harmonizado — ver integração no patch de refactor (não aplicado aqui
# porque o dono pediu só proposta).
