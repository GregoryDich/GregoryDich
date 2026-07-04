"""DuckDB: единая точка доступа.

Одно соединение на процесс; у DuckDB result set живёт на соединении, поэтому
execute+fetch ДОЛЖНЫ быть атомарными — иначе параллельные запросы FastAPI
перезаписывают результаты друг друга. RLock позволяет транзакциям вкладывать
обычные вызовы execute().
"""
import threading
from contextlib import contextmanager
from pathlib import Path

import duckdb

from app import config

_lock = threading.RLock()
_con: duckdb.DuckDBPyConnection | None = None

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_con() -> duckdb.DuckDBPyConnection:
    global _con
    with _lock:
        if _con is None:
            _con = duckdb.connect(str(config.DB_PATH))
            _con.execute(SCHEMA_PATH.read_text())
        return _con


def execute(sql: str, params: list | None = None) -> None:
    """Запись/DDL. Результат не возвращается — для чтения есть fetchall/fetchdf."""
    with _lock:
        get_con().execute(sql, params or [])


def executemany(sql: str, rows: list[list]) -> None:
    """Батч-запись одним вызовом — быстрее цикла execute()."""
    if not rows:
        return
    with _lock:
        get_con().executemany(sql, rows)


def insert_df(sql: str, df) -> None:
    """Самый быстрый путь массовой записи в DuckDB: регистрация DataFrame
    как виртуальной таблицы `_df` + один INSERT ... SELECT ... FROM _df."""
    with _lock:
        con = get_con()
        con.register("_df", df)
        try:
            con.execute(sql)
        finally:
            con.unregister("_df")


def fetchall(sql: str, params: list | None = None) -> list[tuple]:
    with _lock:
        return get_con().execute(sql, params or []).fetchall()


def fetchdf(sql: str, params: list | None = None):
    with _lock:
        return get_con().execute(sql, params or []).fetchdf()


@contextmanager
def transaction():
    """Атомарная пачка записей: лок держится на всю транзакцию."""
    with _lock:
        con = get_con()
        con.execute("BEGIN")
        try:
            yield con
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise


def reset_for_tests(tmp_path: str) -> None:
    """Только для pytest: переключить БД на временный файл."""
    global _con
    with _lock:
        if _con is not None:
            _con.close()
        _con = duckdb.connect(tmp_path)
        _con.execute(SCHEMA_PATH.read_text())
