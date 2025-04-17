# contexto_equipo.py

chunks_equipo = []

# Cargar los 3 TXT
for filename in [
    "08_El_equipo_ideal_(I).txt",
    "09_El_equipo_ideal_(II).txt",
    "10_El_equipo_ideal_(III).txt"
]:
    with open(filename, "r", encoding="utf-8") as f:
        texto = f.read()
        trozos = texto.split("\n\n")
        chunks_equipo.extend([trozo.strip() for trozo in trozos if trozo.strip()])
