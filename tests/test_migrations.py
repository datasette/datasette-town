import pytest
from datasette.app import Datasette


@pytest.mark.asyncio
async def test_migrations_create_tables(datasette_instance):
    ds = datasette_instance
    # Trigger startup which runs migrations
    await ds.invoke_startup()

    internal_db = ds.get_internal_database()
    # Check tables exist
    result = await internal_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'datasette_town_%'"
    )
    table_names = {row[0] for row in result.rows}
    assert "datasette_town_queries" in table_names
    assert "datasette_town_shares" in table_names
