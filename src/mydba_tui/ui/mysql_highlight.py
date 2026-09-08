"""
MySQL-specific syntax highlighter.

Produces Rich Text objects with full coloring for MySQL 8.0/8.4 syntax
including procedural code (BEGIN/END, IF/THEN, DECLARE, CURSOR, HANDLER, etc.).

Color scheme based on VS Code Dark+ theme:
- Keywords (DML/DDL): #c586c0 (purple)
- Procedural keywords: #c586c0 (purple)
- Flow control: #569cd6 (blue)
- Data types: #4ec9b0 (teal)
- Built-in functions: #dcdcaa (yellow)
- Strings: #ce9178 (orange)
- Numbers: #b5cea8 (light green)
- Comments: #6a9955 (green)
- Operators/punctuation: #cccccc (light gray)
- Identifiers/columns: #9cdcfe (light blue)
- System variables: #9cdcfe (light blue)
- Backtick-quoted: #9cdcfe (light blue)
"""

import re

from rich.style import Style
from rich.text import Text

# --- Color definitions (VS Code Dark+ inspired) ---

_C_KEYWORD = Style(color="#c586c0", bold=True)  # Purple — SQL keywords
_C_FLOW = Style(color="#569cd6", bold=True)  # Blue — flow control
_C_TYPE = Style(color="#4ec9b0")  # Teal — data types
_C_FUNCTION = Style(color="#dcdcaa")  # Yellow — built-in functions
_C_STRING = Style(color="#ce9178")  # Orange — strings
_C_NUMBER = Style(color="#b5cea8")  # Light green — numbers
_C_COMMENT = Style(color="#6a9955", italic=True)  # Green italic — comments
_C_OPERATOR = Style(color="#cccccc")  # Light gray — operators
_C_IDENTIFIER = Style(color="#9cdcfe")  # Light blue — backtick-quoted names
_C_SYSVAR = Style(color="#9cdcfe")  # Light blue — @@variables
_C_USERVAR = Style(color="#9cdcfe")  # Light blue — @variables
_C_PARAM = Style(color="#9cdcfe")  # Light blue — procedure params
_C_CONSTANT = Style(color="#7daf9c")  # Muted teal — TRUE/FALSE/NULL

# --- MySQL 8.0/8.4 keyword sets ---

