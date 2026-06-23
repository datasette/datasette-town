"""
Permission tests for the datasette-acl based sharing model.

Per-query access (view / edit / manage) is owned by datasette-acl. The query
creator is seeded a Manager grant; everything else is an acl grant for an actor,
a group, or a public audience. These tests drive that wiring through town's
routes and acl's grant helpers.

Coverage:
- Owner permissions (view, edit, delete) + seeded Manager grant
- Viewer / Editor role shares
- Public access (everyone / authenticated) + anonymous visitors
- Private query denial
- Global gate (datasette-town-access / -create)
- Share lifecycle: grant -> upgrade -> downgrade -> revoke
- Multi-query isolation
"""

import pytest
from datasette.app import Datasette

from conftest import (
    auth_cookie,
    create_query,
    grant_role,
    grant_public,
    revoke_actor,
)


@pytest.fixture
def ds_with_permissions(db_path):
    """access + create granted to all authenticated users."""
    return Datasette(
        [str(db_path)],
        config={
            "permissions": {
                "datasette-town-access": {"id": "*"},
                "datasette-town-create": {"id": "*"},
            }
        },
    )


@pytest.fixture
def ds_no_access(db_path):
    """No town access granted — tests global gate blocking."""
    return Datasette([str(db_path)])


@pytest.fixture
def ds_access_only(db_path):
    """Access granted but create not granted."""
    return Datasette(
        [str(db_path)],
        config={"permissions": {"datasette-town-access": {"id": "*"}}},
    )


# ============================================================
# Owner Permission Tests
# ============================================================


class TestOwnerPermissions:
    @pytest.mark.asyncio
    async def test_owner_can_view_own_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "owner1")
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_owner_can_edit_own_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "Updated", "sql": "select 2"},
            **auth_cookie(ds, "owner1"),
        )
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_owner_can_delete_own_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/delete",
            json={},
            **auth_cookie(ds, "owner1"),
        )
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_owner_detail_page_renders(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1", title="My Title")
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "owner1")
        )
        assert resp.status_code == 200
        assert "My Title" in resp.text


# ============================================================
# Viewer Role Tests
# ============================================================


class TestViewerSharePermissions:
    @pytest.mark.asyncio
    async def test_viewer_can_view_shared_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "viewer1", "Viewer", by="owner1")
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "viewer1")
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_edit_shared_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "viewer1", "Viewer", by="owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "Hacked", "sql": "select 2"},
            **auth_cookie(ds, "viewer1"),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_delete_shared_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "viewer1", "Viewer", by="owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/delete",
            json={},
            **auth_cookie(ds, "viewer1"),
        )
        assert resp.json()["ok"] is False


# ============================================================
# Editor Role Tests
# ============================================================


class TestEditorSharePermissions:
    @pytest.mark.asyncio
    async def test_editor_can_view_shared_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "editor1", "Editor", by="owner1")
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "editor1")
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_editor_can_edit_shared_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "editor1", "Editor", by="owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "Editor Updated", "sql": "select 2"},
            **auth_cookie(ds, "editor1"),
        )
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_editor_cannot_delete_shared_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "editor1", "Editor", by="owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/delete",
            json={},
            **auth_cookie(ds, "editor1"),
        )
        assert resp.json()["ok"] is False


# ============================================================
# Public Access Tests
# ============================================================


