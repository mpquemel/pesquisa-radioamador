# PATCH-04 — Bug de UX/documentação: help promete CPF completo que nunca funciona
#
# Arquivo: scripts/consultar.py
# Linhas: 30 (docstring) e 356 (help de --cpf)
#
# Defeito: o help e os exemplos dizem `--cpf 12345678901` (CPF completo, 11 dígitos).
# Mas a base grava `doc_digitos` com apenas os 5 dígitos centrais visíveis
# (máscara da Anatel `***65935**` → `65935`). Buscar CPF completo
# SEMPRE devolve "Nenhum resultado encontrado", o que parece erro mas é o
# desenho da base. O usuário não tem como saber.
#
# Reproduzir:
#   python3 scripts/consultar.py --cpf 12345678901     # 11 dígitos -> 0 resultados
#   python3 scripts/consultar.py --cpf 65935           # 5 dígitos  -> 2 resultados
#
# Efeitos:
#   (a) usuário tenta CPF completo de si mesmo, acha que não está na base
#   (b) usuário tenta CPF de outra pessoa, acha que está coberto — incorreto
#
# Correções (três, complementares):
#
# 1. Atualizar docstring e epilog para refletir a máscara:
#    "Documento: apenas os 5 dígitos visíveis da máscara Anatel (ex.: 65935).
#     CPF completo NÃO é buscável — a Anatel não publica."
#
# 2. Validar o comprimento em montar_consulta: se sobrar 11 dígitos após
#    so_digitos, alertar que está buscando mascarado e extrair os 5 centrais
#    do padrão `***DDDDD**` (posições 3..7), senão devolver erro claro.
#
# 3. Documentar no README/manual: `doc_digitos` NÃO é um identificador único
#    de pessoa — só 5 dígitos centrais de CPF. Dois CPFs diferentes podem
#    ter os mesmos 5 dígitos centrais (raro mas possível: ~1/100.000).
#    Confirmar pelo indicativo antes de concluir.
#
# --- ANTES (em montar_consulta) ---
#     if args.cpf:
#         d = so_digitos(args.cpf)
#         onde.append("doc_digitos = ?")
#         params.append(d)
#         desc.append(f"documento {d}")

# --- DEPOIS ---
#     if args.cpf:
#         d = so_digitos(args.cpf)
#         if len(d) == 11:  # CPF completo: extrair os 5 dígitos visíveis
#             print("Aviso: a base da Anatel mascara o CPF (***99999**).")
#             print(f"Buscando pelos 5 digitos visiveis: {d[3:8]}.")
#             d = d[3:8]
#         elif len(d) == 14:  # CNPJ vem inteiro — não precisa ajuste
#             pass
#         elif len(d) != 5:
#             print(f"Documento '{args.cpf}' tem {len(d)} digitos.")
#             print("Para CPF: use os 5 digitos visiveis da mascara (***99999**).")
#             print("Para CNPJ: use os 14 digitos completos.")
#             return None, None, ""
#         onde.append("doc_digitos = ?")
#         params.append(d)
#         desc.append(f"documento {d}")
