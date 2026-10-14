"""
ELYirs - Traductor de Python a Ensamblador
Programación de Sistemas de Base 1 - Grupo K

Scanner.py
Analizador léxico: convierte el código fuente (texto) en una lista de Tokens.

Uso básico:
    from Scanner import Scanner
    scanner = Scanner(codigo_fuente)
    tokens = scanner.tokenize()
"""

from typing import List, Optional

from Token import Token
from TokenTypes import (
    TokenType,
    PALABRAS_RESERVADAS, OPERADORES,
    FUNCIONES_INTEGRADAS, EXCEPCIONES_INTEGRADAS, MODULOS_SOPORTADOS,
)

# Operadores agrupados por longitud (de mayor a menor) para "maximal munch"
_OPERADORES_3 = {k: v for k, v in OPERADORES.items() if len(k) == 3}
_OPERADORES_2 = {k: v for k, v in OPERADORES.items() if len(k) == 2}
_OPERADORES_1 = {k: v for k, v in OPERADORES.items() if len(k) == 1}

_APERTURAS = {"(": TokenType.LPAREN, "[": TokenType.LBRACKET, "{": TokenType.LBRACE}
_CIERRES = {")": TokenType.RPAREN, "]": TokenType.RBRACKET, "}": TokenType.RBRACE}
_PAREJA = {"(": ")", "[": "]", "{": "}"}

_ESCAPES_VALIDOS = set("\\'\"abfnrtv0xNuU\n")


class LexerError(Exception):
    """Uso interno para abortar la lectura de un literal (string/número) a medio camino."""
    pass