# DML/DDL keywords
_KEYWORDS = frozenset(
    {
        "SELECT",
        "FROM",
        "WHERE",
        "AND",
        "OR",
        "NOT",
        "IN",
        "EXISTS",
        "BETWEEN",
        "LIKE",
        "IS",
        "AS",
        "ON",
        "USING",
        "JOIN",
        "INNER",
        "LEFT",
        "RIGHT",
        "OUTER",
        "CROSS",
        "NATURAL",
        "STRAIGHT_JOIN",
        "INSERT",
        "INTO",
        "VALUES",
        "VALUE",
        "UPDATE",
        "SET",
        "DELETE",
        "REPLACE",
        "MERGE",
        "CALL",
        "DO",
        "CREATE",
        "ALTER",
        "DROP",
        "RENAME",
        "TRUNCATE",
        "TABLE",
        "VIEW",
        "INDEX",
        "DATABASE",
        "SCHEMA",
        "EVENT",
        "PROCEDURE",
        "FUNCTION",
        "TRIGGER",
        "SERVER",
        "TABLESPACE",
        "COLUMN",
        "CONSTRAINT",
        "FOREIGN",
        "PRIMARY",
        "KEY",
        "UNIQUE",
        "REFERENCES",
        "CASCADE",
        "RESTRICT",
        "NO",
        "ACTION",
        "ADD",
        "MODIFY",
        "CHANGE",
        "AFTER",
        "FIRST",
        "GRANT",
        "REVOKE",
        "PRIVILEGES",
        "ALL",
        "TO",
        "WITH",
        "OPTION",
        "IDENTIFIED",
        "BY",
        "SHOW",
        "DESCRIBE",
        "DESC",
        "EXPLAIN",
        "ANALYZE",
        "USE",
        "LOCK",
        "UNLOCK",
        "TABLES",
        "FLUSH",
        "RESET",
        "START",
        "TRANSACTION",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
        "CHAIN",
        "WORK",
        "ORDER",
        "GROUP",
        "HAVING",
        "LIMIT",
        "OFFSET",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "DISTINCT",
        "ASC",
        "NULLS",
        "LAST",
        "PARTITION",
        "SUBPARTITION",
        "PARTITIONS",
        "ENGINE",
        "CHARSET",
        "CHARACTER",
        "COLLATE",
        "COMMENT",
        "AUTO_INCREMENT",
        "DEFAULT",
        "SIGNED",
        "UNSIGNED",
        "ZEROFILL",
        "NULL",
        "CHECK",
        "TEMPORARY",
        "IF",
        "ALGORITHM",
        "DEFINER",
        "INVOKER",
        "SECURITY",
        "SQL",
        "DETERMINISTIC",
        "CONTAINS",
        "READS",
        "MODIFIES",
        "DATA",
        "RETURNS",
        "RETURN",
        "LANGUAGE",
        "BEFORE",
        "EACH",
        "ROW",
        "FOLLOWS",
        "PRECEDES",
        "FOR",
        "EVERY",
        "SCHEDULE",
        "AT",
        "STARTS",
        "ENDS",
        "COMPLETION",
        "PRESERVE",
        "ENABLE",
        "DISABLE",
        "SLAVE",
        "LOAD",
        "INFILE",
        "OUTFILE",
        "DUMPFILE",
        "FIELDS",
        "TERMINATED",
        "ENCLOSED",
        "ESCAPED",
        "LINES",
        "STARTING",
        "OPTIONALLY",
        "HANDLER",
        "OPEN",
        "CLOSE",
        "FETCH",
        "NEXT",
        "PREPARE",
        "EXECUTE",
        "DEALLOCATE",
        "SIGNAL",
        "RESIGNAL",
        "CONDITION",
        "SQLSTATE",
        "GET",
        "DIAGNOSTICS",
        "STACKED",
        "FORCE",
        "IGNORE",
        "LOW_PRIORITY",
        "DELAYED",
        "HIGH_PRIORITY",
        "QUICK",
        "CONCURRENT",
        "OVER",
        "WINDOW",
        "ROWS",
        "RANGE",
        "GROUPS",
        "UNBOUNDED",
        "PRECEDING",
        "FOLLOWING",
        "CURRENT",
        "EXCLUDE",
        "TIES",
        "OTHERS",
        "LATERAL",
        "RECURSIVE",
        "CTE",
        "SPATIAL",
        "FULLTEXT",
        "SEPARATOR",
        "BOTH",
        "LEADING",
        "TRAILING",
        "ONLY",
        "SOME",
        "ANY",
        "DUAL",
        "FORMAT",
        "JSON",
        "TREE",
        "ENCRYPTION",
        "COMPRESSED",
        "REDUNDANT",
        "DYNAMIC",
        "COMPACT",
        "ROW_FORMAT",
        "KEY_BLOCK_SIZE",
        "STATS_PERSISTENT",
        "STATS_AUTO_RECALC",
        "STATS_SAMPLE_PAGES",
        "STORAGE",
        "DISK",
        "MEMORY",
        "CONVERT",
        "CAST",
        "INTERVAL",
        "YEAR",
        "MONTH",
        "DAY",
        "HOUR",
        "MINUTE",
        "SECOND",
        "MICROSECOND",
        "WEEK",
        "QUARTER",
        "YEAR_MONTH",
        "DAY_HOUR",
        "DAY_MINUTE",
        "DAY_SECOND",
        "HOUR_MINUTE",
        "HOUR_SECOND",
        "MINUTE_SECOND",
        "COLLATION",
        "BINARY",
        "VARYING",
        "MAXVALUE",
        "LESS",
        "THAN",
        "LINEAR",
        "HASH",
        "LIST",
        "INVISIBLE",
        "VISIBLE",
        "GENERATED",
        "ALWAYS",
        "STORED",
        "VIRTUAL",
        "PERSIST",
        "PERSIST_ONLY",
        "GLOBAL",
        "SESSION",
        "LOCAL",
    }
)

