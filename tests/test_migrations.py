import pytest


@pytest.mark.asyncio
async def test_migrations_create_tables(datasette_instance):
    ds = datasette_instance
    # Trigger startup which runs migrations
    await ds.invoke_startup()

    internal_db = ds.get_internal_database()
    result = await internal_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'datasette_town_%'"
    )
    table_names = {row[0] for row in result.rows}
    # The queries table exists; sharing now lives in datasette-acl, so there is
    # no town shares table.
    assert "datasette_town_queries" in table_names
    assert "datasette_town_shares" not in table_names


@pytest.mark.asyncio
async def test_queries_table_has_no_is_public(datasette_instance):
    """Public access is an acl grant now, not an is_public column."""
    ds = datasette_instance
    await ds.invoke_startup()

    internal_db = ds.get_internal_database()
    result = await internal_db.execute("PRAGMA table_info(datasette_town_queries)")
    columns = {row["name"] for row in result.rows}
    assert "is_public" not in columns
    assert {"id", "database_name", "actor_id", "title", "sql"} <= columns
