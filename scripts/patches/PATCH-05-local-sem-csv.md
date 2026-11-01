# PATCH-05 — Bug de robustez: --local não re-extrai do ZIP mesmo quando CSV ausente
#
# Arquivo: scripts/atualizar_base.py
# Linhas: 209-217 (main, modo --local)
#
# Defeito: `--local` existe para "recarregar do zip local, sem rede". Mas a
# implementação só constrói o SQLite de um CSV **já extraído**. Se o usuário
# apagou o CSV e tem o ZIP, o comando falha:
#
#   $ python3 scripts/atualizar_base.py --local
#   > modo local (sem rede)
#     FALHA: CSV local ausente e --local proibe download
#
# O ZIP está em dados/estacoes_licenciadas.zip e o script o ignora.
#
# Reproduzir:
#   rm dados/Estacoes_Radioamador.csv   # CSV ausente, ZIP presente
#   python3 scripts/atualizar_base.py --local
#
# Correção: no caminho --local, se o CSV faltar mas o ZIP existir, extrair
# antes de construir. Só falhar se faltar ambos.

# --- ANTES ---
#     if "--local" in args:
#         print("> modo local (sem rede)")
#         if not os.path.exists(CSV_RADIO):
#             print("  FALHA: CSV local ausente e --local proibe download")
#             sys.exit(1)

# --- DEPOIS ---
#     if "--local" in args:
#         print("> modo local (sem rede)")
#         if not os.path.exists(CSV_RADIO):
#             if os.path.exists(ZIP):
#                 print("  CSV ausente; reextraindo do zip local")
#                 if not extrair_csv():
#                     sys.exit(1)
#             else:
#                 print("  FALHA: CSV e ZIP ausentes; impossivel prosseguir sem rede")
#                 sys.exit(1)
