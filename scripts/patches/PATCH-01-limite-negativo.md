# PATCH-01 — Bug crítico: --limite negativo vira fatia reversa e imprime milhares
#
# Arquivo: scripts/consultar.py
# Linha: 226-232 (trecho de `executar` que faz linhas[: args.limite])
#
# Defeito: `linhas[:-5]` em Python retorna TODOS os itens menos os últimos 5.
# O usuário que digita `--limite=-5` recebe "Exibindo os primeiros -5." seguido
# de 7.741 resultados numa UF com 7.746. Sem aviso, sem validação, sem erro.
#
# Reproduzir:
#   python3 scripts/consultar.py --uf RJ --limite=-5 | wc -l
#   (esperado: erro ou 5 resultados; observado: 77 mil linhas e BrokenPipeError)
#
# Correção: validar args.limite antes de usar; quando inválido, sair com mensagem.
#
# ---------- MUDANÇA ----------
# Em `executar`, logo após `linhas = con.execute(sql, params).fetchall()`:

# --- ANTES ---
#     mostradas = linhas[: args.limite]
#     print(f"\n{len(linhas)} resultado(s) encontrado(s).")
#     if len(linhas) > args.limite:
#         print(f"Exibindo os primeiros {args.limite}. "
#               f"Use --limite N para ver mais, ou --exportar arquivo.csv.")

# --- DEPOIS ---
#     if args.limite < 1:
#         print(f"\nLimite invalido: {args.limite}. Use um inteiro >= 1.")
#         return 2
#     mostradas = linhas[: args.limite]
#     print(f"\n{len(linhas)} resultado(s) encontrado(s).")
#     if len(linhas) > args.limite:
#         print(f"Exibindo os primeiros {args.limite}. "
#               f"Use --limite N para ver mais, ou --exportar arquivo.csv.")