# Procedural/flow control keywords
_FLOW_KEYWORDS = frozenset(
    {
        "BEGIN",
        "END",
        "IF",
        "THEN",
        "ELSE",
        "ELSEIF",
        "CASE",
        "WHEN",
        "WHILE",
        "DO",
        "LOOP",
        "REPEAT",
        "UNTIL",
        "LEAVE",
        "ITERATE",
        "GOTO",
        "DECLARE",
        "CURSOR",
        "CONTINUE",
        "EXIT",
        "OPEN",
        "CLOSE",
        "FETCH",
        "RETURN",
        "RETURNS",
    }
)

# Data types
_TYPES = frozenset(
    {
        "INT",
        "INTEGER",
        "TINYINT",
        "SMALLINT",
        "MEDIUMINT",
        "BIGINT",
        "FLOAT",
        "DOUBLE",
        "REAL",
        "DECIMAL",
        "NUMERIC",
        "DEC",
        "FIXED",
        "BIT",
        "BOOL",
        "BOOLEAN",
        "CHAR",
        "VARCHAR",
        "BINARY",
        "VARBINARY",
        "TINYBLOB",
        "BLOB",
        "MEDIUMBLOB",
        "LONGBLOB",
        "TINYTEXT",
        "TEXT",
        "MEDIUMTEXT",
        "LONGTEXT",
        "ENUM",
        "SET",
        "DATE",
        "TIME",
        "DATETIME",
        "TIMESTAMP",
        "YEAR",
        "JSON",
        "GEOMETRY",
        "POINT",
        "LINESTRING",
        "POLYGON",
        "MULTIPOINT",
        "MULTILINESTRING",
        "MULTIPOLYGON",
        "GEOMETRYCOLLECTION",
        "SERIAL",
        "NCHAR",
        "NVARCHAR",
        "NATIONAL",
        "LONG",
        "PRECISION",
    }
)

