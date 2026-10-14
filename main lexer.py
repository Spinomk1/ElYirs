"""
ELYirs - Traductor de Python a Ensamblador
Programación de Sistemas de Base 1 - Grupo K

main.py
Punto de entrada del analizador léxico: lee un archivo .py (o usa un
código de ejemplo), lo tokeniza y muestra un reporte por consola.

Uso:
    python main.py                 # usa el código de ejemplo incluido
    python main.py mi_archivo.py   # tokeniza el archivo indicado
"""

import sys

from Scanner import Scanner
from Token import Token
from ErrorHandler import ErrorManager

CODIGO_EJEMPLO = '''\
# Programa de ejemplo para probar el scanner
def calcular_salario(horas, tarifa=15.50):
    total = horas * tarifa
    if total > 1000: {
        bono = total * 0.10 ¿
    else:
bono = 0 
    return total + bono


nombre = "Aná" $
edad =$ 0x1F 
activo = True
mensaje = f"Hola {nombre}, tu salario es {calcular_salario(40, 20.0)}

for i in range(5):
    print(i)

if __name__ == "__main__":
    print(mensaje)
'''


def leer_fuente(ruta: str) -> str:
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def imprimir_reporte(tokens: list[Token]) -> None:
    encabezado = f"{'LINEA':<6}{'COL':<5}{'TIPO':<22}{'CATEGORIA':<20}{'LEXEMA':<30}VALOR"
    print(encabezado)
    print("-" * len(encabezado))
    for tok in tokens:
        if tok.is_any(*[]):
            continue
        lexema = tok.lexema.replace("\n", "\\n")
        if len(lexema) > 28:
            lexema = lexema[:25] + "..."
        print(f"{tok.linea:<6}{tok.columna:<5}{tok.type.name:<22}{tok.categoria():<20}"
              f"{lexema:<30}{tok.value!r}")


def imprimir_errores(tokens: list[Token]) -> None:
    errores = [t for t in tokens if t.is_error()]
    print(f"\n{'='*60}")
    if not errores:
        print("No se encontraron errores léxicos.")
    else:
        print(f"Se encontraron {len(errores)} error(es) léxico(s):")
        for err in errores:
            print(f"  linea {err.linea}, col {err.columna}: {err.type.name} -> {err.lexema!r}")
    print(f"{'='*60}")


def main() -> None:
    if len(sys.argv) > 1:
        codigo = leer_fuente(sys.argv[1])
        origen = sys.argv[1]
    else:
        codigo = CODIGO_EJEMPLO
        origen = "(código de ejemplo incluido)"

    print(f"Analizando: {origen}\n")

    scanner = Scanner(codigo)
    tokens = scanner.tokenize()

    imprimir_reporte(tokens)
    print(f"\nTotal de tokens generados: {len(tokens)}")

    error_manager = ErrorManager(codigo)
    error_manager.recolectar_errores_lexicos(tokens)
    error_manager.imprimir_reporte()

if __name__ == "__main__":
    main()
