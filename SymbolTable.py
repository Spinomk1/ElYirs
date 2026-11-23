"""
ELYirs - Traductor de Python a Ensamblador
Programación de Sistemas de Base 1 - Grupo K

SymbolTable.py
Tabla de símbolos del compilador. Se divide en las cuatro secciones vistas en clase:

  1. Constantes universales      True, False, None, ..., __name__, math.pi ...
  2. Funciones estándar          print, len, range... + excepciones, módulos y
                                 funciones de módulos (math.sqrt ...)
  3. Palabras reservadas         def, if, while, for, return ...
  4. Identificadores del usuario variables, parámetros, funciones, clases...
                                 organizados por ÁMBITO (global > función > ...)

Las secciones 1-3 se cargan solas a partir de TokenTypes.py (si el equipo agrega
un token nuevo al enum, aparece aquí sin tocar nada). La sección 4 se llena
recorriendo la lista de tokens que produce el Scanner.

Además de registrar los símbolos, la tabla:
  - calcula la dirección que tendrá cada uno en ensamblador x86 de 32 bits
    (v_total para las globales, [ebp+8] para los parámetros, [ebp-4] para las
    locales) y el tamaño del marco de cada función;
  - verifica que cada llamada use un número válido de argumentos;
  - deja sus avisos en `advertencias` (texto) y en `incidencias`
    (línea, columna, mensaje) para que ErrorHandler.py los imprima junto con
    los errores léxicos.

Uso básico:
    from Scanner import Scanner
    from SymbolTable import TablaSimbolos

    tokens = Scanner(codigo).tokenize()
    tabla = TablaSimbolos()
    tabla.construir(tokens)
    tabla.imprimir()
    tabla.exportar_csv("tabla_simbolos.csv")

Línea de comandos:
    python SymbolTable.py mi_archivo.py                  # tabla + reporte de errores
    python SymbolTable.py mi_archivo.py --completa       # incluye predefinidos sin usar
    python SymbolTable.py mi_archivo.py --csv salida.csv
    python SymbolTable.py mi_archivo.py --sin-errores    # solo la tabla

Depende únicamente de Scanner.py, Token.py y TokenTypes.py. Si ErrorHandler.py
está en la carpeta, lo usa para imprimir el reporte de errores al final.
"""

import argparse
import csv
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple

from Scanner import Scanner
from Token import Token
try:                                   # opcional: solo para el reporte final
    from ErrorHandler import ErrorManager, FaseError
except ImportError:                    # si ErrorHandler.py no está, la tabla igual funciona
    ErrorManager = FaseError = None
from TokenTypes import (
    TokenType,
    PALABRAS_RESERVADAS, CONSTANTES,
    FUNCIONES_INTEGRADAS, EXCEPCIONES_INTEGRADAS, MODULOS_SOPORTADOS,
)


# ======================================================================
# Categorías y estructura de un símbolo
# ======================================================================
class Categoria(Enum):
    CONSTANTE_UNIVERSAL = "Constantes universales"
    FUNCION_ESTANDAR = "Funciones estándar"
    PALABRA_RESERVADA = "Palabras reservadas"
    IDENTIFICADOR_USUARIO = "Identificadores del usuario"


@dataclass
class Simbolo:
    lexema: str
    categoria: Categoria
    subtipo: str                       # ver SUBTIPOS más abajo
    tipo_dato: str = "desconocido"     # int, float, str, bool, list, funcion, clase, modulo...
    valor: Any = None                  # valor constante (si se conoce)
    ambito: str = "global"             # ruta del ámbito: global.calcular_salario
    linea_decl: int = 0
    columna_decl: int = 0
    token_type: str = ""               # nombre del TokenType asociado
    aridad: Optional[Tuple[int, Optional[int]]] = None   # (mínimo, máximo|None=ilimitado)
    retorno: Optional[str] = None      # tipo que devuelve (funciones)
    retorno_anotado: bool = False      # True si vino de una anotación "-> tipo"
    parametros: List[dict] = field(default_factory=list)
    lineas_uso: List[int] = field(default_factory=list)
    lineas_asig: List[int] = field(default_factory=list)
    info: str = ""                     # nota libre: grupo, herencia, etc.
    direccion: str = ""                # dónde vivirá en x86: v_total, [ebp+8], [ebp-4]
    tam_marco: int = 0                 # bytes de variables locales (solo funciones)

    @property
    def usos(self) -> int:
        return len(self.lineas_uso)

    def aridad_txt(self) -> str:
        if self.aridad is None:
            return ""
        mn, mx = self.aridad
        if mx is None:
            return f"{mn}..*"
        return str(mn) if mn == mx else f"{mn}..{mx}"


# subtipos usados:
#   constante universal : "literal", "dunder", "constante_modulo"
#   función estándar    : "funcion_integrada", "excepcion", "modulo", "funcion_modulo"
#   palabra reservada   : "palabra_reservada"
#   usuario             : "variable", "parametro", "funcion", "metodo", "clase",
#                         "modulo", "importado", "funcion_importada", "constante_importada"


class Ambito:
    """Un nivel de la tabla: el archivo (global), una función o una clase."""

    def __init__(self, nombre: str, tipo: str, padre: Optional["Ambito"] = None,
                 dueno: Optional[Simbolo] = None):
        self.nombre = nombre
        self.tipo = tipo                       # "global" | "funcion" | "clase"
        self.padre = padre
        self.dueno = dueno                     # símbolo de la función/clase que lo abre
        self.simbolos: Dict[str, Simbolo] = {}
        self.hijos: List["Ambito"] = []
        self.globales: set = set()             # nombres declarados con 'global'
        self.nolocales: set = set()            # nombres declarados con 'nonlocal'

    @property
    def ruta(self) -> str:
        return self.nombre if self.padre is None else f"{self.padre.ruta}.{self.nombre}"


# ======================================================================
# Datos de los símbolos predefinidos
# ======================================================================
# nombre -> (mínimo de argumentos, máximo (None = ilimitado), tipo que devuelve)
_INFO_BUILTINS: Dict[str, Tuple[int, Optional[int], str]] = {
    "print": (0, None, "NoneType"), "input": (0, 1, "str"), "open": (1, None, "file"),
    "int": (0, 2, "int"), "float": (0, 1, "float"), "str": (0, 3, "str"),
    "bool": (0, 1, "bool"), "complex": (0, 2, "complex"), "bytes": (0, 3, "bytes"),
    "bin": (1, 1, "str"), "hex": (1, 1, "str"), "oct": (1, 1, "str"),
    "chr": (1, 1, "str"), "ord": (1, 1, "int"),
    "list": (0, 1, "list"), "dict": (0, None, "dict"), "tuple": (0, 1, "tuple"),
    "set": (0, 1, "set"), "frozenset": (0, 1, "frozenset"),
    "range": (1, 3, "range"), "len": (1, 1, "int"),
    "abs": (1, 1, "number"), "round": (1, 2, "number"), "pow": (2, 3, "number"),
    "divmod": (2, 2, "tuple"), "min": (1, None, "any"), "max": (1, None, "any"),
    "sum": (1, 2, "number"),
    "enumerate": (1, 2, "enumerate"), "zip": (0, None, "zip"), "map": (2, None, "map"),
    "filter": (2, 2, "filter"), "sorted": (1, None, "list"), "reversed": (1, 1, "reversed"),
    "any": (1, 1, "bool"), "all": (1, 1, "bool"), "iter": (1, 2, "iterator"),
    "next": (1, 2, "any"),
    "type": (1, 3, "type"), "isinstance": (2, 2, "bool"), "id": (1, 1, "int"),
    "repr": (1, 1, "str"), "format": (1, 2, "str"), "super": (0, 2, "object"),
    "object": (0, 0, "object"), "hasattr": (2, 2, "bool"), "getattr": (2, 3, "any"),
    "setattr": (3, 3, "NoneType"),
}

