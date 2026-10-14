"""
ELYirs - Traductor de Python a Ensamblador
Programación de Sistemas de Base 1 - Grupo K

TokenTypes.py (versión 2, basada en la propuesta de tokens del equipo)

Organización de los tipos de token:
  1. Especiales y estructura del código
  2. Identificadores
  3. Literales numéricos
  4. Literales de cadena
  5. Constantes (True, False, None)
  6. Palabras reservadas
  7. Operadores (aritméticos, comparación, asignación, bits)
  8. Agrupación y puntuación
  9. Funciones integradas (print, input, len, range...)
 10. Excepciones integradas (ValueError, ZeroDivisionError...)
 11. Módulos soportados (math, pandas, matplotlib...)
 12. Errores léxicos
"""

from enum import Enum, auto


class TokenType(Enum):
    # ==========================================
    # 1. Especiales y estructura del código
    # ==========================================
    EOF = auto()                  # fin del archivo
    NEWLINE = auto()              # fin de una instrucción
    NL = auto()                   # salto de línea que NO termina instrucción (línea vacía o dentro de paréntesis)
    INDENT = auto()               # aumenta la sangría: abre bloque
    DEDENT = auto()               # disminuye la sangría: cierra bloque
    COMMENT = auto()              # # comentario
    LINE_CONTINUATION = auto()    # \ al final de la línea

    # ==========================================
    # 2. Identificadores
    # ==========================================
    IDENTIFIER = auto()           # salario_bruto, calcular_salario
    DUNDER_NAME = auto()          # __name__, __main__, __init__

    # ==========================================
    # 3. Literales numéricos
    # ==========================================
    INTEGER = auto()              # 40, 1_000
    FLOAT = auto()                # 15.50, .5
    SCIENTIFIC = auto()           # 1e10, 2.5E-3
    HEX_INTEGER = auto()          # 0xFF
    OCTAL_INTEGER = auto()        # 0o17
    BINARY_INTEGER = auto()       # 0b1010
    IMAGINARY = auto()            # 3j

    # ==========================================
    # 4. Literales de cadena
    # ==========================================
    STRING = auto()               # 'Ana', "texto"
    TRIPLE_STRING = auto()        # """docstring""" o '''texto'''
    RAW_STRING = auto()           # r"C:\ruta"
    BYTES = auto()                # b"datos"
    RAW_BYTES = auto()            # rb"datos"
    F_STRING_START = auto()       # f"        (inicio de f-string)
    F_STRING_MIDDLE = auto()      # texto fijo dentro de la f-string
    F_STRING_END = auto()         # "         (fin de f-string)

    # ==========================================
    # 5. Constantes
    # ==========================================
    TRUE = auto()                 # True
    FALSE = auto()                # False
    NONE = auto()                 # None

    # ==========================================
    # 6. Palabras reservadas
    # ==========================================
    # Funciones
    DEF = auto()
    RETURN = auto()
    LAMBDA = auto()
    YIELD = auto()
    # Decisiones
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    MATCH = auto()                # palabra reservada "suave" (Python 3.10+)
    CASE = auto()                 # palabra reservada "suave" (Python 3.10+)
    # Repeticiones
    WHILE = auto()
    FOR = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    PASS = auto()
    # Operadores lógicos y de identidad
    AND = auto()
    OR = auto()
    NOT = auto()
    IS = auto()
    # Módulos
    IMPORT = auto()
    FROM = auto()
    AS = auto()
    # Clases y ámbitos
    CLASS = auto()
    GLOBAL = auto()
    NONLOCAL = auto()
    DEL = auto()
    # Manejo de errores
    TRY = auto()
    EXCEPT = auto()
    FINALLY = auto()
    RAISE = auto()
    ASSERT = auto()
    WITH = auto()
    # Asincronía
    ASYNC = auto()
    AWAIT = auto()

    # ==========================================
    # 7. Operadores
    # ==========================================
    # Aritméticos
    PLUS = auto()                 # +
    MINUS = auto()                # -
    MULTIPLY = auto()             # *
    DIVIDE = auto()               # /
    FLOOR_DIVIDE = auto()         # //
    MODULO = auto()               # %
    POWER = auto()                # **
    # Comparación
    EQUAL = auto()                # ==
    NOT_EQUAL = auto()            # !=
    LESS_THAN = auto()            # <
    GREATER_THAN = auto()         # >
    LESS_EQUAL = auto()           # <=
    GREATER_EQUAL = auto()        # >=
    # Asignación
    ASSIGN = auto()               # =
    PLUS_ASSIGN = auto()          # +=
    MINUS_ASSIGN = auto()         # -=
    MULTIPLY_ASSIGN = auto()      # *=
    DIVIDE_ASSIGN = auto()        # /=
    FLOOR_DIVIDE_ASSIGN = auto()  # //=
    MODULO_ASSIGN = auto()        # %=
    POWER_ASSIGN = auto()         # **=
    BIT_AND_ASSIGN = auto()       # &=
    BIT_OR_ASSIGN = auto()        # |=
    BIT_XOR_ASSIGN = auto()       # ^=
    LEFT_SHIFT_ASSIGN = auto()    # <<=
    RIGHT_SHIFT_ASSIGN = auto()   # >>=
    MATMUL_ASSIGN = auto()        # @=
    WALRUS = auto()               # :=
    # A nivel de bits (equivalente directo en ensamblador: AND, OR, XOR, NOT, SHL, SHR)
    BIT_AND = auto()              # &
    BIT_OR = auto()               # |
    BIT_XOR = auto()              # ^
    BIT_NOT = auto()              # ~
    LEFT_SHIFT = auto()           # <<
    RIGHT_SHIFT = auto()          # >>

    # ==========================================
    # 8. Agrupación y puntuación
    # ==========================================
    LPAREN = auto()               # (
    RPAREN = auto()               # )
    LBRACKET = auto()             # [
    RBRACKET = auto()             # ]
    LBRACE = auto()               # {
    RBRACE = auto()               # }
    COMMA = auto()                # ,
    DOT = auto()                  # .
    COLON = auto()                # :
    SEMICOLON = auto()            # ;
    ARROW = auto()                # ->
    AT = auto()                   # @  (decorador o multiplicación de matrices)
    ELLIPSIS = auto()             # ...

    # ==========================================
    # 9. Funciones integradas
    # En Python son identificadores, pero ELYirs las reconoce aparte porque
    # cada una necesita una traducción especial a ensamblador
    # (print -> rutina de salida, input -> rutina de entrada, etc.)
    # ==========================================
    # Entrada / salida
    BUILTIN_PRINT = auto()
    BUILTIN_INPUT = auto()
    BUILTIN_OPEN = auto()
    # Conversión de tipos
    BUILTIN_INT = auto()
    BUILTIN_FLOAT = auto()
    BUILTIN_STR = auto()
    BUILTIN_BOOL = auto()
    BUILTIN_COMPLEX = auto()
    BUILTIN_BYTES = auto()
    BUILTIN_BIN = auto()
    BUILTIN_HEX = auto()
    BUILTIN_OCT = auto()
    BUILTIN_CHR = auto()
    BUILTIN_ORD = auto()
    # Colecciones
    BUILTIN_LIST = auto()
    BUILTIN_DICT = auto()
    BUILTIN_TUPLE = auto()
    BUILTIN_SET = auto()
    BUILTIN_FROZENSET = auto()
    BUILTIN_RANGE = auto()
    BUILTIN_LEN = auto()
    # Matemáticas
    BUILTIN_ABS = auto()
    BUILTIN_ROUND = auto()
    BUILTIN_POW = auto()
    BUILTIN_DIVMOD = auto()
    BUILTIN_MIN = auto()
    BUILTIN_MAX = auto()
    BUILTIN_SUM = auto()
    # Iteración
    BUILTIN_ENUMERATE = auto()
    BUILTIN_ZIP = auto()
    BUILTIN_MAP = auto()
    BUILTIN_FILTER = auto()
    BUILTIN_SORTED = auto()
    BUILTIN_REVERSED = auto()
    BUILTIN_ANY = auto()
    BUILTIN_ALL = auto()
    BUILTIN_ITER = auto()
    BUILTIN_NEXT = auto()
    # Tipos y objetos
    BUILTIN_TYPE = auto()
    BUILTIN_ISINSTANCE = auto()
    BUILTIN_ID = auto()
    BUILTIN_REPR = auto()
    BUILTIN_FORMAT = auto()
    BUILTIN_SUPER = auto()
    BUILTIN_OBJECT = auto()
    BUILTIN_HASATTR = auto()
    BUILTIN_GETATTR = auto()
    BUILTIN_SETATTR = auto()

    # ==========================================
    # 10. Excepciones integradas
    # ==========================================
    EXC_EXCEPTION = auto()
    EXC_ARITHMETIC_ERROR = auto()       # padre de ZeroDivisionError y OverflowError
    EXC_VALUE_ERROR = auto()
    EXC_TYPE_ERROR = auto()
    EXC_NAME_ERROR = auto()
    EXC_ZERO_DIVISION_ERROR = auto()
    EXC_OVERFLOW_ERROR = auto()
    EXC_INDEX_ERROR = auto()
    EXC_KEY_ERROR = auto()
    EXC_ATTRIBUTE_ERROR = auto()
    EXC_FILE_NOT_FOUND_ERROR = auto()
    EXC_OS_ERROR = auto()
    EXC_PERMISSION_ERROR = auto()
    EXC_UNICODE_DECODE_ERROR = auto()   # al leer CSV/TXT con acentos mal codificados
    EXC_EOF_ERROR = auto()
    EXC_RUNTIME_ERROR = auto()
    EXC_RECURSION_ERROR = auto()
    EXC_NOT_IMPLEMENTED_ERROR = auto()
    EXC_ASSERTION_ERROR = auto()
    EXC_IMPORT_ERROR = auto()
    EXC_STOP_ITERATION = auto()
    EXC_KEYBOARD_INTERRUPT = auto()
    EXC_MEMORY_ERROR = auto()

    # ==========================================
    # 11. Módulos soportados
    # (pandas y matplotlib vienen de la propuesta: leer XLSX/CSV y graficar)
    # ==========================================
    MODULE_MATH = auto()
    MODULE_RANDOM = auto()
    MODULE_SYS = auto()
    MODULE_OS = auto()
    MODULE_TIME = auto()
    MODULE_CSV = auto()
    MODULE_DATETIME = auto()
    MODULE_STATISTICS = auto()
    MODULE_NUMPY = auto()               # lo usa pandas internamente
    MODULE_PANDAS = auto()
    MODULE_OPENPYXL = auto()            # pandas lo necesita para leer XLSX
    MODULE_MATPLOTLIB = auto()

    # ==========================================
    # 12. Errores léxicos
    # ==========================================
    UNKNOWN = auto()                    # token no clasificado
    INVALID_CHARACTER = auto()          # $, ?, ` fuera de una cadena
    INVALID_NUMBER = auto()             # 12.3.4, 0xZZ
    INVALID_IDENTIFIER = auto()         # 2variable
    LEADING_ZERO_NUMBER = auto()        # 007 (no válido en Python 3)
    INVALID_UNDERSCORE_NUMBER = auto()  # 1__000, 100_
    UNTERMINATED_STRING = auto()        # "texto sin cerrar
    UNTERMINATED_TRIPLE_STRING = auto() # """docstring sin cerrar
    INVALID_ESCAPE = auto()             # "\q"
    INVALID_INDENTATION = auto()        # la sangría no coincide con ningún bloque abierto
    MIXED_TABS_SPACES = auto()          # sangría con tabuladores y espacios mezclados
    UNMATCHED_BRACKET = auto()          # ) ] } sin su pareja de apertura
    UNCLOSED_BRACKET = auto()           # ( [ { sin cerrar al terminar el archivo