# Built-in functions (MySQL 8.0/8.4 — comprehensive list)
_FUNCTIONS = frozenset(
    {
        # String functions
        "ASCII",
        "BIN",
        "BIT_LENGTH",
        "CHAR",
        "CHAR_LENGTH",
        "CHARACTER_LENGTH",
        "CONCAT",
        "CONCAT_WS",
        "ELT",
        "EXPORT_SET",
        "FIELD",
        "FIND_IN_SET",
        "FORMAT",
        "FROM_BASE64",
        "HEX",
        "INSERT",
        "INSTR",
        "LCASE",
        "LEFT",
        "LENGTH",
        "LOAD_FILE",
        "LOCATE",
        "LOWER",
        "LPAD",
        "LTRIM",
        "MAKE_SET",
        "MID",
        "OCT",
        "OCTET_LENGTH",
        "ORD",
        "POSITION",
        "QUOTE",
        "REPEAT",
        "REPLACE",
        "REVERSE",
        "RIGHT",
        "RPAD",
        "RTRIM",
        "SOUNDEX",
        "SPACE",
        "STRCMP",
        "SUBSTR",
        "SUBSTRING",
        "SUBSTRING_INDEX",
        "TO_BASE64",
        "TRIM",
        "UCASE",
        "UNHEX",
        "UPPER",
        "WEIGHT_STRING",
        # Numeric functions
        "ABS",
        "ACOS",
        "ASIN",
        "ATAN",
        "ATAN2",
        "CEIL",
        "CEILING",
        "CONV",
        "COS",
        "COT",
        "CRC32",
        "DEGREES",
        "DIV",
        "EXP",
        "FLOOR",
        "LN",
        "LOG",
        "LOG10",
        "LOG2",
        "MOD",
        "PI",
        "POW",
        "POWER",
        "RADIANS",
        "RAND",
        "ROUND",
        "SIGN",
        "SIN",
        "SQRT",
        "TAN",
        "TRUNCATE",
        # Date/time functions
        "ADDDATE",
        "ADDTIME",
        "CONVERT_TZ",
        "CURDATE",
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
        "CURTIME",
        "DATE",
        "DATE_ADD",
        "DATE_FORMAT",
        "DATE_SUB",
        "DATEDIFF",
        "DAY",
        "DAYNAME",
        "DAYOFMONTH",
        "DAYOFWEEK",
        "DAYOFYEAR",
        "EXTRACT",
        "FROM_DAYS",
        "FROM_UNIXTIME",
        "GET_FORMAT",
        "HOUR",
        "LAST_DAY",
        "LOCALTIME",
        "LOCALTIMESTAMP",
        "MAKEDATE",
        "MAKETIME",
        "MICROSECOND",
        "MINUTE",
        "MONTH",
        "MONTHNAME",
        "NOW",
        "PERIOD_ADD",
        "PERIOD_DIFF",
        "QUARTER",
        "SEC_TO_TIME",
        "SECOND",
        "STR_TO_DATE",
        "SUBDATE",
        "SUBTIME",
        "SYSDATE",
        "TIME",
        "TIME_FORMAT",
        "TIME_TO_SEC",
        "TIMEDIFF",
        "TIMESTAMP",
        "TIMESTAMPADD",
        "TIMESTAMPDIFF",
        "TO_DAYS",
        "TO_SECONDS",
        "UNIX_TIMESTAMP",
        "UTC_DATE",
        "UTC_TIME",
        "UTC_TIMESTAMP",
        "WEEK",
        "WEEKDAY",
        "WEEKOFYEAR",
        "YEAR",
        "YEARWEEK",
        # Aggregate functions
        "AVG",
        "BIT_AND",
        "BIT_OR",
        "BIT_XOR",
        "COUNT",
        "GROUP_CONCAT",
        "JSON_ARRAYAGG",
        "JSON_OBJECTAGG",
        "MAX",
        "MIN",
        "STD",
        "STDDEV",
        "STDDEV_POP",
        "STDDEV_SAMP",
        "SUM",
        "VAR_POP",
        "VAR_SAMP",
        "VARIANCE",
        # Window functions
        "CUME_DIST",
        "DENSE_RANK",
        "FIRST_VALUE",
        "LAG",
        "LAST_VALUE",
        "LEAD",
        "NTH_VALUE",
        "NTILE",
        "PERCENT_RANK",
        "RANK",
        "ROW_NUMBER",
        # JSON functions
        "JSON_ARRAY",
        "JSON_ARRAY_APPEND",
        "JSON_ARRAY_INSERT",
        "JSON_CONTAINS",
        "JSON_CONTAINS_PATH",
        "JSON_DEPTH",
        "JSON_EXTRACT",
        "JSON_INSERT",
        "JSON_KEYS",
        "JSON_LENGTH",
        "JSON_MERGE",
        "JSON_MERGE_PATCH",
        "JSON_MERGE_PRESERVE",
        "JSON_OBJECT",
        "JSON_OVERLAPS",
        "JSON_PRETTY",
        "JSON_QUOTE",
        "JSON_REMOVE",
        "JSON_REPLACE",
        "JSON_SCHEMA_VALID",
        "JSON_SCHEMA_VALIDATION_REPORT",
        "JSON_SEARCH",
        "JSON_SET",
        "JSON_STORAGE_FREE",
        "JSON_STORAGE_SIZE",
        "JSON_TABLE",
        "JSON_TYPE",
        "JSON_UNQUOTE",
        "JSON_VALID",
        "JSON_VALUE",
        "MEMBER",
        "OF",
        # Control flow
        "IF",
        "IFNULL",
        "NULLIF",
        "COALESCE",
        "GREATEST",
        "LEAST",
        "ISNULL",
        "INTERVAL",
        # Cast
        "CAST",
        "CONVERT",
        "BINARY",
        # Encryption
        "AES_DECRYPT",
        "AES_ENCRYPT",
        "MD5",
        "SHA1",
        "SHA2",
        "RANDOM_BYTES",
        "STATEMENT_DIGEST",
        "STATEMENT_DIGEST_TEXT",
        # Information functions
        "BENCHMARK",
        "CHARSET",
        "COERCIBILITY",
        "COLLATION",
        "CONNECTION_ID",
        "CURRENT_ROLE",
        "CURRENT_USER",
        "DATABASE",
        "FOUND_ROWS",
        "ICU_VERSION",
        "LAST_INSERT_ID",
        "ROW_COUNT",
        "SCHEMA",
        "SESSION_USER",
        "SYSTEM_USER",
        "USER",
        "VERSION",
        # Misc functions
        "ANY_VALUE",
        "BIN_TO_UUID",
        "DEFAULT",
        "GROUPING",
        "INET_ATON",
        "INET_NTOA",
        "INET6_ATON",
        "INET6_NTOA",
        "IS_IPV4",
        "IS_IPV4_COMPAT",
        "IS_IPV4_MAPPED",
        "IS_IPV6",
        "IS_UUID",
        "NAME_CONST",
        "SLEEP",
        "UUID",
        "UUID_SHORT",
        "UUID_TO_BIN",
        "VALUES",
        # Spatial functions
        "ST_AREA",
        "ST_ASBINARY",
        "ST_ASGEOJSON",
        "ST_ASTEXT",
        "ST_BUFFER",
        "ST_CENTROID",
        "ST_CONTAINS",
        "ST_CROSSES",
        "ST_DIFFERENCE",
        "ST_DIMENSION",
        "ST_DISJOINT",
        "ST_DISTANCE",
        "ST_DISTANCE_SPHERE",
        "ST_ENDPOINT",
        "ST_ENVELOPE",
        "ST_EQUALS",
        "ST_EXTERIORRING",
        "ST_GEOHASH",
        "ST_GEOMCOLLFROMTEXT",
        "ST_GEOMFROMGEOJSON",
        "ST_GEOMFROMTEXT",
        "ST_GEOMFROMWKB",
        "ST_GEOMETRYN",
        "ST_GEOMETRYTYPE",
        "ST_INTERIORRINGN",
        "ST_INTERSECTION",
        "ST_INTERSECTS",
        "ST_ISCLOSED",
        "ST_ISEMPTY",
        "ST_ISSIMPLE",
        "ST_ISVALID",
        "ST_LATFROMGEOHASH",
        "ST_LATITUDE",
        "ST_LENGTH",
        "ST_LINEFROMTEXT",
        "ST_LONGFROMGEOHASH",
        "ST_LONGITUDE",
        "ST_MAKEENVELOPE",
        "ST_MLINEFROMTEXT",
        "ST_MPOINTFROMTEXT",
        "ST_MPOLYFROMTEXT",
        "ST_NUMGEOMETRIES",
        "ST_NUMINTERIORRING",
        "ST_NUMPOINTS",
        "ST_OVERLAPS",
        "ST_POINTFROMGEOHASH",
        "ST_POINTFROMTEXT",
        "ST_POINTN",
        "ST_POLYFROMTEXT",
        "ST_SIMPLIFY",
        "ST_SRID",
        "ST_STARTPOINT",
        "ST_SWAPXY",
        "ST_SYMDIFFERENCE",
        "ST_TOUCHES",
        "ST_TRANSFORM",
        "ST_UNION",
        "ST_VALIDATE",
        "ST_WITHIN",
        "ST_X",
        "ST_Y",
        # Full-text
        "MATCH",
        "AGAINST",
        # Locking
        "GET_LOCK",
        "IS_FREE_LOCK",
        "IS_USED_LOCK",
        "RELEASE_LOCK",
        "RELEASE_ALL_LOCKS",
        # Performance Schema
        "PS_CURRENT_THREAD_ID",
        "PS_THREAD_ID",
        # Replication
        "GTID_SUBSET",
        "GTID_SUBTRACT",
        "WAIT_FOR_EXECUTED_GTID_SET",
        "WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS",
        "SOURCE_POS_WAIT",
    }
)

