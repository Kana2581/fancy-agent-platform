"""Unit tests for SQLite compatibility layer (app/utils/db_compat.py)."""
import pytest
from sqlalchemy import Text, event
from sqlalchemy.ext.asyncio import create_async_engine

from app.utils.db_compat import IS_SQLITE, LargeText


class TestIsSqliteFlag:
    def test_flag_matches_configured_url(self):
        from app.core.config import settings
        expected = settings.DATABASE_URL.startswith("sqlite")
        assert IS_SQLITE is expected

    def test_sqlite_url_would_be_detected(self):
        assert "sqlite+aiosqlite:///./test.db".startswith("sqlite") is True

    def test_mysql_url_would_not_be_detected(self):
        assert "mysql+asyncmy://root:pass@localhost/db".startswith("sqlite") is False


class TestLargeText:
    def test_is_text_instance(self):
        assert isinstance(LargeText, Text)

    def test_has_mysql_longtext_variant(self):
        from sqlalchemy.dialects.mysql import LONGTEXT

        mysql_variant = LargeText._variant_mapping.get("mysql")
        assert mysql_variant is not None
        assert isinstance(mysql_variant, LONGTEXT)

    def test_sqlite_falls_back_to_text(self):
        # When compiled for SQLite, no variant is applied — stays as TEXT
        from sqlalchemy.dialects import sqlite as sqlite_dialect
        compiled = LargeText.compile(dialect=sqlite_dialect.dialect())
        assert "TEXT" in str(compiled).upper()

    def test_mysql_compiles_to_longtext(self):
        from sqlalchemy.dialects import mysql as mysql_dialect
        compiled = LargeText.compile(dialect=mysql_dialect.dialect())
        assert "LONGTEXT" in str(compiled).upper()


class TestFkPragma:
    async def test_pragma_foreign_keys_on(self):
        """After registering the same event hook as database.py, FK enforcement is active."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        @event.listens_for(engine.sync_engine, "connect")
        def _fk_on(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        results = []

        @event.listens_for(engine.sync_engine, "connect")
        def _read_pragma(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys")
            results.append(cur.fetchone()[0])
            cur.close()

        async with engine.connect():
            pass

        await engine.dispose()
        assert results[0] == 1

    async def test_without_pragma_fk_is_off_by_default(self):
        """Baseline: raw SQLite does NOT enforce FK constraints unless told to."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        results = []

        @event.listens_for(engine.sync_engine, "connect")
        def _read_pragma(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys")
            results.append(cur.fetchone()[0])
            cur.close()

        async with engine.connect():
            pass

        await engine.dispose()
        assert results[0] == 0
