import re

from app.schema import ALLOWED_TABLES

FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
]

FORBIDDEN_QUESTION_PATTERNS = [
    r"\bdelete\b",
    r"\bdrop\b",
    r"\btruncate\b",
    r"\bupdate\b",
    r"\binsert\b",
    r"\balter\b",
    r"\bremove\b",
    r"\bmodify\b",
    r"\bcreate table\b",
    r"\bdelete all rows\b",
    r"\bwrite sql that deletes\b",
]

FORBIDDEN_SYSTEM_PATTERNS = [
    r"\binformation_schema\b",
    r"\bpg_catalog\b",
    r"\bpg_tables\b",
    r"\bpg_class\b",
    r"\bpg_attribute\b",
    r"\bpg_indexes\b",
]

def normalize_sql(sql: str) -> str:
    return sql.strip()


def has_multiple_statements(sql: str) -> bool:
    stripped = sql.strip()

    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()

    return ";" in stripped


def starts_with_select_or_with(sql: str) -> bool:
    sql_upper = sql.strip().upper()
    return sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")


def contains_forbidden_keywords(sql: str) -> bool:
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_upper):
            return True
    return False


def contains_select_into(sql: str) -> bool:
    return re.search(
        r"\bselect\b.*\binto\b",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    ) is not None


def contains_forbidden_system_access(sql: str) -> bool:
    for pattern in FORBIDDEN_SYSTEM_PATTERNS:
        if re.search(pattern, sql, flags=re.IGNORECASE):
            return True
    return False


def extract_table_names(sql: str) -> list[str]:
    # Match tables following FROM or JOIN, accounting for optional schema prefixes (e.g. public.tablename)
    matches = re.findall(
        r"\b(?:from|join)\s+(?:([a-zA-Z0-9_]+)\.)?([a-zA-Z_][a-zA-Z0-9_]*)",
        sql,
        flags=re.IGNORECASE,
    )
    return [table for schema, table in matches]



def extract_cte_names(sql: str) -> set[str]:
    cte_names = set()

    matches = re.findall(
        r"(?:\bwith\b|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(",
        sql,
        flags=re.IGNORECASE,
    )

    for name in matches:
        cte_names.add(name.lower())

    return cte_names


def uses_only_allowed_tables(sql: str) -> tuple[bool, str]:
    table_names = extract_table_names(sql)
    cte_names = extract_cte_names(sql)

    if not table_names:
        return False, "SQL must reference at least one allowed table."

    real_table_found = False

    for table in table_names:
        table_lower = table.lower()

        if table_lower in cte_names:
            continue

        if table_lower not in ALLOWED_TABLES:
            return False, f"Table '{table}' is not allowed."

        real_table_found = True

    if not real_table_found:
        return False, "SQL must reference at least one allowed base table."

    return True, "All referenced tables are allowed."


def validate_sql(sql: str) -> tuple[bool, str]:
    sql = normalize_sql(sql)

    if not sql:
        return False, "SQL is empty."

    if has_multiple_statements(sql):
        return False, "Multiple SQL statements are not allowed."

    if not starts_with_select_or_with(sql):
        return False, "Only SELECT queries are allowed."

    if contains_forbidden_keywords(sql):
        return False, "SQL contains forbidden keywords."

    if contains_select_into(sql):
        return False, "SELECT INTO is not allowed."

    if contains_forbidden_system_access(sql):
        return False, "Access to system tables is not allowed."

    allowed_tables_ok, allowed_tables_message = uses_only_allowed_tables(sql)
    if not allowed_tables_ok:
        return False, allowed_tables_message

    return True, "SQL is valid."


def validate_user_question(question: str) -> tuple[bool, str]:
    q = question.strip().lower()

    if not q:
        return False, "Please enter a business analytics question."

    for pattern in FORBIDDEN_QUESTION_PATTERNS:
        if re.search(pattern, q, flags=re.IGNORECASE):
            return False, (
                "This application only supports read-only analytics questions. "
                "Requests that modify or delete data are not allowed."
            )

    return True, "Question is valid."
