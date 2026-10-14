"""
ELYirs - Traductor de Python a Ensamblador
Programación de Sistemas de Base 1 - Grupo K

ErrorHandler.py
Gestor centralizado de errores. Recolecta, clasifica y formatea los errores
léxicos, sintácticos y semánticos, mostrando el contexto exacto en el código fuente.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List
from TokenTypes import TokenType
from Token import Token

class FaseError(Enum):
    LEXICO = "Léxico"
    SINTAXIS = "Sintaxis"
    SEMANTICO = "Semántico"
    ENSAMBLADOR = "Generación de Código"

# Diccionario para traducir los tokens de error a mensajes amigables
MENSAJES_LEXICOS = {
    TokenType.UNKNOWN: "Componente léxico desconocido.",
    TokenType.INVALID_CHARACTER: "Carácter no válido o no reconocido.",
    TokenType.INVALID_NUMBER: "Formato numérico inválido.",
    TokenType.INVALID_IDENTIFIER: "Identificador inválido (posiblemente comienza con números).",
    TokenType.LEADING_ZERO_NUMBER: "Los números enteros no pueden tener ceros a la izquierda.",
    TokenType.INVALID_UNDERSCORE_NUMBER: "Uso inválido de guiones bajos en el número.",
    TokenType.UNTERMINATED_STRING: "Cadena de texto sin comilla de cierre.",
    TokenType.UNTERMINATED_TRIPLE_STRING: "Cadena de texto multilínea sin cerrar.",
    TokenType.INVALID_ESCAPE: "Secuencia de escape inválida en la cadena.",
    TokenType.INVALID_INDENTATION: "La indentación no coincide con ningún nivel de bloque abierto.",
    TokenType.MIXED_TABS_SPACES: "Uso mixto de tabuladores y espacios en la indentación.",
    TokenType.UNMATCHED_BRACKET: "Símbolo de cierre sin su pareja de apertura.",
    TokenType.UNCLOSED_BRACKET: "Símbolo de agrupación sin cerrar al finalizar el archivo."
}

@dataclass
class CompilerError:
    fase: FaseError
    mensaje: str
    linea: int
    columna: int
    lexema: str

class ErrorManager:
    def __init__(self, source_code: str):
        self.source_code = source_code.replace("\r\n", "\n").replace("\r", "\n")
        self.errores: List[CompilerError] = []

    def recolectar_errores_lexicos(self, tokens: List[Token]):
        """Filtra los tokens generados por el Scanner y extrae los que son errores."""
        for tok in tokens:
            if tok.is_error():
                mensaje = MENSAJES_LEXICOS.get(tok.type, f"Error léxico no especificado: {tok.type.name}")
                self.agregar_error(FaseError.LEXICO, mensaje, tok.linea, tok.columna, tok.lexema)

    def agregar_error(self, fase: FaseError, mensaje: str, linea: int, columna: int, lexema: str):
        """Agrega un nuevo error al registro central."""
        nuevo_error = CompilerError(fase, mensaje, linea, columna, lexema)
        self.errores.append(nuevo_error)

    def hay_errores(self) -> bool:
        return len(self.errores) > 0

    def _formatear_contexto(self, error: CompilerError) -> str:
        """Extrae la línea de código afectada y coloca un apuntador '^' bajo el error."""
        lineas_fuente = self.source_code.split('\n')
        
        # Validar que la línea exista en el código fuente
        if 1 <= error.linea <= len(lineas_fuente):
            linea_codigo = lineas_fuente[error.linea - 1]
            
            # Reemplazar tabs por espacios para no romper la alineación en consola
            prefijo = linea_codigo[:max(0, error.columna - 1)]
            espaciado_apuntador = "".join(' ' if ch != '\t' else '\t' for ch in prefijo)
            
            # Resaltar en rojo si la terminal lo soporta (opcional)
            color_rojo = "\033[91m"
            reset_color = "\033[0m"
            
            return f"    {linea_codigo}\n    {espaciado_apuntador}{color_rojo}^{reset_color}"
        return ""

    def imprimir_reporte(self):
        """Imprime todos los errores con su contexto visual en la consola."""
        print(f"\n{'='*60}")
        if not self.hay_errores():
            print("Compilación exitosa. No se encontraron errores.")
            print(f"{'='*60}")
            return

        print(f"SE ENCONTRARON {len(self.errores)} ERROR(ES):\n")
        
        for i, error in enumerate(self.errores, 1):
            encabezado = f"[{error.fase.value}] Línea {error.linea}, Columna {error.columna}: {error.mensaje}"
            print(f"{i}. {encabezado}")
            if error.lexema:
                print(f"   Lexema problemático: {error.lexema!r}")
            
            contexto = self._formatear_contexto(error)
            if contexto:
                print(f"{contexto}\n")
                
        print(f"{'='*60}")