# ======================================================================
# Tablas de búsqueda para el scanner
# ======================================================================

PALABRAS_RESERVADAS = {
    "True": TokenType.TRUE, "False": TokenType.FALSE, "None": TokenType.NONE,
    "def": TokenType.DEF, "return": TokenType.RETURN,
    "lambda": TokenType.LAMBDA, "yield": TokenType.YIELD,
    "if": TokenType.IF, "elif": TokenType.ELIF, "else": TokenType.ELSE,
    "match": TokenType.MATCH, "case": TokenType.CASE,
    "while": TokenType.WHILE, "for": TokenType.FOR, "in": TokenType.IN,
    "break": TokenType.BREAK, "continue": TokenType.CONTINUE, "pass": TokenType.PASS,
    "and": TokenType.AND, "or": TokenType.OR, "not": TokenType.NOT, "is": TokenType.IS,
    "import": TokenType.IMPORT, "from": TokenType.FROM, "as": TokenType.AS,
    "class": TokenType.CLASS, "global": TokenType.GLOBAL,
    "nonlocal": TokenType.NONLOCAL, "del": TokenType.DEL,
    "try": TokenType.TRY, "except": TokenType.EXCEPT, "finally": TokenType.FINALLY,
    "raise": TokenType.RAISE, "assert": TokenType.ASSERT, "with": TokenType.WITH,
    "async": TokenType.ASYNC, "await": TokenType.AWAIT,
}