# excepción -> clase de la que hereda (solo las que están en TokenTypes)
_EXC_PADRE: Dict[str, str] = {
    "ArithmeticError": "Exception", "ZeroDivisionError": "ArithmeticError",
    "OverflowError": "ArithmeticError", "ValueError": "Exception",
    "UnicodeDecodeError": "ValueError", "TypeError": "Exception",
    "NameError": "Exception", "IndexError": "Exception", "KeyError": "Exception",
    "AttributeError": "Exception", "OSError": "Exception",
    "FileNotFoundError": "OSError", "PermissionError": "OSError",
    "EOFError": "Exception", "RuntimeError": "Exception",
    "RecursionError": "RuntimeError", "NotImplementedError": "RuntimeError",
    "AssertionError": "Exception", "ImportError": "Exception",
    "StopIteration": "Exception", "MemoryError": "Exception",
    "KeyboardInterrupt": "BaseException", "Exception": "BaseException",
}

# Constantes de módulos soportados: nombre calificado -> (tipo, valor)
_CONSTANTES_MODULO: Dict[str, Tuple[str, Any]] = {
    "math.pi": ("float", math.pi), "math.e": ("float", math.e),
    "math.tau": ("float", math.tau), "math.inf": ("float", math.inf),
    "math.nan": ("float", math.nan),
}

# Funciones de módulos soportados: nombre calificado -> (mín, máx, retorno)
# (lista inicial; se amplía agregando líneas aquí)
_FUNCIONES_MODULO: Dict[str, Tuple[int, Optional[int], str]] = {
    "math.sqrt": (1, 1, "float"), "math.sin": (1, 1, "float"), "math.cos": (1, 1, "float"),
    "math.tan": (1, 1, "float"), "math.floor": (1, 1, "int"), "math.ceil": (1, 1, "int"),
    "math.log": (1, 2, "float"), "math.log10": (1, 1, "float"), "math.exp": (1, 1, "float"),
    "math.factorial": (1, 1, "int"), "math.fabs": (1, 1, "float"), "math.gcd": (0, None, "int"),
    "random.random": (0, 0, "float"), "random.randint": (2, 2, "int"),
    "random.choice": (1, 1, "any"), "random.shuffle": (1, 1, "NoneType"),
    "time.time": (0, 0, "float"), "time.sleep": (1, 1, "NoneType"),
}

# Grupos de palabras reservadas (los mismos comentarios de TokenTypes.py)
_GRUPOS_RESERVADAS: Dict[str, List[str]] = {
    "Funciones": ["DEF", "RETURN", "LAMBDA", "YIELD"],
    "Decisiones": ["IF", "ELIF", "ELSE", "MATCH", "CASE"],
    "Repeticiones": ["WHILE", "FOR", "IN", "BREAK", "CONTINUE", "PASS"],
    "Lógicos y de identidad": ["AND", "OR", "NOT", "IS"],
    "Módulos": ["IMPORT", "FROM", "AS"],
    "Clases y ámbitos": ["CLASS", "GLOBAL", "NONLOCAL", "DEL"],
    "Manejo de errores": ["TRY", "EXCEPT", "FINALLY", "RAISE", "ASSERT", "WITH"],
    "Asincronía": ["ASYNC", "AWAIT"],
}
_GRUPO_DE = {nombre: grupo for grupo, nombres in _GRUPOS_RESERVADAS.items() for nombre in nombres}

# Tipo de dato según el token literal
_TIPO_LITERAL = {
    TokenType.INTEGER: "int", TokenType.HEX_INTEGER: "int",
    TokenType.OCTAL_INTEGER: "int", TokenType.BINARY_INTEGER: "int",
    TokenType.FLOAT: "float", TokenType.SCIENTIFIC: "float",
    TokenType.IMAGINARY: "complex",
    TokenType.STRING: "str", TokenType.TRIPLE_STRING: "str", TokenType.RAW_STRING: "str",
    TokenType.BYTES: "bytes", TokenType.RAW_BYTES: "bytes",
    TokenType.TRUE: "bool", TokenType.FALSE: "bool", TokenType.NONE: "NoneType",
}
_COMPUESTAS = (TokenType.IF, TokenType.ELIF, TokenType.ELSE, TokenType.WHILE,
               TokenType.FOR, TokenType.TRY, TokenType.EXCEPT, TokenType.FINALLY,
               TokenType.WITH, TokenType.DEF, TokenType.CLASS)
_NUMERICOS = (TokenType.INTEGER, TokenType.HEX_INTEGER, TokenType.OCTAL_INTEGER,
              TokenType.BINARY_INTEGER, TokenType.FLOAT, TokenType.SCIENTIFIC,
              TokenType.IMAGINARY)