# Constants
_CONSTANTS = frozenset(
    {
        "TRUE",
        "FALSE",
        "NULL",
        "UNKNOWN",
    }
)

# --- Tokenizer regex pattern ---

_TOKEN_PATTERN = re.compile(
    r"""
    (?P<block_comment>/\*[\s\S]*?\*/)           |  # Block comment
    (?P<line_comment>--[^\n]*)                   |  # Line comment
    (?P<hash_comment>\#[^\n]*)                   |  # Hash comment
    (?P<dq_string>"(?:[^"\\]|\\.)*")             |  # Double-quoted string
    (?P<sq_string>'(?:[^'\\]|\\.)*')             |  # Single-quoted string
    (?P<backtick>`[^`]*`)                        |  # Backtick-quoted identifier
    (?P<sysvar>@@\w+)                            |  # System variable
    (?P<uservar>@\w+)                            |  # User variable
    (?P<number>\b\d+\.?\d*(?:[eE][+-]?\d+)?\b)  |  # Number
    (?P<hex_number>\b0x[0-9a-fA-F]+\b)          |  # Hex number
    (?P<word>\b[a-zA-Z_]\w*\b)                   |  # Word (keyword/identifier)
    (?P<operator>[+\-*/%=<>!&|^~:]+)            |  # Operators
    (?P<paren>[()[\]{}])                         |  # Brackets
    (?P<punct>[;,.:])                            |  # Punctuation
    (?P<whitespace>\s+)                          |  # Whitespace
    (?P<other>.)                                    # Anything else
    """,
    re.VERBOSE | re.IGNORECASE,
)