# Ordenados del más largo al más corto: el scanner debe probar en este
# orden para quedarse con la coincidencia más larga ("**=" antes que "**" y "*")
OPERADORES = {
    # 3 caracteres
    "**=": TokenType.POWER_ASSIGN, "//=": TokenType.FLOOR_DIVIDE_ASSIGN,
    "<<=": TokenType.LEFT_SHIFT_ASSIGN, ">>=": TokenType.RIGHT_SHIFT_ASSIGN,
    "...": TokenType.ELLIPSIS,
    # 2 caracteres
    "**": TokenType.POWER, "//": TokenType.FLOOR_DIVIDE,
    "==": TokenType.EQUAL, "!=": TokenType.NOT_EQUAL,
    "<=": TokenType.LESS_EQUAL, ">=": TokenType.GREATER_EQUAL,
    "<<": TokenType.LEFT_SHIFT, ">>": TokenType.RIGHT_SHIFT,
    "+=": TokenType.PLUS_ASSIGN, "-=": TokenType.MINUS_ASSIGN,
    "*=": TokenType.MULTIPLY_ASSIGN, "/=": TokenType.DIVIDE_ASSIGN,
    "%=": TokenType.MODULO_ASSIGN, "&=": TokenType.BIT_AND_ASSIGN,
    "|=": TokenType.BIT_OR_ASSIGN, "^=": TokenType.BIT_XOR_ASSIGN,
    "@=": TokenType.MATMUL_ASSIGN, ":=": TokenType.WALRUS,
    "->": TokenType.ARROW,
    # 1 caracter
    "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.MULTIPLY,
    "/": TokenType.DIVIDE, "%": TokenType.MODULO,
    "<": TokenType.LESS_THAN, ">": TokenType.GREATER_THAN, "=": TokenType.ASSIGN,
    "&": TokenType.BIT_AND, "|": TokenType.BIT_OR, "^": TokenType.BIT_XOR,
    "~": TokenType.BIT_NOT,
    "(": TokenType.LPAREN, ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
    "{": TokenType.LBRACE, "}": TokenType.RBRACE,
    ",": TokenType.COMMA, ".": TokenType.DOT, ":": TokenType.COLON,
    ";": TokenType.SEMICOLON, "@": TokenType.AT,
    "\\": TokenType.LINE_CONTINUATION,
}