class TestPublicQueryAccess:
    @pytest.mark.asyncio
    async def test_public_query_viewable_by_other_user(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_public(ds, query_id, by="owner1")
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "stranger")
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_public_query_not_editable_by_stranger(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_public(ds, query_id, by="owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "Hacked", "sql": "select 2"},
            **auth_cookie(ds, "stranger"),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_authenticated_audience_grant(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_public(ds, query_id, principal_type="authenticated", by="owner1")
        # Signed-in stranger can view
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "stranger")
        )
        assert resp.status_code == 200
        # Anonymous cannot (authenticated audience only)
        resp = await ds.client.get(f"/test/-/town/q/{query_id}")
        assert resp.status_code == 403


# ============================================================
# Private Query Denial Tests
# ============================================================


class TestPrivateQueryDenial:
    @pytest.mark.asyncio
    async def test_private_query_not_viewable_by_stranger(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "stranger")
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_nonexistent_query_returns_404(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        resp = await ds.client.get(
            "/test/-/town/q/nonexistent", **auth_cookie(ds, "user1")
        )
        assert resp.status_code == 404


# ============================================================
# Anonymous User Tests
# ============================================================


class TestAnonymousAccess:
    @pytest.mark.asyncio
    async def test_anonymous_can_view_public_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_public(ds, query_id, by="owner1")
        resp = await ds.client.get(f"/test/-/town/q/{query_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_anonymous_cannot_view_private_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        resp = await ds.client.get(f"/test/-/town/q/{query_id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_anonymous_cannot_edit_public_query(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_public(ds, query_id, by="owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "Hacked", "sql": "drop table test_table"},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_requires_authentication(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        resp = await ds.client.post(
            "/test/-/api/town/queries/new",
            json={"title": "Anon Query", "sql": "select 1"},
        )
        assert resp.status_code in (401, 403)


# ============================================================
# Global Gate Tests
# ============================================================


class TestGlobalGate:
    @pytest.mark.asyncio
    async def test_no_access_blocks_town_list(self, ds_no_access):
        ds = ds_no_access
        await ds.invoke_startup()
        resp = await ds.client.get("/test/-/town", **auth_cookie(ds, "user1"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_no_access_blocks_query_create(self, ds_no_access):
        ds = ds_no_access
        await ds.invoke_startup()
        resp = await ds.client.post(
            "/test/-/api/town/queries/new",
            json={"title": "Test", "sql": "select 1"},
            **auth_cookie(ds, "user1"),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_access_without_create_blocks_new_query(self, ds_access_only):
        ds = ds_access_only
        await ds.invoke_startup()
        resp = await ds.client.post(
            "/test/-/api/town/queries/new",
            json={"title": "Test", "sql": "select 1"},
            **auth_cookie(ds, "user1"),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_access_without_create_can_view_list(self, ds_access_only):
        ds = ds_access_only
        await ds.invoke_startup()
        resp = await ds.client.get("/test/-/town", **auth_cookie(ds, "user1"))
        assert resp.status_code == 200


# ============================================================
# Share Lifecycle Tests
# ============================================================


class TestShareLifecycle:
    @pytest.mark.asyncio
    async def test_add_viewer_then_upgrade_to_editor(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "user2", "Viewer", by="owner1")

        # user2 can view but not edit
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "X", "sql": "select 2"},
            **auth_cookie(ds, "user2"),
        )
        assert resp.status_code == 403

        # Upgrade to Editor
        await grant_role(ds, query_id, "user2", "Editor", by="owner1")
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "User2 Edit", "sql": "select 2"},
            **auth_cookie(ds, "user2"),
        )
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_revoke_revokes_access(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "user2", "Viewer", by="owner1")

        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2")
        )
        assert resp.status_code == 200

        await revoke_actor(ds, query_id, "user2", by="owner1")
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2")
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_multiple_shares_independent(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "user2", "Viewer", by="owner1")
        await grant_role(ds, query_id, "user3", "Editor", by="owner1")

        await revoke_actor(ds, query_id, "user2", by="owner1")

        # user3 still has access and can edit
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user3")
        )
        assert resp.status_code == 200
        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/update",
            json={"title": "Edited by 3", "sql": "select 3"},
            **auth_cookie(ds, "user3"),
        )
        assert resp.json()["ok"] is True

        # user2 lost access
        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2")
        )
        assert resp.status_code == 403


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_queries_isolated_permissions(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_a = await create_query(ds, "owner1", title="Query A")
        query_b = await create_query(ds, "owner2", title="Query B")
        await grant_role(ds, query_a, "user3", "Editor", by="owner1")

        # user3 can view query_a but not query_b
        resp = await ds.client.get(
            f"/test/-/town/q/{query_a}", **auth_cookie(ds, "user3")
        )
        assert resp.status_code == 200
        resp = await ds.client.get(
            f"/test/-/town/q/{query_b}", **auth_cookie(ds, "user3")
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_removes_query_for_grantees(self, ds_with_permissions):
        ds = ds_with_permissions
        await ds.invoke_startup()
        query_id = await create_query(ds, "owner1")
        await grant_role(ds, query_id, "user2", "Editor", by="owner1")

        resp = await ds.client.post(
            f"/test/-/api/town/queries/{query_id}/delete",
            json={},
            **auth_cookie(ds, "owner1"),
        )
        assert resp.json()["ok"] is True

        resp = await ds.client.get(
            f"/test/-/town/q/{query_id}", **auth_cookie(ds, "user2")
        )
        assert resp.status_code == 404
