import pytest
from datasette.app import Datasette


async def _auth_cookie(ds, actor_id):
    """Get an auth cookie for the given actor_id."""
    cookie = ds.client.actor_cookie({"id": actor_id})
    return {"cookies": {"ds_actor": cookie}}


@pytest.mark.asyncio
async def test_create_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth = await _auth_cookie(ds, "user1")

    response = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "My Query", "description": "test", "sql": "select 1", "is_public": False},
        **auth,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_and_get_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth = await _auth_cookie(ds, "user1")

    # Create
    response = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "Test", "sql": "select 1"},
        **auth,
    )
    query_id = response.json()["id"]

    # View detail page
    response = await ds.client.get(f"/test/-/town/q/{query_id}", **auth)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth = await _auth_cookie(ds, "user1")

    # Create
    resp = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "Original", "sql": "select 1"},
        **auth,
    )
    query_id = resp.json()["id"]

    # Update
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/update",
        json={"title": "Updated", "description": "", "sql": "select 2", "is_public": True},
        **auth,
    )
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_patch_query(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth = await _auth_cookie(ds, "user1")

    resp = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "Original", "sql": "select 1"},
        **auth,
    )
    query_id = resp.json()["id"]

    # Patch just the title
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/patch",
        json={"title": "Patched Title"},
        **auth,
    )
    assert resp.json()["ok"] is True

    # Verify title changed but sql didn't
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
    auth = await _auth_cookie(ds, "user1")

    resp = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "To Delete", "sql": "select 1"},
        **auth,
    )
    query_id = resp.json()["id"]

    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/delete",
        json={},
        **auth,
    )
    assert resp.json()["ok"] is True

    # Should be gone
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_shares_crud(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth1 = await _auth_cookie(ds, "user1")
    auth2 = await _auth_cookie(ds, "user2")

    # Create query as user1
    resp = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "Shared", "sql": "select 1"},
        **auth1,
    )
    query_id = resp.json()["id"]

    # Add share for user2
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/shares/add",
        json={"actor_id": "user2", "can_edit": False},
        **auth1,
    )
    assert resp.json()["ok"] is True
    share_id = resp.json()["id"]

    # List shares
    resp = await ds.client.get(
        f"/test/-/api/town/queries/{query_id}/shares",
        **auth1,
    )
    assert len(resp.json()["shares"]) == 1

    # user2 can view
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth2)
    assert resp.status_code == 200

    # Update share
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/shares/{share_id}/update",
        json={"can_edit": True},
        **auth1,
    )
    assert resp.json()["ok"] is True

    # Remove share
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/shares/{share_id}/remove",
        json={},
        **auth1,
    )
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_permission_denied_for_non_owner(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth1 = await _auth_cookie(ds, "user1")
    auth2 = await _auth_cookie(ds, "user2")

    # Create private query as user1
    resp = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "Private", "sql": "select 1", "is_public": False},
        **auth1,
    )
    query_id = resp.json()["id"]

    # user2 cannot view
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth2)
    assert resp.status_code == 403

    # user2 cannot delete
    resp = await ds.client.post(
        f"/test/-/api/town/queries/{query_id}/delete",
        json={},
        **auth2,
    )
    assert resp.json()["ok"] is False


@pytest.mark.asyncio
async def test_public_query_visible(datasette_instance):
    ds = datasette_instance
    await ds.invoke_startup()
    auth1 = await _auth_cookie(ds, "user1")
    auth2 = await _auth_cookie(ds, "user2")

    resp = await ds.client.post(
        "/test/-/api/town/queries/new",
        json={"title": "Public Q", "sql": "select 1", "is_public": True},
        **auth1,
    )
    query_id = resp.json()["id"]

    # user2 can view public query
    resp = await ds.client.get(f"/test/-/town/q/{query_id}", **auth2)
    assert resp.status_code == 200
