"""
ELYirs - Traductor de Python a Ensamblador
Programación de Sistemas de Base 1 - Grupo K

Token.py (versión 2, compatible con TokenTypes v2)
Representa un componente léxico (token) encontrado por el scanner.
"""

from dataclasses import dataclass
from typing import Any, Dict

from TokenTypes import (
    TokenType,
    ESPECIALES, IDENTIFICADORES, NUMERICOS, ENTEROS, CADENAS, CONSTANTES,
    LITERALES, PALABRAS_CLAVE, ESTRUCTURAS_CONTROL,
    OPERADORES_ARITMETICOS, OPERADORES_COMPARACION, OPERADORES_ASIGNACION,
    OPERADORES_LOGICOS, OPERADORES_BITS, OPERADORES_TODOS,
    AGRUPACION, APERTURA, PUNTUACION,
    BUILTINS, EXCEPCIONES, MODULOS, ERRORES,
)


@dataclass
class Token:
    type: TokenType
    value: Any          # valor ya convertido: "0xFF" -> 255, "15.50" -> 15.5
    linea: int
    columna: int = 1
    posicion: int = 0   # índice del primer carácter dentro del código fuente
    lexema: str = ""    # texto tal cual aparece en el código

    def __post_init__(self):
        if not self.lexema and self.value is not None:
            self.lexema = str(self.value)

    # ==========================================
    # Representación
    # ==========================================
    def __str__(self) -> str:
        return (f"Token({self.type.name}, {self.value!r}, "
                f"linea={self.linea}, col={self.columna})")

    def __repr__(self) -> str:
        return (f"Token(type={self.type}, value={self.value!r}, "
                f"linea={self.linea}, columna={self.columna}, "
                f"posicion={self.posicion}, lexema={self.lexema!r})")

    def __eq__(self, other) -> bool:
        if not isinstance(other, Token):
            return False
        return self.type == other.type and self.value == other.value

    def __hash__(self) -> int:
        return hash((self.type, self.value))

    def to_dict(self) -> Dict[str, Any]:
        """Para el reporte de tokens."""
        return {
            "tipo": self.type.name,
            "categoria": self.categoria(),
            "valor": self.value,
            "lexema": self.lexema,
            "linea": self.linea,
            "columna": self.columna,
            "posicion": self.posicion,
        }

    def categoria(self) -> str:
        """Nombre de la categoría del token, para reportes y mensajes de error."""
        if self.is_error():               return "ERROR"
        if self.is_special():             return "ESPECIAL"
        if self.is_identifier():          return "IDENTIFICADOR"
        if self.is_numeric():             return "NUMERO"
        if self.is_string():              return "CADENA"
        if self.is_constant():            return "CONSTANTE"
        if self.is_logical_operator():    return "OPERADOR_LOGICO"
        if self.is_keyword():             return "PALABRA_RESERVADA"
        if self.is_arithmetic_operator(): return "OPERADOR_ARITMETICO"
        if self.is_comparison_operator(): return "OPERADOR_COMPARACION"
        if self.is_assignment_operator(): return "OPERADOR_ASIGNACION"
        if self.is_bitwise_operator():    return "OPERADOR_BITS"
        if self.is_grouping():            return "AGRUPACION"
        if self.is_punctuation():         return "PUNTUACION"
        if self.is_builtin():             return "FUNCION_INTEGRADA"
        if self.is_exception():           return "EXCEPCION"
        if self.is_module():              return "MODULO"
        return "DESCONOCIDO"

    # ==========================================
    # Métodos generales
    # ==========================================
    # token.is_type(TokenType.INTEGER)
    def is_type(self, token_type: TokenType) -> bool:
        return self.type == token_type

    # token.has_value("main")
    def has_value(self, expected_value: Any) -> bool:
        return self.value == expected_value

    # token.matches(TokenType.IDENTIFIER, "main")
    def matches(self, token_type: TokenType, value: Any = None) -> bool:
        if value is None:
            return self.is_type(token_type)
        return self.is_type(token_type) and self.has_value(value)

    # token.is_any(TokenType.PLUS, TokenType.MINUS)
    def is_any(self, *token_types: TokenType) -> bool:
        return self.type in token_types

    # ==========================================
    # Categorías
    # ==========================================
    def is_special(self) -> bool:
        return self.type in ESPECIALES

    def is_identifier(self) -> bool:
        return self.type in IDENTIFICADORES

    def is_literal(self) -> bool:
        return self.type in LITERALES

    def is_numeric(self) -> bool:
        return self.type in NUMERICOS

    def is_integer(self) -> bool:
        # enteros en cualquier base: 40, 0xFF, 0o17, 0b1010
        return self.type in ENTEROS

    def is_float(self) -> bool:
        return self.is_any(TokenType.FLOAT, TokenType.SCIENTIFIC)

    def is_string(self) -> bool:
        return self.type in CADENAS

    def is_fstring(self) -> bool:
        return self.is_any(TokenType.F_STRING_START,
                           TokenType.F_STRING_MIDDLE, TokenType.F_STRING_END)

    def is_constant(self) -> bool:
        return self.type in CONSTANTES

    def is_boolean(self) -> bool:
        return self.is_any(TokenType.TRUE, TokenType.FALSE)

    def is_keyword(self) -> bool:
        return self.type in PALABRAS_CLAVE

    def is_control_structure(self) -> bool:
        return self.type in ESTRUCTURAS_CONTROL

    def is_operator(self) -> bool:
        return self.type in OPERADORES_TODOS

    def is_arithmetic_operator(self) -> bool:
        return self.type in OPERADORES_ARITMETICOS

    def is_comparison_operator(self) -> bool:
        return self.type in OPERADORES_COMPARACION

    def is_assignment_operator(self) -> bool:
        return self.type in OPERADORES_ASIGNACION

    def is_compound_assignment(self) -> bool:
        # +=, -=, <<=, ... (todas menos "=" y ":=")
        return (self.is_assignment_operator()
                and not self.is_any(TokenType.ASSIGN, TokenType.WALRUS))

    def is_logical_operator(self) -> bool:
        return self.type in OPERADORES_LOGICOS

    def is_bitwise_operator(self) -> bool:
        return self.type in OPERADORES_BITS

    def is_grouping(self) -> bool:
        return self.type in AGRUPACION

    def is_opening(self) -> bool:
        return self.type in APERTURA

    def is_closing(self) -> bool:
        return self.type in APERTURA.values()

    def closes(self, apertura: "Token") -> bool:
        # token_rparen.closes(token_lparen) -> True
        return APERTURA.get(apertura.type) == self.type

    def is_punctuation(self) -> bool:
        return self.type in PUNTUACION

    def is_builtin(self) -> bool:
        return self.type in BUILTINS

    def is_exception(self) -> bool:
        return self.type in EXCEPCIONES

    def is_module(self) -> bool:
        return self.type in MODULOS

    def is_error(self) -> bool:
        return self.type in ERRORES

    # ==========================================
    # Estructura del código
    # ==========================================
    def is_newline(self) -> bool:
        return self.is_type(TokenType.NEWLINE)

    def is_indent(self) -> bool:
        return self.is_type(TokenType.INDENT)

    def is_dedent(self) -> bool:
        return self.is_type(TokenType.DEDENT)

    def is_comment(self) -> bool:
        return self.is_type(TokenType.COMMENT)

    def is_eof(self) -> bool:
        return self.is_type(TokenType.EOF)

    # ==========================================
    # Los más usados por el parser
    # ==========================================
    def is_def(self) -> bool:
        return self.is_type(TokenType.DEF)

    def is_return(self) -> bool:
        return self.is_type(TokenType.RETURN)

    def is_if(self) -> bool:
        return self.is_type(TokenType.IF)

    def is_elif(self) -> bool:
        return self.is_type(TokenType.ELIF)

    def is_else(self) -> bool:
        return self.is_type(TokenType.ELSE)

    def is_while(self) -> bool:
        return self.is_type(TokenType.WHILE)

    def is_for(self) -> bool:
        return self.is_type(TokenType.FOR)

    def is_assign(self) -> bool:
        return self.is_type(TokenType.ASSIGN)

    def is_colon(self) -> bool:
        return self.is_type(TokenType.COLON)

    def is_comma(self) -> bool:
        return self.is_type(TokenType.COMMA)

    def is_print(self) -> bool:
        return self.is_type(TokenType.BUILTIN_PRINT)

    def is_input(self) -> bool:
        return self.is_type(TokenType.BUILTIN_INPUT)

    def is_main_guard_name(self) -> bool:
        # detecta __name__ en:  if __name__ == "__main__":
        return self.matches(TokenType.DUNDER_NAME, "__name__")