# ======================================================================
# La tabla
# ======================================================================
class TablaSimbolos:
    def __init__(self):
        self.predefinidos: Dict[str, Simbolo] = {}   # secciones 1, 2 y 3
        self.raiz = Ambito("global", "global")        # sección 4
        self.actual = self.raiz
        self.advertencias: List[str] = []

        self.incidencias: List[Tuple[int, int, str]] = []   # (línea, columna, mensaje)

        self._usos: List[Tuple[str, Ambito, int, int]] = []
        self._llamadas: List[Tuple[str, int, bool, int, int, Ambito]] = []
        self._pendiente: Optional[Tuple[str, str, Simbolo, List[dict]]] = None
        self._bloques: List[bool] = []

        self._cargar_predefinidos()

    # ------------------------------------------------------------------
    # Avisos
    # ------------------------------------------------------------------
    def _avisar(self, mensaje: str, linea: int = 0, columna: int = 1) -> None:
        """Registra un aviso en los dos formatos: texto para imprimir y
        (línea, columna, mensaje) para ErrorHandler.py."""
        prefijo = f"línea {linea}: " if linea else ""
        self.advertencias.append(prefijo + mensaje)
        self.incidencias.append((linea, columna, mensaje))

    # ------------------------------------------------------------------
    # Secciones 1-3: símbolos predefinidos
    # ------------------------------------------------------------------
    def _agregar(self, s: Simbolo) -> None:
        self.predefinidos[s.lexema] = s

    def _cargar_predefinidos(self) -> None:
        C, F, R = (Categoria.CONSTANTE_UNIVERSAL, Categoria.FUNCION_ESTANDAR,
                   Categoria.PALABRA_RESERVADA)

        # --- 1. Constantes universales ---
        valores = {"True": (True, "bool"), "False": (False, "bool"), "None": (None, "NoneType")}
        for lex, tt in PALABRAS_RESERVADAS.items():
            if tt in CONSTANTES:
                valor, tipo = valores[lex]
                self._agregar(Simbolo(lex, C, "literal", tipo, valor, token_type=tt.name))
        self._agregar(Simbolo("...", C, "literal", "ellipsis", token_type="ELLIPSIS",
                              info="Ellipsis"))
        self._agregar(Simbolo("__name__", C, "dunder", "str", token_type="DUNDER_NAME",
                              info="vale '__main__' si el archivo se ejecuta directamente"))
        for nombre, (tipo, valor) in _CONSTANTES_MODULO.items():
            self._agregar(Simbolo(nombre, C, "constante_modulo", tipo, valor,
                                  info=f"constante del módulo {nombre.split('.')[0]}"))

        # --- 2. Funciones estándar ---
        for nombre, tt in FUNCIONES_INTEGRADAS.items():
            mn, mx, ret = _INFO_BUILTINS.get(nombre, (0, None, "any"))
            self._agregar(Simbolo(nombre, F, "funcion_integrada", "funcion",
                                  token_type=tt.name, aridad=(mn, mx), retorno=ret))
        for nombre, tt in EXCEPCIONES_INTEGRADAS.items():
            padre = _EXC_PADRE.get(nombre, "Exception")
            self._agregar(Simbolo(nombre, F, "excepcion", "clase", token_type=tt.name,
                                  info=f"hereda de {padre}"))
        for nombre, tt in MODULOS_SOPORTADOS.items():
            self._agregar(Simbolo(nombre, F, "modulo", "modulo", token_type=tt.name))
        for nombre, (mn, mx, ret) in _FUNCIONES_MODULO.items():
            self._agregar(Simbolo(nombre, F, "funcion_modulo", "funcion", aridad=(mn, mx),
                                  retorno=ret, info=f"función del módulo {nombre.split('.')[0]}"))

        # --- 3. Palabras reservadas (sin las constantes) ---
        for lex, tt in PALABRAS_RESERVADAS.items():
            if tt in CONSTANTES:
                continue
            grupo = _GRUPO_DE.get(tt.name, "Otras")
            if tt in (TokenType.MATCH, TokenType.CASE):
                grupo += " (palabra suave)"
            self._agregar(Simbolo(lex, R, "palabra_reservada", token_type=tt.name, info=grupo))

    # ------------------------------------------------------------------
    # Ámbitos
    # ------------------------------------------------------------------
    def entrar_ambito(self, nombre: str, tipo: str, dueno: Optional[Simbolo] = None) -> Ambito:
        amb = Ambito(nombre, tipo, self.actual, dueno)
        self.actual.hijos.append(amb)
        self.actual = amb
        return amb

    def salir_ambito(self) -> None:
        if self.actual.padre is not None:
            self.actual = self.actual.padre

    def _todos_ambitos(self, amb: Optional[Ambito] = None) -> Iterator[Ambito]:
        amb = amb or self.raiz
        yield amb
        for h in amb.hijos:
            yield from self._todos_ambitos(h)

    def _ambito_destino(self, nombre: str) -> Ambito:
        """Dónde cae una asignación: respeta 'global' y 'nonlocal'."""
        if nombre in self.actual.globales:
            return self.raiz
        if nombre in self.actual.nolocales:
            amb = self.actual.padre
            while amb is not None:
                if nombre in amb.simbolos:
                    return amb
                amb = amb.padre
        return self.actual

    # ------------------------------------------------------------------
    # Declarar / buscar
    # ------------------------------------------------------------------
    def declarar(self, nombre: str, subtipo: str, linea: int, columna: int,
                 tipo: str = "desconocido", valor: Any = None) -> Simbolo:
        amb = self._ambito_destino(nombre)
        ex = amb.simbolos.get(nombre)
        if ex is not None:
            # reasignación: ya no es una constante conocida
            ex.lineas_asig.append(linea)
            ex.valor = None
            # Conservador: si alguna asignación tiene tipo incierto, el símbolo queda
            # 'desconocido'; si dos asignaciones tienen tipos distintos, queda 'dinamico'.
            if ex.tipo_dato in ("desconocido", "dinamico"):
                pass
            elif tipo == "desconocido":
                ex.tipo_dato = "desconocido"
            elif ex.tipo_dato != tipo:
                self._avisar(f"'{nombre}' cambia de tipo ({ex.tipo_dato} -> {tipo})", linea)
                ex.tipo_dato = "dinamico"
            return ex
        pre = self.predefinidos.get(nombre)
        if pre is not None and pre.categoria in (Categoria.FUNCION_ESTANDAR,
                                                 Categoria.CONSTANTE_UNIVERSAL):
            self._avisar(f"'{nombre}' es un nombre predefinido ({pre.subtipo}); "
                         f"redefinirlo no está soportado en ELYirs-Py", linea, columna)
        s = Simbolo(nombre, Categoria.IDENTIFICADOR_USUARIO, subtipo, tipo, valor,
                    ambito=amb.ruta, linea_decl=linea, columna_decl=columna,
                    lineas_asig=[linea])
        amb.simbolos[nombre] = s
        return s

    def buscar(self, nombre: str, ambito: Optional[Ambito] = None) -> Optional[Simbolo]:
        """Busca un nombre subiendo por los ámbitos y al final en los predefinidos."""
        s = self._buscar_en_cadena(nombre, ambito or self.actual)
        return s if s is not None else self.predefinidos.get(nombre)

    @staticmethod
    def _buscar_en_cadena(nombre: str, amb: Optional[Ambito]) -> Optional[Simbolo]:
        while amb is not None:
            if nombre in amb.simbolos:
                return amb.simbolos[nombre]
            amb = amb.padre
        return None

    def todos(self) -> Iterator[Simbolo]:
        yield from self.predefinidos.values()
        for amb in self._todos_ambitos():
            yield from amb.simbolos.values()

    # ------------------------------------------------------------------
    # Construcción a partir de los tokens del Scanner
    # ------------------------------------------------------------------
    def construir(self, tokens: List[Token]) -> "TablaSimbolos":
        toks = [t for t in tokens
                if not t.is_any(TokenType.COMMENT, TokenType.NL, TokenType.LINE_CONTINUATION)]
        n_err = sum(1 for t in toks if t.is_error())
        if n_err:
            self.advertencias.append(
                f"el código tiene {n_err} error(es) léxico(s); la tabla puede quedar incompleta")
            # no se agrega a incidencias: esos errores ya los reporta el Scanner

        stmt: List[Token] = []
        depth = 0
        for t in toks:
            if t.is_eof():
                break
            if t.is_indent():
                self._abrir_bloque()
            elif t.is_dedent():
                self._cerrar_bloque()
            elif t.is_newline():
                if stmt:
                    self._procesar(stmt)
                    stmt = []
                depth = 0
            elif t.is_type(TokenType.SEMICOLON) and depth == 0:
                if stmt:                      # 'a = 1; b = 2' son dos instrucciones
                    self._procesar(stmt)
                    stmt = []
            else:
                if not stmt and self._pendiente is not None:
                    self._pendiente = None   # el encabezado no abrió bloque (cuerpo en una línea)
                if t.is_opening():
                    depth += 1
                elif t.is_closing():
                    depth -= 1
                stmt.append(t)
        if stmt:
            self._procesar(stmt)

        self.actual = self.raiz
        self._resolver_usos()
        self._resolver_llamadas()
        for amb in self._todos_ambitos():
            for s in amb.simbolos.values():
                if s.subtipo in ("funcion", "metodo") and s.retorno is None:
                    s.retorno = "NoneType"      # función sin 'return'
        self._asignar_direcciones()
        return self

    # --- bloques (INDENT / DEDENT) ---
    def _abrir_bloque(self) -> None:
        if self._pendiente is not None:
            nombre, tipo, simbolo, params = self._pendiente
            self.entrar_ambito(nombre, tipo, simbolo)
            self._declarar_params(params)
            self._bloques.append(True)
            self._pendiente = None
        else:
            self._bloques.append(False)

    def _cerrar_bloque(self) -> None:
        if self._bloques and self._bloques.pop():
            self.salir_ambito()

    def _declarar_params(self, params: List[dict]) -> None:
        for p in params:
            previo = self.actual.simbolos.get(p["nombre"])
            if previo is not None:
                self._avisar(f"el parámetro '{p['nombre']}' está repetido "
                             f"(ya aparece en la línea {previo.linea_decl})",
                             p["linea"], p["col"])
            s = self.declarar(p["nombre"], "parametro", p["linea"], p["col"], tipo=p["tipo"])
            if p["variadico"]:
                s.info = f"parámetro {p['variadico']}"

    # --- una instrucción (lista de tokens sin el NEWLINE) ---
    def _procesar(self, st: List[Token]) -> None:
        saltar: set = set()      # índices de identificadores que NO son un "uso"
        if st[0].is_type(TokenType.AT):
            return               # '@decorador': no declara ni usa nada en ELYirs-Py
        i0 = 1 if (st[0].is_type(TokenType.ASYNC) and len(st) > 1) else 0
        t0 = st[i0]
        self._lambdas(st, saltar)

        # 'if x: y = 1', 'else: pass', 'def g(): return 1' -> encabezado + cuerpo por separado
        if t0.is_any(*_COMPUESTAS) and not st[-1].is_colon():
            ic = self._primer_colon(st)
            if ic is not None and ic + 1 < len(st):
                self._procesar(st[:ic + 1])
                if self._pendiente is not None:          # def / class: el cuerpo va en su ámbito
                    self._abrir_bloque()
                    self._procesar(st[ic + 1:])
                    self._cerrar_bloque()
                else:
                    self._procesar(st[ic + 1:])
                return

        if t0.is_def():
            self._def(st, i0, saltar)
        elif t0.is_type(TokenType.CLASS):
            self._clase(st, i0, saltar)
        elif t0.is_for():
            self._for(st, i0, saltar)
        elif t0.is_type(TokenType.IMPORT):
            self._import(st, i0, saltar)
        elif t0.is_type(TokenType.FROM):
            self._from(st, i0, saltar)
        elif t0.is_any(TokenType.GLOBAL, TokenType.NONLOCAL):
            destino = (self.actual.globales if t0.is_type(TokenType.GLOBAL)
                       else self.actual.nolocales)
            for k, t in enumerate(st):
                if t.is_identifier():
                    destino.add(t.lexema)
                    saltar.add(k)
        elif t0.is_return():
            self._return(st, i0)
        else:
            self._asignaciones(st, saltar)

        self._declaraciones_genericas(st, saltar)
        self._registrar_usos(st, saltar)

    # --- helpers de análisis ---
    @staticmethod
    def _primer_colon(st: List[Token]) -> Optional[int]:
        """Índice del primer ':' fuera de paréntesis (el que cierra el encabezado)."""
        depth = 0
        for k, t in enumerate(st):
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                depth -= 1
            elif depth == 0 and t.is_colon():
                return k
        return None

    @staticmethod
    def _tramo(st: List[Token], a: int) -> Tuple[int, List[Token]]:
        """Desde st[a], recorre hasta una coma/'='/cierre de nivel 0. Devuelve (fin, tokens)."""
        depth, b = 0, a
        while b < len(st):
            t = st[b]
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and t.is_any(TokenType.COMMA, TokenType.ASSIGN):
                break
            b += 1
        return b, st[a:b]

    @staticmethod
    def _abarca_todo(toks: List[Token], k: int) -> bool:
        """¿El agrupador que abre en toks[k] cierra justo en el último token?"""
        depth = 0
        for idx in range(k, len(toks)):
            if toks[idx].is_opening():
                depth += 1
            elif toks[idx].is_closing():
                depth -= 1
                if depth == 0:
                    return idx == len(toks) - 1
        return False

    @staticmethod
    def _objetivos(st: List[Token], a: int, b: int) -> List[int]:
        """Índices en st[a:b] de nombres que reciben un valor: 'x', 'a, b', '(a, b)'.
        Excluye 'lista[i]' y 'obj.attr' porque ahí el nombre solo se usa."""
        res = []
        for k in range(a, b):
            t = st[k]
            if not t.is_type(TokenType.IDENTIFIER):
                continue
            antes_ok = k == a or st[k - 1].is_any(TokenType.COMMA, TokenType.LPAREN,
                                                  TokenType.MULTIPLY)
            despues_ok = k + 1 >= b or st[k + 1].is_any(TokenType.COMMA, TokenType.RPAREN)
            if antes_ok and despues_ok:
                res.append(k)
        return res

    _OPS_ARIT = (TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY, TokenType.DIVIDE,
                 TokenType.FLOOR_DIVIDE, TokenType.MODULO)

    @staticmethod
    def _combinar(a: str, op: TokenType, b: str) -> str:
        if a in ("int", "float") and b in ("int", "float"):
            if op == TokenType.DIVIDE:
                return "float"
            return "float" if "float" in (a, b) else "int"
        if a == "str" and op == TokenType.MODULO:
            return "str"
        if a == "str" and b == "str" and op == TokenType.PLUS:
            return "str"
        if op == TokenType.MULTIPLY and {a, b} == {"str", "int"}:
            return "str"
        if a == "list" and b == "list" and op == TokenType.PLUS:
            return "list"
        return "desconocido"

    def _tipo_aritmetico(self, toks: List[Token]) -> Optional[str]:
        """Expresiones planas 'a + b * 2' (sin paréntesis): tipo según los operandos."""
        if len(toks) < 3 or len(toks) % 2 == 0:
            return None
        ops, operandos = toks[1::2], toks[0::2]
        if not all(o.type in self._OPS_ARIT for o in ops):
            return None
        tipos = []
        for o in operandos:
            if o.type in _TIPO_LITERAL:
                tipos.append(_TIPO_LITERAL[o.type])
            elif o.is_type(TokenType.IDENTIFIER):
                s = self.buscar(o.lexema)
                tipos.append(s.tipo_dato if s is not None else "desconocido")
            else:
                return None
        acum = tipos[0]
        for op, t in zip(ops, tipos[1:]):
            acum = self._combinar(acum, op.type, t)
            if acum == "desconocido":
                break
        return acum

    def _inferir(self, toks: List[Token]) -> Tuple[str, Any]:
        """Tipo (y valor, si es literal) de una expresión SENCILLA. Lo demás: 'desconocido'."""
        if not toks:
            return "desconocido", None
        t = toks[0]
        if len(toks) == 1 and t.is_type(TokenType.IDENTIFIER):   # 'x = otra_variable'
            ref = self.buscar(t.lexema)
            return (ref.tipo_dato if ref is not None else "desconocido"), None
        if len(toks) == 1 and t.type in _TIPO_LITERAL:
            valor = {TokenType.TRUE: True, TokenType.FALSE: False,
                     TokenType.NONE: None}.get(t.type, t.value)
            return _TIPO_LITERAL[t.type], valor
        if (len(toks) == 2 and toks[0].is_any(TokenType.MINUS, TokenType.PLUS)
                and toks[1].type in _NUMERICOS):
            v = toks[1].value
            return _TIPO_LITERAL[toks[1].type], (-v if toks[0].is_type(TokenType.MINUS) else v)
        if all(x.is_fstring() for x in toks):
            return "str", None
        if t.is_type(TokenType.LBRACKET) and self._abarca_todo(toks, 0):
            return "list", None
        if t.is_type(TokenType.LBRACE) and self._abarca_todo(toks, 0):
            depth, dos_puntos = 0, False
            for x in toks:
                if x.is_opening():
                    depth += 1
                elif x.is_closing():
                    depth -= 1
                elif depth == 1 and x.is_colon():
                    dos_puntos = True
            return ("dict" if (dos_puntos or len(toks) == 2) else "set"), None
        if t.is_type(TokenType.LPAREN) and self._abarca_todo(toks, 0):
            depth, coma = 0, False
            for x in toks:
                if x.is_opening():
                    depth += 1
                elif x.is_closing():
                    depth -= 1
                elif depth == 1 and x.is_comma():
                    coma = True
            if coma or len(toks) == 2:
                return "tuple", None
        ar = self._tipo_aritmetico(toks)
        if ar is not None:
            return ar, None
        if len(toks) > 1 and toks[1].is_type(TokenType.LPAREN) and self._abarca_todo(toks, 1):
            if t.is_builtin():
                ret = self.predefinidos[t.lexema].retorno
                return (ret if ret not in (None, "any", "number") else "desconocido"), None
            if t.is_type(TokenType.IDENTIFIER):
                f = self.buscar(t.lexema)
                if f is not None and f.subtipo in ("funcion", "metodo") and f.retorno:
                    return f.retorno, None
        return "desconocido", None

    # --- def / class / for / import / return / asignaciones ---
    def _def(self, st: List[Token], i0: int, saltar: set) -> None:
        k = i0 + 1
        if k >= len(st) or not st[k].is_identifier():
            if k < len(st) and (st[k].is_builtin() or st[k].is_exception()):
                self._avisar(f"'{st[k].lexema}' es un nombre predefinido y no se puede "
                             f"usar como nombre de función en ELYirs-Py",
                             st[k].linea, st[k].columna)
            return
        nombre_tok = st[k]
        saltar.add(k)
        params: List[dict] = []
        j = k + 1
        if j < len(st) and st[j].is_type(TokenType.LPAREN):
            params, j = self._parse_params(st, j, saltar)
        retorno = None
        if j < len(st) and st[j].is_type(TokenType.ARROW):
            fin = len(st) - 1 if st[-1].is_colon() else len(st)
            retorno = "".join(x.lexema for x in st[j + 1:fin]) or None

        subtipo = "metodo" if self.actual.tipo == "clase" else "funcion"
        s = self.declarar(nombre_tok.lexema, subtipo, nombre_tok.linea, nombre_tok.columna,
                          tipo="funcion")
        s.parametros = [{k2: v for k2, v in p.items() if k2 not in ("linea", "col")}
                        for p in params]
        minimo = sum(1 for p in params if not p["defecto"] and not p["variadico"])
        maximo = None if any(p["variadico"] for p in params) else len(params)
        s.aridad = (minimo, maximo)
        if retorno:
            s.retorno, s.retorno_anotado = retorno, True

        if st[-1].is_colon():
            self._pendiente = (nombre_tok.lexema, "funcion", s, params)

    def _parse_params(self, st: List[Token], j: int, saltar: set) -> Tuple[List[dict], int]:
        """st[j] es el '(' de la definición. Devuelve (parámetros, índice tras el ')')."""
        params: List[dict] = []
        actual: Optional[dict] = None
        k, depth = j + 1, 1
        while k < len(st) and depth > 0:
            t = st[k]
            if (depth == 1 and t.is_identifier()
                    and st[k - 1].is_any(TokenType.LPAREN, TokenType.COMMA,
                                         TokenType.MULTIPLY, TokenType.POWER)):
                prev = st[k - 1]
                var = "*" if prev.is_type(TokenType.MULTIPLY) else \
                      "**" if prev.is_type(TokenType.POWER) else None
                actual = {"nombre": t.lexema, "tipo": "desconocido", "defecto": False,
                          "valor": None, "variadico": var, "linea": t.linea, "col": t.columna}
                params.append(actual)
                saltar.add(k)
                k += 1
                continue
            if depth == 1 and actual is not None and t.is_colon():
                fin, toks = self._tramo(st, k + 1)
                actual["tipo"] = "".join(x.lexema for x in toks) or "desconocido"
                k = fin
                continue
            if depth == 1 and actual is not None and t.is_assign():
                fin, toks = self._tramo(st, k + 1)
                actual["defecto"] = True
                actual["defecto_txt"] = "".join(x.lexema for x in toks)
                tipo_def, val = self._inferir(toks)
                if actual["tipo"] == "desconocido":
                    actual["tipo"] = tipo_def
                actual["valor"] = val
                k = fin
                continue
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                depth -= 1
            k += 1
        return params, k

    def _clase(self, st: List[Token], i0: int, saltar: set) -> None:
        k = i0 + 1
        if k >= len(st) or not st[k].is_identifier():
            return
        t = st[k]
        saltar.add(k)
        s = self.declarar(t.lexema, "clase", t.linea, t.columna, tipo="clase")
        bases = []
        if k + 1 < len(st) and st[k + 1].is_type(TokenType.LPAREN):
            bases = [x.lexema for x in st[k + 2:] if not x.is_any(
                TokenType.COMMA, TokenType.RPAREN, TokenType.COLON)]
        if bases:
            s.info = "hereda de " + ", ".join(bases)
        if st[-1].is_colon():
            self._pendiente = (t.lexema, "clase", s, [])

    def _for(self, st: List[Token], i0: int, saltar: set) -> None:
        depth, fin = 0, None
        for m in range(i0 + 1, len(st)):
            t = st[m]
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                depth -= 1
            elif depth == 0 and t.is_type(TokenType.IN):
                fin = m
                break
        if fin is None:
            return
        objetivos = self._objetivos(st, i0 + 1, fin)
        tipo = "desconocido"
        if (len(objetivos) == 1 and fin + 1 < len(st)
                and st[fin + 1].is_type(TokenType.BUILTIN_RANGE)):
            tipo = "int"       # for i in range(...) -> i es entero
        for m in objetivos:
            self.declarar(st[m].lexema, "variable", st[m].linea, st[m].columna, tipo=tipo)
            saltar.add(m)

    def _elementos(self, st: List[Token], a: int) -> List[List[Tuple[int, Token]]]:
        """Parte st[a:] por comas de nivel 0: [[(idx, tok), ...], ...]"""
        res: List[List[Tuple[int, Token]]] = [[]]
        depth = 0
        for k in range(a, len(st)):
            t = st[k]
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                depth -= 1
            if depth == 0 and t.is_comma():
                res.append([])
            else:
                res[-1].append((k, t))
        return [e for e in res if e]

    def _import(self, st: List[Token], i0: int, saltar: set) -> None:
        # import a, b as c, math.pi ...
        for el in self._elementos(st, i0 + 1):
            alias = None
            for pos, (idx, t) in enumerate(el):
                if t.is_type(TokenType.AS) and pos + 1 < len(el):
                    alias = el[pos + 1]
            base = el[0][1]
            soportado = base.is_module()
            if not soportado:
                self._avisar(f"el módulo '{base.lexema}' no está soportado por ELYirs",
                             base.linea, base.columna)
            destino = alias[1] if alias else (base if base.is_identifier() else None)
            if destino is not None:
                s = self.declarar(destino.lexema, "modulo", destino.linea, destino.columna,
                                  tipo="modulo")
                if alias:
                    s.info = f"alias de {base.lexema}"
        saltar.update(k for k, t in enumerate(st) if t.is_identifier())

    def _from(self, st: List[Token], i0: int, saltar: set) -> None:
        # from modulo import a, b as c
        m = next((k for k, t in enumerate(st) if t.is_type(TokenType.IMPORT)), None)
        if m is None or i0 + 1 >= m:
            return
        modulo = st[i0 + 1]
        if not modulo.is_module():
            self._avisar(f"el módulo '{modulo.lexema}' no está soportado por ELYirs",
                         modulo.linea, modulo.columna)
        for el in self._elementos(st, m + 1):
            nombre = el[0][1]
            if nombre.is_type(TokenType.MULTIPLY):
                self._avisar(f"'from {modulo.lexema} import *' no está soportado",
                             nombre.linea, nombre.columna)
                continue
            alias = None
            for pos, (idx, t) in enumerate(el):
                if t.is_type(TokenType.AS) and pos + 1 < len(el):
                    alias = el[pos + 1][1]
            destino = alias or nombre
            pre = self.predefinidos.get(f"{modulo.lexema}.{nombre.lexema}")
            if pre is not None:
                subtipo = ("constante_importada"
                           if pre.categoria == Categoria.CONSTANTE_UNIVERSAL
                           else "funcion_importada")
                s = self.declarar(destino.lexema, subtipo, destino.linea, destino.columna,
                                  tipo=pre.tipo_dato, valor=pre.valor)
                s.aridad, s.retorno = pre.aridad, pre.retorno
                s.info = f"de {modulo.lexema}.{nombre.lexema}"
                pre.lineas_uso.append(nombre.linea)
            else:
                s = self.declarar(destino.lexema, "importado", destino.linea, destino.columna)
                s.info = f"de {modulo.lexema}"
        saltar.update(k for k, t in enumerate(st) if t.is_identifier())

    def _return(self, st: List[Token], i0: int) -> None:
        tipo = "NoneType" if len(st) == i0 + 1 else self._inferir(st[i0 + 1:])[0]
        amb = self.actual
        while amb is not None and amb.tipo != "funcion":
            amb = amb.padre
        f = amb.dueno if amb is not None else None
        if f is None or f.retorno_anotado:
            return
        if f.retorno is None:
            f.retorno = tipo
        elif f.retorno != tipo and f.retorno not in ("desconocido", "dinamico"):
            f.retorno = "desconocido" if tipo == "desconocido" else "dinamico"

    def _asignaciones(self, st: List[Token], saltar: set) -> None:
        # 'print = 3': el scanner ya clasificó el nombre como predefinido
        if (len(st) > 1 and st[1].is_assignment_operator()
                and (st[0].is_builtin() or st[0].is_exception() or st[0].is_module()
                     or st[0].is_constant())):
            self._avisar(f"'{st[0].lexema}' es un nombre predefinido y no se puede "
                         f"reasignar en ELYirs-Py", st[0].linea, st[0].columna)
            return

        # aumentada:  x += 1   (lee y escribe la misma variable)
        if (len(st) > 1 and st[0].is_type(TokenType.IDENTIFIER)
                and st[1].is_compound_assignment()):
            s = self._buscar_en_cadena(st[0].lexema, self.actual)
            if s is None:
                return           # no declarada: queda como uso y sale la advertencia
            s.lineas_asig.append(st[0].linea)
            s.lineas_uso.append(st[0].linea)
            s.valor = None       # ya no se conoce su valor
            tipo = self._inferir(st[2:])[0]
            if (tipo != "desconocido" and s.tipo_dato not in ("desconocido", "dinamico")
                    and s.tipo_dato != tipo):
                self._avisar(f"'{st[0].lexema}' cambia de tipo ({s.tipo_dato} -> {tipo})",
                             st[0].linea, st[0].columna)
                s.tipo_dato = "dinamico"
            saltar.add(0)
            return

        # anotada:  x: int = 5
        if len(st) > 2 and st[0].is_type(TokenType.IDENTIFIER) and st[1].is_colon():
            fin, anot = self._tramo(st, 2)
            tipo_a = "".join(x.lexema for x in anot)
            tipo_v, val = "desconocido", None
            if fin < len(st) and st[fin].is_assign():
                tipo_v, val = self._inferir(st[fin + 1:])
            self.declarar(st[0].lexema, "variable", st[0].linea, st[0].columna,
                          tipo=tipo_a or tipo_v, valor=val)
            saltar.add(0)
            return

        # normal / encadenada:  a = b = 5      (los '=' de nivel 0)
        pos, depth = [], 0
        for k, t in enumerate(st):
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                depth -= 1
            elif depth == 0 and t.is_assign():
                pos.append(k)
        if not pos:
            return
        lim = [-1] + pos + [len(st)]
        segs = [(lim[n] + 1, lim[n + 1]) for n in range(len(lim) - 1)]
        tipo, val = self._inferir(st[segs[-1][0]:segs[-1][1]])
        for a, b in segs[:-1]:
            objetivos = self._objetivos(st, a, b)
            unico = len(objetivos) == 1 and (b - a) == 1     # 'x = ...' y no 'a, b = ...'
            for k in objetivos:
                self.declarar(st[k].lexema, "variable", st[k].linea, st[k].columna,
                              tipo=tipo if unico else "desconocido",
                              valor=val if unico else None)
                saltar.add(k)

    def _lambdas(self, st: List[Token], saltar: set) -> None:
        """Cada 'lambda p1, p2: cuerpo' abre su propio ámbito, declara sus parámetros
        y consume su cuerpo ahí, para que no parezcan nombres sueltos del ámbito de afuera."""
        k = 0
        while k < len(st):
            if not st[k].is_type(TokenType.LAMBDA):
                k += 1
                continue
            saltar.add(k)
            ini = k
            # parámetros: identificadores hasta el ':' de la lambda
            params, j, depth = [], k + 1, 0
            while j < len(st):
                t = st[j]
                if t.is_opening():
                    depth += 1
                elif t.is_closing():
                    if depth == 0:
                        break
                    depth -= 1
                elif depth == 0 and t.is_colon():
                    break
                elif depth == 0 and t.is_identifier():
                    params.append({"nombre": t.lexema, "tipo": "desconocido", "defecto": False,
                                   "valor": None, "variadico": None,
                                   "linea": t.linea, "col": t.columna})
                saltar.add(j)
                j += 1
            if j >= len(st) or not st[j].is_colon():
                k = j + 1
                continue
            saltar.add(j)
            # cuerpo: hasta una coma o un cierre del nivel de la lambda
            fin, depth = j + 1, 0
            while fin < len(st):
                t = st[fin]
                if t.is_opening():
                    depth += 1
                elif t.is_closing():
                    if depth == 0:
                        break
                    depth -= 1
                elif depth == 0 and t.is_comma():
                    break
                fin += 1
            cuerpo = st[j + 1:fin]
            s = self.declarar(f"lambda@{st[ini].linea}", "funcion", st[ini].linea,
                              st[ini].columna, tipo="funcion")
            s.parametros = [{k2: v for k2, v in p.items() if k2 not in ("linea", "col")}
                            for p in params]
            s.aridad = (len(params), len(params))
            s.retorno = self._inferir(cuerpo)[0]
            s.info = "función anónima (lambda)"
            self.entrar_ambito(f"lambda@{st[ini].linea}", "funcion", s)
            self._declarar_params(params)
            self._registrar_usos(cuerpo, set())
            self.salir_ambito()
            saltar.update(range(j + 1, fin))
            k = fin

    def _declaraciones_genericas(self, st: List[Token], saltar: set) -> None:
        """'(n := 5)', 'with ... as f', 'except ... as e'."""
        for k, t in enumerate(st):
            if k in saltar or not t.is_type(TokenType.IDENTIFIER):
                continue
            if k + 1 < len(st) and st[k + 1].is_type(TokenType.WALRUS):
                self.declarar(t.lexema, "variable", t.linea, t.columna)
                saltar.add(k)
            elif k > 0 and st[k - 1].is_type(TokenType.AS):
                self.declarar(t.lexema, "variable", t.linea, t.columna)
                saltar.add(k)

    # --- llamadas ---
    @staticmethod
    def _argumentos(st: List[Token], k: int) -> Optional[Tuple[int, bool]]:
        """Si st[k+1] abre una llamada, devuelve (número de argumentos, hay * o **)."""
        if k + 1 >= len(st) or not st[k + 1].is_type(TokenType.LPAREN):
            return None
        depth, j, comas, vacio, estrellas = 0, k + 1, 0, True, False
        while j < len(st):
            t = st[j]
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                depth -= 1
                if depth == 0:
                    break
            elif depth == 1:
                vacio = False
                if t.is_comma():
                    comas += 1
                elif t.is_any(TokenType.MULTIPLY, TokenType.POWER) and (
                        st[j - 1].is_any(TokenType.LPAREN, TokenType.COMMA)):
                    estrellas = True
            j += 1
        if depth != 0:
            return None                      # paréntesis sin cerrar
        return (0 if vacio else comas + 1), estrellas

    def _anotar_llamada(self, st: List[Token], k: int, nombre: str) -> None:
        datos = self._argumentos(st, k)
        if datos is None:
            return
        nargs, estrellas = datos
        self._llamadas.append((nombre, nargs, estrellas, st[k].linea, st[k].columna,
                               self.actual))

    def _resolver_llamadas(self) -> None:
        for nombre, nargs, estrellas, linea, col, amb in self._llamadas:
            if estrellas:
                continue                     # f(*args): no se puede contar
            s = self._buscar_en_cadena(nombre, amb) or self.predefinidos.get(nombre)
            if s is None or s.aridad is None:
                continue
            mn, mx = s.aridad
            if nargs < mn or (mx is not None and nargs > mx):
                self._avisar(f"'{nombre}' espera {s.aridad_txt()} argumento(s) "
                             f"y se llamó con {nargs}", linea, col)
        self._llamadas.clear()

    # --- usos ---
    def _registrar_usos(self, st: List[Token], saltar: set) -> None:
        depth = 0
        for k, t in enumerate(st):
            if t.is_opening():
                depth += 1
            elif t.is_closing():
                depth -= 1

            # símbolos predefinidos: se cuenta cada aparición
            if (t.is_keyword() or t.is_constant() or t.is_builtin() or t.is_exception()
                    or t.is_module() or t.is_any(TokenType.ELLIPSIS, TokenType.DUNDER_NAME)):
                pre = self.predefinidos.get(t.lexema)
                if pre is not None:
                    pre.lineas_uso.append(t.linea)
                    if pre.categoria == Categoria.FUNCION_ESTANDAR:
                        self._anotar_llamada(st, k, t.lexema)
                continue

            if t.is_type(TokenType.F_STRING_MIDDLE):
                self._usos_en_fstring(t)
                continue
            if not t.is_type(TokenType.IDENTIFIER):
                continue
            prev = st[k - 1] if k > 0 else None
            if prev is not None and prev.is_type(TokenType.DOT):
                # atributo: solo interesa si es miembro de un módulo soportado (math.sqrt)
                if k >= 2 and st[k - 2].is_module():
                    cualificado = f"{st[k - 2].lexema}.{t.lexema}"
                    q = self.predefinidos.get(cualificado)
                    if q is not None:
                        q.lineas_uso.append(t.linea)
                        self._anotar_llamada(st, k, cualificado)
                continue
            if k in saltar:
                continue
            nxt = st[k + 1] if k + 1 < len(st) else None
            if (depth > 0 and nxt is not None and nxt.is_assign() and prev is not None
                    and prev.is_any(TokenType.LPAREN, TokenType.COMMA)):
                continue    # argumento con nombre: f(x=1)
            self._usos.append((t.lexema, self.actual, t.linea, t.columna))
            self._anotar_llamada(st, k, t.lexema)

    @staticmethod
    def _expresiones_fstring(texto: str) -> List[str]:
        """Extrae las expresiones de 'Hola {nombre!r:>10} {{literal}}' -> ['nombre']."""
        res, i, n = [], 0, len(texto)
        while i < n:
            if texto[i] != "{":
                i += 1
                continue
            if texto[i + 1:i + 2] == "{":          # '{{' es una llave literal
                i += 2
                continue
            depth, j, comilla, corte = 0, i + 1, None, None
            while j < n:
                ch = texto[j]
                if comilla:
                    if ch == comilla:
                        comilla = None
                elif ch in "'\"":
                    comilla = ch
                elif ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    if depth == 0 and ch == "}":
                        break
                    depth -= 1
                elif depth == 0 and corte is None and (
                        ch == ":" or (ch == "!" and texto[j + 1:j + 2] != "=")):
                    corte = j                       # inicio de !r o :formato
                j += 1
            res.append(texto[i + 1:corte if corte is not None else j])
            i = j + 1
        return res

    def _usos_en_fstring(self, tok: Token) -> None:
        """Tokeniza cada {expresión} de una f-string para contar los nombres que usa."""
        for expr in self._expresiones_fstring(str(tok.value)):
            if not expr.strip():
                continue
            sub = [x for x in Scanner(expr.strip()).tokenize()
                   if not x.is_any(TokenType.NEWLINE, TokenType.NL, TokenType.EOF,
                                   TokenType.INDENT, TokenType.DEDENT)]
            for x in sub:
                x.linea = tok.linea
            self._registrar_usos(sub, set())

    def _resolver_usos(self) -> None:
        for nombre, amb, linea, col in self._usos:
            s = self._buscar_en_cadena(nombre, amb)
            if s is not None:
                s.lineas_uso.append(linea)
            else:
                self._avisar(f"'{nombre}' se usa pero nunca se declara", linea, col)
        self._usos.clear()

    # ------------------------------------------------------------------
    # Direcciones para el back-end (x86 de 32 bits, convención cdecl)
    # ------------------------------------------------------------------
    def _asignar_direcciones(self) -> None:
        """Globales -> etiqueta v_<nombre> en la sección .data (el prefijo evita chocar
        con palabras reservadas de MASM como add o loop). Parámetros -> [ebp+8], [ebp+12]...
        Locales -> [ebp-4], [ebp-8]... Funciones y clases -> su propia etiqueta."""
        for amb in self._todos_ambitos():
            if amb.tipo == "funcion":
                param, local = 8, -4
                for s in amb.simbolos.values():
                    if s.subtipo == "parametro":
                        s.direccion = f"[ebp+{param}]"
                        param += 4
                    elif s.subtipo in ("funcion", "metodo", "clase"):
                        s.direccion = s.lexema
                    else:
                        s.direccion = f"[ebp{local}]"
                        local -= 4
                if amb.dueno is not None:
                    amb.dueno.tam_marco = -4 - local
            elif amb.tipo == "clase":
                for s in amb.simbolos.values():
                    s.direccion = f"{amb.nombre}.{s.lexema}"
            else:
                for s in amb.simbolos.values():
                    s.direccion = (s.lexema if s.subtipo in ("funcion", "metodo", "clase")
                                   else f"v_{s.lexema}")

    # ------------------------------------------------------------------
    # Reportes
    # ------------------------------------------------------------------
    @staticmethod
    def _recortar(x: Any, ancho: int) -> str:
        s = "" if x is None else str(x)
        s = s.replace("\n", "\\n")
        return s if len(s) <= ancho else s[:ancho - 3] + "..."

    def _tabla(self, columnas: List[Tuple[str, int]], filas: List[List[Any]]) -> None:
        enc = "".join(f"{t:<{w}}" for t, w in columnas)
        print("  " + enc)
        print("  " + "-" * len(enc))
        for fila in filas:
            print("  " + "".join(f"{self._recortar(v, w - 1):<{w}}"
                                  for v, (_, w) in zip(fila, columnas)))
        print()

    @staticmethod
    def _lineas(s: Simbolo) -> str:
        return ",".join(str(x) for x in sorted(set(s.lineas_uso)))

    def imprimir(self, solo_usados: bool = False) -> None:
        """Imprime las 4 secciones. solo_usados=True oculta los predefinidos que no aparecen
        en el código analizado (los identificadores del usuario siempre se muestran)."""
        def pre(cat: Categoria, subtipo: Optional[str] = None) -> List[Simbolo]:
            lista = [s for s in self.predefinidos.values()
                     if s.categoria == cat and (subtipo is None or s.subtipo == subtipo)]
            return [s for s in lista if s.usos] if solo_usados else lista

        def titulo(txt: str) -> None:
            print("=" * 78)
            print(txt)
            print("=" * 78)

        # 1. Constantes universales
        titulo("1. CONSTANTES UNIVERSALES")
        filas = [[s.lexema, s.tipo_dato, s.valor, s.usos, s.info] for s in
                 pre(Categoria.CONSTANTE_UNIVERSAL)]
        self._tabla([("LEXEMA", 12), ("TIPO", 12), ("VALOR", 24), ("USOS", 6), ("NOTA", 40)],
                    filas)

        # 2. Funciones estándar
        titulo("2. FUNCIONES ESTANDAR")
        bloques = [
            ("2.1 Funciones integradas", "funcion_integrada"),
            ("2.2 Excepciones", "excepcion"),
            ("2.3 Módulos soportados", "modulo"),
            ("2.4 Funciones de módulos", "funcion_modulo"),
        ]
        for nombre, sub in bloques:
            print(f"  {nombre}")
            self._tabla([("LEXEMA", 18), ("ARIDAD", 9), ("RETORNO", 12), ("USOS", 6), ("NOTA", 36)],
                        [[s.lexema, s.aridad_txt(), s.retorno, s.usos, s.info]
                         for s in pre(Categoria.FUNCION_ESTANDAR, sub)])

        # 3. Palabras reservadas
        titulo("3. PALABRAS RESERVADAS")
        self._tabla([("LEXEMA", 12), ("TOKEN", 12), ("GRUPO", 34), ("USOS", 6)],
                    [[s.lexema, s.token_type, s.info, s.usos]
                     for s in pre(Categoria.PALABRA_RESERVADA)])

        # 4. Identificadores del usuario, por ámbito
        titulo("4. IDENTIFICADORES DEL USUARIO")
        for amb in self._todos_ambitos():
            print(f"  Ámbito: {amb.ruta}   ({amb.tipo})")
            if not amb.simbolos:
                print("    (vacío)\n")
                continue
            filas = []
            for s in amb.simbolos.values():
                detalle = s.info
                if s.subtipo in ("funcion", "metodo"):
                    ps = ", ".join(
                        (p["variadico"] or "") + p["nombre"]
                        + (f": {p['tipo']}" if p["tipo"] != "desconocido" else "")
                        + (f"={p['defecto_txt']}" if p["defecto"] else "")
                        for p in s.parametros)
                    detalle = f"({ps}) -> {s.retorno}"
                    if s.tam_marco:
                        detalle += f"   marco: {s.tam_marco} bytes"
                filas.append([s.lexema, s.subtipo, s.tipo_dato, s.valor,
                              f"{s.linea_decl}:{s.columna_decl}", len(s.lineas_asig),
                              self._lineas(s), s.direccion, detalle])
            self._tabla([("LEXEMA", 18), ("SUBTIPO", 20), ("TIPO", 13), ("VALOR", 10),
                         ("DECL", 7), ("ASIG", 6), ("USOS (líneas)", 16),
                         ("DIRECCION x86", 15), ("DETALLE", 52)], filas)

        if self.advertencias:
            titulo("ADVERTENCIAS")
            for a in self.advertencias:
                print(f"  - {a}")
            print()

    def to_dicts(self) -> List[Dict[str, Any]]:
        filas = []
        for s in self.todos():
            filas.append({
                "categoria": s.categoria.value, "subtipo": s.subtipo, "lexema": s.lexema,
                "tipo_dato": s.tipo_dato, "valor": s.valor, "ambito": s.ambito,
                "linea_decl": s.linea_decl, "columna_decl": s.columna_decl,
                "aridad": s.aridad_txt(), "retorno": s.retorno or "",
                "parametros": ", ".join(p["nombre"] for p in s.parametros),
                "asignaciones": len(s.lineas_asig), "usos": s.usos,
                "lineas_uso": ",".join(str(x) for x in sorted(set(s.lineas_uso))),
                "info": s.info, "direccion": s.direccion, "tam_marco": s.tam_marco,
            })
        return filas

    def exportar_csv(self, ruta: str) -> None:
        filas = self.to_dicts()
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Excel
            w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            w.writeheader()
            w.writerows(filas)


