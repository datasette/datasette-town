import pytest

from conftest import auth_cookie, create_query, grant_role


@pytest.mark.asyncio
async def test_town_list_page(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()

    response = await ds.client.get("/test/-/town", **auth_cookie(ds, "user1"))
    assert response.status_code == 200
    assert "pageData" in response.text


@pytest.mark.asyncio
async def test_town_list_splits_mine_and_shared(datasette_instance):
    """The list page is built from acl grants: owned queries land in my_queries,
    queries shared with the actor land in shared_queries."""
    ds = datasette_instance
    await ds.invoke_startup()

    mine = await create_query(ds, "user1", title="Mine")
    theirs = await create_query(ds, "owner2", title="Theirs")
    await grant_role(ds, theirs, "user1", "Viewer", by="owner2")
    # A query user1 has no grant on must not appear.
    await create_query(ds, "owner3", title="Hidden")

    response = await ds.client.get("/test/-/town", **auth_cookie(ds, "user1"))
    assert response.status_code == 200
    body = response.text
    assert mine in body
    assert theirs in body
    assert "Mine" in body
    assert "Theirs" in body
    assert "Hidden" not in body


@pytest.mark.asyncio
async def test_new_query_page(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()

    response = await ds.client.get("/test/-/town/new", **auth_cookie(ds, "user1"))
    assert response.status_code == 200
    assert "pageData" in response.text


@pytest.mark.asyncio
async def test_query_detail_page(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1", title="Detail Test")

    response = await ds.client.get(
        f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user1")
    )
    assert response.status_code == 200
    assert "pageData" in response.text
    assert "Detail Test" in response.text


@pytest.mark.asyncio
async def test_query_detail_page_loads_share_assets(datasette_instance):
    """The query detail page opts into the datasette-acl-share bundle."""
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1")

    response = await ds.client.get(
        f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user1")
    )
    assert "datasette_acl_share" in response.text


@pytest.mark.asyncio
async def test_plugin_is_installed(datasette_instance):
    ds = datasette_instance
    response = await ds.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-town" in installed_plugins
