import pytest

from conftest import auth_cookie, create_query, grant_role, grant_public


@pytest.mark.asyncio
async def test_create_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()

    response = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "My Query", "description": "test", "sql": "select 1"},
        **auth_cookie(ds, "user1"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_seeds_owner_manager_grant(datasette_instance):
    """Creating a query grants the creator the Manager role via acl."""
    from datasette_acl.grants import list_grants
    from datasette_town.resources import TOWN_QUERY_RESOURCE_TYPE

    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1")

    grants = await list_grants(ds, TOWN_QUERY_RESOURCE_TYPE, "test", query_id)
    actor_grants = [g for g in grants if g["principal"] == "actor"]
    assert len(actor_grants) == 1
    assert actor_grants[0]["actor_id"] == "user1"
    # Manager bundles view + edit + manage.
    assert {
        "datasette-town-view",
        "datasette-town-edit",
        "datasette-town-manage",
    } <= set(actor_grants[0]["actions"])


@pytest.mark.asyncio
async def test_create_and_get_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1", title="Test")

    response = await ds.client.get(
        f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user1")
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1", title="Original")

    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/update",
        json={"title": "Updated", "description": "", "sql": "select 2"},
        **auth_cookie(ds, "user1"),
    )
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_patch_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1", title="Original")
    auth = auth_cookie(ds, "user1")

    # Patch just the title
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/patch",
        json={"title": "Patched Title"},
        **auth,
    )
    assert resp.json()["ok"] is True

    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth)
    assert resp.status_code == 200
    assert "Patched Title" in resp.text

    # Patch just the sql
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/patch",
        json={"sql": "select 42"},
        **auth,
    )
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_delete_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1", title="To Delete")
    auth = auth_cookie(ds, "user1")

    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/delete", json={}, **auth
    )
    assert resp.json()["ok"] is True

    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_share_via_acl_grant(datasette_instance):
    """A Viewer grant lets another actor view but not edit."""
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "owner1")

    await grant_role(ds, query_id, "user2", "Viewer", by="owner1")

    # user2 can view
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2"))
    assert resp.status_code == 200

    # ...but not edit
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/update",
        json={"title": "x", "sql": "y"},
        **auth_cookie(ds, "user2"),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_share_over_acl_http_api(datasette_instance):
    """End-to-end: the owner grants via the acl JSON API (what the share dialog
    calls), then the grantee can view."""
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "owner1")

    # Owner is a manager, so the acl read endpoint reports can_manage.
    resp = await ds.client.get(
        f"/-/acl/api/resource/town-query/test/{query_id}",
        **auth_cookie(ds, "owner1"),
    )
    assert resp.status_code == 200
    assert resp.json()["can_manage"] is True

    # Grant user2 the Editor role through the acl API.
    resp = await ds.client.post(
        f"/-/acl/api/resource/town-query/test/{query_id}/grant",
        json={"actor_id": "user2", "role": "Editor"},
        **auth_cookie(ds, "owner1"),
    )
    assert resp.status_code == 200, resp.text

    # user2 can now view and edit.
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2"))
    assert resp.status_code == 200
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/update",
        json={"title": "Edited", "sql": "select 2"},
        **auth_cookie(ds, "user2"),
    )
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_non_manager_cannot_use_acl_api(datasette_instance):
    """A non-owner cannot read or write grants through the acl API."""
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "owner1")
    await grant_role(ds, query_id, "viewer1", "Viewer", by="owner1")

    # Viewer is not a manager.
    resp = await ds.client.get(
        f"/-/acl/api/resource/town-query/test/{query_id}",
        **auth_cookie(ds, "viewer1"),
    )
    assert resp.status_code == 403

    resp = await ds.client.post(
        f"/-/acl/api/resource/town-query/test/{query_id}/grant",
        json={"actor_id": "evil", "role": "Manager"},
        **auth_cookie(ds, "viewer1"),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_permission_denied_for_non_owner(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1", title="Private")

    # user2 cannot view
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2"))
    assert resp.status_code == 403

    # user2 cannot delete
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/delete",
        json={},
        **auth_cookie(ds, "user2"),
    )
    assert resp.json()["ok"] is False


@pytest.mark.asyncio
async def test_public_query_visible(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    query_id = await create_query(ds, "user1", title="Public Q")
    await grant_public(ds, query_id, by="user1")

    # user2 can view a public query
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2"))
    assert resp.status_code == 200