def _nombre_python(miembro: TokenType, prefijo: str) -> str:
    """BUILTIN_IS_INSTANCE -> 'isinstance', EXC_VALUE_ERROR -> 'ValueError'."""
    base = miembro.name[len(prefijo):]
    if prefijo == "EXC_":
        return "".join(p.capitalize() for p in base.split("_"))
    return base.lower()


# print -> BUILTIN_PRINT, len -> BUILTIN_LEN, ...
FUNCIONES_INTEGRADAS = {
    _nombre_python(t, "BUILTIN_"): t for t in TokenType if t.name.startswith("BUILTIN_")
}

# ValueError -> EXC_VALUE_ERROR, ...
EXCEPCIONES_INTEGRADAS = {
    _nombre_python(t, "EXC_"): t for t in TokenType if t.name.startswith("EXC_")
}
EXCEPCIONES_INTEGRADAS["OSError"] = EXCEPCIONES_INTEGRADAS.pop("OsError")
EXCEPCIONES_INTEGRADAS["EOFError"] = EXCEPCIONES_INTEGRADAS.pop("EofError")

# math -> MODULE_MATH, ...
MODULOS_SOPORTADOS = {
    _nombre_python(t, "MODULE_"): t for t in TokenType if t.name.startswith("MODULE_")
}


# ======================================================================
# Categorías (las usa Token.py)
# ======================================================================

