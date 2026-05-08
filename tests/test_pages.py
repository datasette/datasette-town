import pytest


async def _auth_cookie(ds, actor_id):
    cookie = ds.client.actor_cookie({"id": actor_id})
    return {"cookies": {"ds_actor": cookie}}


@pytest.mark.asyncio
async def test_town_list_page(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth = await _auth_cookie(ds, "user1")

    response = await ds.client.get("/test/-/town", **auth)
    assert response.status_code == 200
    assert "pageData" in response.text


@pytest.mark.asyncio
async def test_new_query_page(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth = await _auth_cookie(ds, "user1")

    response = await ds.client.get("/test/-/town/new", **auth)
    assert response.status_code == 200
    assert "pageData" in response.text


@pytest.mark.asyncio
async def test_query_detail_page(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth = await _auth_cookie(ds, "user1")

    # Create a query first
    resp = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "Detail Test", "sql": "select 1"},
        **auth,
    )
    query_id = resp.json()["id"]

    response = await ds.client.get(f"/test/-/town/q/{query_id}", **auth)
    assert response.status_code == 200
    assert "pageData" in response.text
    assert "Detail Test" in response.text


@pytest.mark.asyncio
async def test_plugin_is_installed(datasette_instance):
    ds = datasette_instance
    response = await ds.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-town" in installed_plugins