class Scanner:
    def __init__(self, source: str):
        # Normalizamos separadores de línea
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.length = len(self.source)
        self.pos = 0
        self.linea = 1
        self.columna = 1

        self.tokens: List[Token] = []
        self.indent_stack = [0]          # pila de niveles de sangría
        self.paren_stack: List[str] = [] # pila de agrupadores abiertos: '(' '[' '{'
        self.at_line_start = True        # ¿estamos al inicio de una línea lógica?
        self.errores: List[Token] = []   # acceso rápido a todos los tokens de error

    # ==========================================
    # Utilidades de bajo nivel
    # ==========================================
    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.source[i] if i < self.length else ""

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.linea += 1
            self.columna = 1
        else:
            self.columna += 1
        return ch

    def _match(self, texto: str) -> bool:
        if self.source.startswith(texto, self.pos):
            for _ in texto:
                self._advance()
            return True
        return False

    def _emit(self, tipo: TokenType, valor, linea: int, columna: int, posicion: int, lexema: str) -> None:
        tok = Token(type=tipo, value=valor, linea=linea, columna=columna,
                    posicion=posicion, lexema=lexema)
        self.tokens.append(tok)
        if tok.is_error():
            self.errores.append(tok)

    # ==========================================
    # Punto de entrada
    # ==========================================
    def tokenize(self) -> List[Token]:
        while self.pos < self.length:
            if self.at_line_start and not self.paren_stack:
                if not self._procesar_indentacion():
                    continue  # línea en blanco o solo comentario: ya se manejó
            self.at_line_start = False
            self._escanear_token()

        self._cerrar_archivo()
        return self.tokens

    # ==========================================
    # Indentación
    # ==========================================
    def _procesar_indentacion(self) -> bool:
        """Mide la sangría de una nueva línea lógica y emite INDENT/DEDENT.
        Devuelve False si la línea era blanca o solo comentario (ya consumida)."""
        inicio_linea = self.pos
        linea_actual = self.linea
        espacios = 0
        tabs = 0
        while self._peek() in (" ", "\t"):
            if self._peek() == "\t":
                tabs += 1
                espacios += 8 - (espacios % 8)  # tabulación -> múltiplo de 8
            else:
                espacios += 1
            self._advance()

        c = self._peek()

        # Línea en blanco (solo salto de línea) -> no afecta indentación
        if c == "\n":
            self._advance()
            self._emit(TokenType.NL, "\n", linea_actual, 1, inicio_linea, "\n")
            return False

        # Línea con solo comentario -> tampoco afecta indentación
        if c == "#":
            self._leer_comentario()
            if self._peek() == "\n":
                self._advance()
            self._emit(TokenType.NL, "\n", linea_actual, 1, inicio_linea, "\n")
            return False

        # Fin de archivo tras espacios en blanco
        if c == "":
            return False

        if espacios and tabs and " " in self.source[inicio_linea:self.pos] and tabs:
            # mezcla de tabs y espacios en la misma sangría
            self._emit(TokenType.MIXED_TABS_SPACES, self.source[inicio_linea:self.pos],
                        linea_actual, 1, inicio_linea, self.source[inicio_linea:self.pos])

        nivel_previo = self.indent_stack[-1]
        if espacios > nivel_previo:
            self.indent_stack.append(espacios)
            self._emit(TokenType.INDENT, espacios, linea_actual, 1, inicio_linea,
                       self.source[inicio_linea:self.pos])
        elif espacios < nivel_previo:
            while self.indent_stack and self.indent_stack[-1] > espacios:
                self.indent_stack.pop()
                self._emit(TokenType.DEDENT, espacios, linea_actual, self.columna,
                           self.pos, "")
            if not self.indent_stack or self.indent_stack[-1] != espacios:
                self._emit(TokenType.INVALID_INDENTATION, espacios, linea_actual, 1,
                           inicio_linea, self.source[inicio_linea:self.pos])
                self.indent_stack.append(espacios)
        return True

    # ==========================================
    # Despachador principal de tokens
    # ==========================================
    def _escanear_token(self) -> None:
        c = self._peek()

        if c == "":
            return

        if c == "\n":
            self._leer_fin_de_linea()
            return

        if c in (" ", "\t"):
            self._advance()
            return

        if c == "\\" and self._peek(1) == "\n":
            inicio = self.pos
            linea, col = self.linea, self.columna
            self._advance()
            self._advance()
            self._emit(TokenType.LINE_CONTINUATION, "\\\n", linea, col, inicio, "\\\n")
            return

        if c == "#":
            self._leer_comentario()
            return

        if c.isdigit() or (c == "." and self._peek(1).isdigit()):
            self._leer_numero()
            return

        if c.isalpha() or c == "_":
            self._leer_identificador_o_cadena_con_prefijo()
            return

        if c in ("'", '"'):
            self._leer_cadena(prefijo="")
            return

        if c in _APERTURAS:
            self._leer_apertura(c)
            return

        if c in _CIERRES:
            self._leer_cierre(c)
            return

        if self._leer_operador():
            return

        # Carácter no reconocido
        inicio = self.pos
        linea, col = self.linea, self.columna
        ch = self._advance()
        self._emit(TokenType.INVALID_CHARACTER, ch, linea, col, inicio, ch)

    def _leer_fin_de_linea(self) -> None:
        inicio = self.pos
        linea, col = self.linea, self.columna
        self._advance()  # consume '\n'
        if self.paren_stack:
            # dentro de (), [] o {}: el salto de línea no termina la instrucción
            self._emit(TokenType.NL, "\n", linea, col, inicio, "\n")
        else:
            self._emit(TokenType.NEWLINE, "\n", linea, col, inicio, "\n")
            self.at_line_start = True

    def _leer_comentario(self) -> None:
        inicio = self.pos
        linea, col = self.linea, self.columna
        texto = []
        while self._peek() not in ("\n", ""):
            texto.append(self._advance())
        lexema = "".join(texto)
        self._emit(TokenType.COMMENT, lexema, linea, col, inicio, lexema)

    # ==========================================
    # Agrupadores
    # ==========================================
    def _leer_apertura(self, c: str) -> None:
        inicio = self.pos
        linea, col = self.linea, self.columna
        self._advance()
        self.paren_stack.append(c)
        self._emit(_APERTURAS[c], c, linea, col, inicio, c)

    def _leer_cierre(self, c: str) -> None:
        inicio = self.pos
        linea, col = self.linea, self.columna
        self._advance()
        if self.paren_stack and _PAREJA[self.paren_stack[-1]] == c:
            self.paren_stack.pop()
            self._emit(_CIERRES[c], c, linea, col, inicio, c)
        else:
            self._emit(TokenType.UNMATCHED_BRACKET, c, linea, col, inicio, c)

    # ==========================================
    # Operadores y puntuación
    # ==========================================
    def _leer_operador(self) -> bool:
        linea, col, inicio = self.linea, self.columna, self.pos
        for tabla in (_OPERADORES_3, _OPERADORES_2, _OPERADORES_1):
            for texto, tipo in tabla.items():
                if self.source.startswith(texto, self.pos):
                    for _ in texto:
                        self._advance()
                    self._emit(tipo, texto, linea, col, inicio, texto)
                    return True
        return False

    # ==========================================
    # Identificadores / palabras reservadas / prefijos de cadena
    # ==========================================
    def _leer_identificador_o_cadena_con_prefijo(self) -> None:
        inicio = self.pos
        linea, col = self.linea, self.columna
        letras = []
        while self._peek().isalnum() or self._peek() == "_":
            letras.append(self._advance())
        lexema = "".join(letras)

        # ¿Es un prefijo de cadena? (r, b, f, rb, br, rf, fr, y sus mayúsculas)
        prefijo_normalizado = lexema.lower()
        if prefijo_normalizado in ("r", "b", "f", "rb", "br", "rf", "fr") \
                and self._peek() in ("'", '"'):
            self._leer_cadena(prefijo=prefijo_normalizado, lexema_prefijo=lexema,
                               linea=linea, col=col, inicio=inicio)
            return

        # Identificador inválido: número pegado justo antes ya se maneja en _leer_numero;
        # aquí cubrimos identificadores que arrancan con letra (siempre válidos en Python).
        self._clasificar_identificador(lexema, linea, col, inicio)

    def _clasificar_identificador(self, lexema: str, linea: int, col: int, inicio: int) -> None:
        if lexema in PALABRAS_RESERVADAS:
            self._emit(PALABRAS_RESERVADAS[lexema], lexema, linea, col, inicio, lexema)
        elif lexema.startswith("__") and lexema.endswith("__") and len(lexema) > 4:
            self._emit(TokenType.DUNDER_NAME, lexema, linea, col, inicio, lexema)
        elif lexema in FUNCIONES_INTEGRADAS:
            self._emit(FUNCIONES_INTEGRADAS[lexema], lexema, linea, col, inicio, lexema)
        elif lexema in EXCEPCIONES_INTEGRADAS:
            self._emit(EXCEPCIONES_INTEGRADAS[lexema], lexema, linea, col, inicio, lexema)
        elif lexema in MODULOS_SOPORTADOS:
            self._emit(MODULOS_SOPORTADOS[lexema], lexema, linea, col, inicio, lexema)
        else:
            self._emit(TokenType.IDENTIFIER, lexema, linea, col, inicio, lexema)

    # ==========================================
    # Números
    # ==========================================
    def _leer_numero(self) -> None:
        inicio = self.pos
        linea, col = self.linea, self.columna
        digitos = []

        def leer_digitos(valido) -> None:
            while valido(self._peek()) or self._peek() == "_":
                digitos.append(self._advance())

        # Bases especiales: 0x, 0o, 0b
        if self._peek() == "0" and self._peek(1) in ("x", "X", "o", "O", "b", "B"):
            digitos.append(self._advance())          # '0'
            marcador = self._advance().lower()        # 'x' | 'o' | 'b'
            digitos.append(marcador)
            validador = {
                "x": lambda ch: ch and ch in "0123456789abcdefABCDEF",
                "o": lambda ch: ch and ch in "01234567",
                "b": lambda ch: ch and ch in "01",
            }[marcador]
            inicio_digitos = len(digitos)
            leer_digitos(validador)
            lexema = "".join(digitos)
            cuerpo = lexema[inicio_digitos:]
            if not cuerpo.replace("_", ""):
                extra = []
                while self._peek().isalnum() or self._peek() == "_":
                    extra.append(self._advance())
                lexema_completo = lexema + "".join(extra)
                self._emit(TokenType.INVALID_NUMBER, lexema_completo, linea, col, inicio,
                            lexema_completo)
                return
            if "__" in cuerpo or cuerpo.startswith("_") or cuerpo.endswith("_"):
                self._emit(TokenType.INVALID_UNDERSCORE_NUMBER, lexema, linea, col, inicio, lexema)
                return
            # ¿siguen caracteres alfanuméricos inválidos pegados? -> número inválido
            if self._peek().isalnum() or self._peek() == "_":
                extra = []
                while self._peek().isalnum() or self._peek() == "_":
                    extra.append(self._advance())
                self._emit(TokenType.INVALID_NUMBER, lexema + "".join(extra), linea, col,
                            inicio, lexema + "".join(extra))
                return
            base = {"x": 16, "o": 8, "b": 2}[marcador]
            valor = int(cuerpo.replace("_", ""), base)
            tipo = {"x": TokenType.HEX_INTEGER, "o": TokenType.OCTAL_INTEGER,
                    "b": TokenType.BINARY_INTEGER}[marcador]
            self._emit(tipo, valor, linea, col, inicio, lexema)
            return

        # Parte entera
        leer_digitos(lambda ch: ch.isdigit())
        es_flotante = False
        es_cientifico = False
        puntos_extra = False

        if self._peek() == "." and self._peek(1) != ".":
            es_flotante = True
            digitos.append(self._advance())
            leer_digitos(lambda ch: ch.isdigit())
            # segundo punto decimal -> número inválido (12.3.4)
            if self._peek() == "." and self._peek(1).isdigit():
                puntos_extra = True
                while self._peek() == "." or self._peek().isdigit() or self._peek() == "_":
                    digitos.append(self._advance())

        if self._peek() in ("e", "E") and (self._peek(1).isdigit()
                                            or (self._peek(1) in ("+", "-") and self._peek(2).isdigit())):
            es_cientifico = True
            digitos.append(self._advance())
            if self._peek() in ("+", "-"):
                digitos.append(self._advance())
            leer_digitos(lambda ch: ch.isdigit())

        es_imaginario = False
        if self._peek() in ("j", "J"):
            es_imaginario = True
            digitos.append(self._advance())

        lexema = "".join(digitos)
        cuerpo_numerico = lexema[:-1] if es_imaginario else lexema

        # Caracteres inválidos pegados justo después (p.ej. "2variable")
        if self._peek().isalpha() or self._peek() == "_":
            extra = []
            while self._peek().isalnum() or self._peek() == "_":
                extra.append(self._advance())
            self._emit(TokenType.INVALID_IDENTIFIER, lexema + "".join(extra), linea, col,
                        inicio, lexema + "".join(extra))
            return

        if puntos_extra:
            self._emit(TokenType.INVALID_NUMBER, lexema, linea, col, inicio, lexema)
            return

        cuerpo_sin_signo_exp = cuerpo_numerico
        if "__" in cuerpo_sin_signo_exp or cuerpo_sin_signo_exp.startswith("_") \
                or cuerpo_sin_signo_exp.endswith("_") or "_." in cuerpo_sin_signo_exp \
                or "._" in cuerpo_sin_signo_exp:
            self._emit(TokenType.INVALID_UNDERSCORE_NUMBER, lexema, linea, col, inicio, lexema)
            return

        # Cero a la izquierda: "007" (pero no "0", "0.5", "0x.." ya filtrado arriba)
        limpio = cuerpo_numerico.replace("_", "")
        if (not es_flotante and not es_cientifico and len(limpio) > 1
                and limpio[0] == "0"):
            self._emit(TokenType.LEADING_ZERO_NUMBER, lexema, linea, col, inicio, lexema)
            return

        valor_txt = limpio
        try:
            if es_imaginario:
                valor = complex(0, float(valor_txt))
                tipo = TokenType.IMAGINARY
            elif es_cientifico:
                valor = float(valor_txt)
                tipo = TokenType.SCIENTIFIC
            elif es_flotante:
                valor = float(valor_txt)
                tipo = TokenType.FLOAT
            else:
                valor = int(valor_txt)
                tipo = TokenType.INTEGER
        except ValueError:
            self._emit(TokenType.INVALID_NUMBER, lexema, linea, col, inicio, lexema)
            return

        self._emit(tipo, valor, linea, col, inicio, lexema)

    # ==========================================
    # Cadenas (incluye raw, bytes, triple y f-strings)
    # ==========================================
    def _leer_cadena(self, prefijo: str, lexema_prefijo: str = "",
                      linea: Optional[int] = None, col: Optional[int] = None,
                      inicio: Optional[int] = None) -> None:
        if linea is None:
            linea, col, inicio = self.linea, self.columna, self.pos

        comilla = self._peek()
        es_triple = self.source.startswith(comilla * 3, self.pos)
        n_comillas = 3 if es_triple else 1
        for _ in range(n_comillas):
            self._advance()

        es_raw = "r" in prefijo
        es_bytes = "b" in prefijo
        es_f = "f" in prefijo

        if es_f:
            self._leer_fstring(comilla, n_comillas, es_raw, lexema_prefijo, linea, col, inicio)
            return

        contenido = []
        cerrada = False
        while self.pos < self.length:
            if not es_triple and self._peek() == "\n":
                break
            if self.source.startswith(comilla * n_comillas, self.pos):
                for _ in range(n_comillas):
                    self._advance()
                cerrada = True
                break
            if self._peek() == "\\" and not es_raw:
                contenido.append(self._advance())
                if self._peek() != "":
                    escape = self._advance()
                    contenido.append(escape)
                    if escape not in _ESCAPES_VALIDOS and not escape.isdigit():
                        pos_err = self.pos - 2
                        self._emit(TokenType.INVALID_ESCAPE, "\\" + escape, self.linea,
                                    self.columna - 2, pos_err, "\\" + escape)
                continue
            if self._peek() == "\\" and es_raw:
                contenido.append(self._advance())
                if self._peek() != "":
                    contenido.append(self._advance())
                continue
            contenido.append(self._advance())

        lexema_completo = self.source[inicio:self.pos]
        if not cerrada:
            tipo_error = TokenType.UNTERMINATED_TRIPLE_STRING if es_triple else TokenType.UNTERMINATED_STRING
            self._emit(tipo_error, lexema_completo, linea, col , inicio, lexema_completo)
            return

        valor = "".join(contenido)
        if es_bytes:
            tipo = TokenType.RAW_BYTES if es_raw else TokenType.BYTES
        elif es_triple:
            tipo = TokenType.TRIPLE_STRING
        elif es_raw:
            tipo = TokenType.RAW_STRING
        else:
            tipo = TokenType.STRING
        self._emit(tipo, valor, linea, col, inicio, lexema_completo)

    def _leer_fstring(self, comilla: str, n_comillas: int, es_raw: bool, lexema_prefijo: str,
                       linea: int, col: int, inicio: int) -> None:
        """Versión simplificada: START (prefijo+comillas) / MIDDLE (contenido crudo,
        con las expresiones {..} incluidas tal cual) / END (comillas de cierre)."""
        marca_inicio = lexema_prefijo + comilla * n_comillas
        self._emit(TokenType.F_STRING_START, marca_inicio, linea, col, inicio, marca_inicio)

        inicio_medio = self.pos
        linea_medio, col_medio = self.linea, self.columna
        contenido = []
        cerrada = False
        profundidad_llaves = 0
        while self.pos < self.length:
            if profundidad_llaves == 0 and self.source.startswith(comilla * n_comillas, self.pos):
                cerrada = True
                break
            if n_comillas == 1 and self._peek() == "\n":
                break
            if self._peek() == "{" and self._peek(1) != "{":
                profundidad_llaves += 1
                contenido.append(self._advance())
                continue
            if self._peek() == "}" and profundidad_llaves > 0:
                profundidad_llaves -= 1
                contenido.append(self._advance())
                continue
            if self._peek() == "\\" and not es_raw and self._peek() != "":
                contenido.append(self._advance())
                if self._peek() != "":
                    contenido.append(self._advance())
                continue
            contenido.append(self._advance())

        valor = "".join(contenido)
        if valor:
            self._emit(TokenType.F_STRING_MIDDLE, valor, linea_medio, col_medio, inicio_medio, valor)

        if not cerrada:
            self._emit(TokenType.UNTERMINATED_STRING, self.source[inicio:self.pos],
                        linea, col, inicio, self.source[inicio:self.pos])
            return

        pos_fin = self.pos
        linea_fin, col_fin = self.linea, self.columna
        for _ in range(n_comillas):
            self._advance()
        marca_fin = comilla * n_comillas
        self._emit(TokenType.F_STRING_END, marca_fin, linea_fin, col_fin, pos_fin, marca_fin)

    # ==========================================
    # Cierre del archivo
    # ==========================================
    def _cerrar_archivo(self) -> None:
        # Si el archivo no terminó con salto de línea pero hubo contenido, cerramos la instrucción
        if self.tokens and not self.tokens[-1].is_any(TokenType.NEWLINE, TokenType.NL,
                                                        TokenType.INDENT, TokenType.DEDENT):
            self._emit(TokenType.NEWLINE, "\n", self.linea, self.columna, self.pos, "")

        # Agrupadores sin cerrar
        for simbolo in reversed(self.paren_stack):
            self._emit(TokenType.UNCLOSED_BRACKET, simbolo, self.linea, self.columna, self.pos, simbolo)
        self.paren_stack.clear()

        # DEDENT finales hasta nivel 0
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self._emit(TokenType.DEDENT, self.indent_stack[-1] if self.indent_stack else 0,
                        self.linea, self.columna, self.pos, "")

        self._emit(TokenType.EOF, None, self.linea, self.columna, self.pos, "")


def tokenize(source: str) -> List[Token]:
    """Función de conveniencia: tokeniza un string y devuelve la lista de Tokens."""
    return Scanner(source).tokenize()