ESPECIALES = frozenset({
    TokenType.EOF, TokenType.NEWLINE, TokenType.NL, TokenType.INDENT,
    TokenType.DEDENT, TokenType.COMMENT, TokenType.LINE_CONTINUATION,
})
IDENTIFICADORES = frozenset({TokenType.IDENTIFIER, TokenType.DUNDER_NAME})
NUMERICOS = frozenset({
    TokenType.INTEGER, TokenType.FLOAT, TokenType.SCIENTIFIC,
    TokenType.HEX_INTEGER, TokenType.OCTAL_INTEGER,
    TokenType.BINARY_INTEGER, TokenType.IMAGINARY,
})
ENTEROS = frozenset({
    TokenType.INTEGER, TokenType.HEX_INTEGER,
    TokenType.OCTAL_INTEGER, TokenType.BINARY_INTEGER,
})
CADENAS = frozenset({
    TokenType.STRING, TokenType.TRIPLE_STRING, TokenType.RAW_STRING,
    TokenType.BYTES, TokenType.RAW_BYTES, TokenType.F_STRING_START,
    TokenType.F_STRING_MIDDLE, TokenType.F_STRING_END,
})
CONSTANTES = frozenset({TokenType.TRUE, TokenType.FALSE, TokenType.NONE})
LITERALES = NUMERICOS | CADENAS | CONSTANTES

PALABRAS_CLAVE = frozenset(PALABRAS_RESERVADAS.values()) - CONSTANTES
ESTRUCTURAS_CONTROL = frozenset({
    TokenType.IF, TokenType.ELIF, TokenType.ELSE, TokenType.MATCH,
    TokenType.CASE, TokenType.WHILE, TokenType.FOR, TokenType.IN,
    TokenType.BREAK, TokenType.CONTINUE, TokenType.PASS,
})

OPERADORES_ARITMETICOS = frozenset({
    TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY, TokenType.DIVIDE,
    TokenType.FLOOR_DIVIDE, TokenType.MODULO, TokenType.POWER,
})
OPERADORES_COMPARACION = frozenset({
    TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LESS_THAN,
    TokenType.GREATER_THAN, TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL,
    TokenType.IS, TokenType.IN,
})
OPERADORES_ASIGNACION = frozenset({
    TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
    TokenType.MULTIPLY_ASSIGN, TokenType.DIVIDE_ASSIGN,
    TokenType.FLOOR_DIVIDE_ASSIGN, TokenType.MODULO_ASSIGN,
    TokenType.POWER_ASSIGN, TokenType.BIT_AND_ASSIGN, TokenType.BIT_OR_ASSIGN,
    TokenType.BIT_XOR_ASSIGN, TokenType.LEFT_SHIFT_ASSIGN,
    TokenType.RIGHT_SHIFT_ASSIGN, TokenType.MATMUL_ASSIGN, TokenType.WALRUS,
})
OPERADORES_LOGICOS = frozenset({TokenType.AND, TokenType.OR, TokenType.NOT})
OPERADORES_BITS = frozenset({
    TokenType.BIT_AND, TokenType.BIT_OR, TokenType.BIT_XOR,
    TokenType.BIT_NOT, TokenType.LEFT_SHIFT, TokenType.RIGHT_SHIFT,
})
OPERADORES_TODOS = (OPERADORES_ARITMETICOS | OPERADORES_COMPARACION
                    | OPERADORES_ASIGNACION | OPERADORES_LOGICOS | OPERADORES_BITS)

AGRUPACION = frozenset({
    TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACKET,
    TokenType.RBRACKET, TokenType.LBRACE, TokenType.RBRACE,
})
APERTURA = {TokenType.LPAREN: TokenType.RPAREN,
            TokenType.LBRACKET: TokenType.RBRACKET,
            TokenType.LBRACE: TokenType.RBRACE}
PUNTUACION = frozenset({
    TokenType.COMMA, TokenType.DOT, TokenType.COLON, TokenType.SEMICOLON,
    TokenType.ARROW, TokenType.AT, TokenType.ELLIPSIS,
})

BUILTINS = frozenset(FUNCIONES_INTEGRADAS.values())
EXCEPCIONES = frozenset(EXCEPCIONES_INTEGRADAS.values())
MODULOS = frozenset(MODULOS_SOPORTADOS.values())

ERRORES = frozenset({
    TokenType.UNKNOWN, TokenType.INVALID_CHARACTER, TokenType.INVALID_NUMBER,
    TokenType.INVALID_IDENTIFIER, TokenType.LEADING_ZERO_NUMBER,
    TokenType.INVALID_UNDERSCORE_NUMBER, TokenType.UNTERMINATED_STRING,
    TokenType.UNTERMINATED_TRIPLE_STRING, TokenType.INVALID_ESCAPE,
    TokenType.INVALID_INDENTATION, TokenType.MIXED_TABS_SPACES,
    TokenType.UNMATCHED_BRACKET, TokenType.UNCLOSED_BRACKET,
})