def highlight_mysql(sql: str) -> Text:
    """Highlight MySQL SQL text and return a Rich Text object.

    Handles all MySQL syntax including:
    - DDL (CREATE TABLE/VIEW/PROCEDURE/FUNCTION/TRIGGER/EVENT)
    - DML (SELECT/INSERT/UPDATE/DELETE)
    - Procedural code (BEGIN/END, IF/THEN, DECLARE, LOOP, CURSOR)
    - Comments (block, line, hash)
    - Strings (single/double quoted)
    - Backtick-quoted identifiers
    - System/user variables
    - Built-in functions
    - Data types
    - Numbers and hex literals

    Args:
        sql: The SQL text to highlight.

    Returns:
        Rich Text object with syntax styles applied.
    """
    text = Text()

    for match in _TOKEN_PATTERN.finditer(sql):
        token = match.group()
        kind = match.lastgroup

        if kind == "block_comment":
            text.append(token, style=_C_COMMENT)
        elif kind == "line_comment":
            text.append(token, style=_C_COMMENT)
        elif kind == "hash_comment":
            text.append(token, style=_C_COMMENT)
        elif kind in ("dq_string", "sq_string"):
            text.append(token, style=_C_STRING)
        elif kind == "backtick":
            text.append(token, style=_C_IDENTIFIER)
        elif kind == "sysvar":
            text.append(token, style=_C_SYSVAR)
        elif kind == "uservar":
            text.append(token, style=_C_USERVAR)
        elif kind in ("number", "hex_number"):
            text.append(token, style=_C_NUMBER)
        elif kind == "word":
            upper = token.upper()
            if upper in _CONSTANTS:
                text.append(token, style=_C_CONSTANT)
            elif upper in _FLOW_KEYWORDS:
                text.append(token, style=_C_FLOW)
            elif upper in _TYPES:
                text.append(token, style=_C_TYPE)
            elif upper in _FUNCTIONS:
                text.append(token, style=_C_FUNCTION)
            elif upper in _KEYWORDS:
                text.append(token, style=_C_KEYWORD)
            else:
                # Regular identifier — no special coloring
                text.append(token)
        elif kind == "operator":
            text.append(token, style=_C_OPERATOR)
        elif kind in ("paren", "punct"):
            text.append(token, style=_C_OPERATOR)
        elif kind == "whitespace":
            text.append(token)
        else:
            text.append(token)

    return text


def highlight_mysql_lines(sql: str) -> list[Text]:
    """Highlight MySQL SQL and return a list of Rich Text objects, one per line."""
    full = highlight_mysql(sql)
    return list(full.split("\n"))
