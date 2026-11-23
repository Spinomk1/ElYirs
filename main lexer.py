
import argparse

from Scanner import Scanner
from Token import Token
from ErrorHandler import ErrorManager, FaseError
from SymbolTable import TablaSimbolos

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
        lexema = tok.lexema.replace("\n", "\\n")
        if len(lexema) > 28:
            lexema = lexema[:25] + "..."
        print(f"{tok.linea:<6}{tok.columna:<5}{tok.type.name:<22}{tok.categoria():<20}"
              f"{lexema:<30}{tok.value!r}")

def main() -> None:
    ap = argparse.ArgumentParser(description="Front-End de ELYirs: léxico + tabla de símbolos")
    ap.add_argument("archivo", nargs="?",
                    help="archivo a analizar (si no se indica, usa el ejemplo incluido)")
    ap.add_argument("--solo-lexico", action="store_true",
                    help="no construye la tabla de símbolos")
    ap.add_argument("--completa", action="store_true",
                    help="en la tabla, muestra también los predefinidos que el código no usa")
    ap.add_argument("--csv", metavar="SALIDA.csv", help="exporta la tabla de símbolos a CSV")
    args = ap.parse_args()

    if args.archivo:
        try:
            codigo = leer_fuente(args.archivo)
        except OSError as e:
            print(f"No se pudo abrir '{args.archivo}': {e}")
            raise SystemExit(1)
        origen = args.archivo
    else:
        codigo = CODIGO_EJEMPLO
        origen = "(código de ejemplo incluido)"

    print(f"Analizando: {origen}\n")

    # ---------- 1. Análisis léxico ----------
    tokens = Scanner(codigo).tokenize()
    imprimir_reporte(tokens)
    print(f"\nTotal de tokens generados: {len(tokens)}")

    gestor = ErrorManager(codigo)
    gestor.recolectar_errores_lexicos(tokens)

    # ---------- 2. Tabla de símbolos ----------
    if not args.solo_lexico:
        print()
        tabla = TablaSimbolos().construir(tokens)
        tabla.imprimir(solo_usados=not args.completa)
        if args.csv:
            tabla.exportar_csv(args.csv)
            print(f"CSV exportado a {args.csv}\n")
        for linea, columna, mensaje in sorted(tabla.incidencias):
            gestor.agregar_error(FaseError.SEMANTICO, mensaje, linea, columna, "")

    # ---------- 3. Reporte único de errores ----------
    gestor.imprimir_reporte()


if __name__ == "__main__":
    main()