# ======================================================================
# Línea de comandos
# ======================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="Tabla de símbolos de ELYirs")
    ap.add_argument("archivo", help="archivo con el código fuente a analizar")
    ap.add_argument("--completa", action="store_true",
                    help="muestra también los predefinidos que el código no usa")
    ap.add_argument("--csv", metavar="SALIDA.csv", help="exporta la tabla a CSV")
    ap.add_argument("--sin-errores", action="store_true",
                    help="no imprime el reporte de errores al final")
    args = ap.parse_args()

    try:
        with open(args.archivo, "r", encoding="utf-8") as f:
            codigo = f.read()
    except OSError as e:
        print(f"No se pudo abrir '{args.archivo}': {e}")
        raise SystemExit(1)

    print(f"Analizando: {args.archivo}\n")

    tokens = Scanner(codigo).tokenize()
    tabla = TablaSimbolos().construir(tokens)
    tabla.imprimir(solo_usados=not args.completa)

    if args.csv:
        tabla.exportar_csv(args.csv)
        print(f"CSV exportado a {args.csv}")

    # Reporte final con ErrorHandler.py: errores léxicos del Scanner
    # + avisos de la tabla, en un solo listado ordenado por línea.
    if not args.sin_errores and ErrorManager is not None:
        gestor = ErrorManager(codigo)
        gestor.recolectar_errores_lexicos(tokens)
        for linea, columna, mensaje in sorted(tabla.incidencias):
            gestor.agregar_error(FaseError.SEMANTICO, mensaje, linea, columna, "")
        gestor.imprimir_reporte()


if __name__ == "__main__":
    main()
