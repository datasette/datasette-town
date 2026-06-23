import os
import pytest
import sqlite3

from datasette.app import Datasette
from datasette_acl.grants import grant, revoke, Principal

from datasette_town.resources import TOWN_QUERY_RESOURCE_TYPE

# Use dev mode for vite so we don't need a built manifest
os.environ["DATASETTE_TOWN_VITE_PATH"] = "http://localhost:5180/"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE test_table (id integer primary key, name text)")
    conn.execute("INSERT INTO test_table VALUES (1, 'alice')")
    conn.execute("INSERT INTO test_table VALUES (2, 'bob')")
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def datasette_instance(db_path):
    return Datasette(
        [str(db_path)],
        config={
            "permissions": {
                "datasette-town-access": {"id": "*"},
                "datasette-town-create": {"id": "*"},
            }
        },
    )


# ---------------------------------------------------------------------------
# Shared test helpers
#
# Sharing is owned by datasette-acl now. In production the
# <datasette-acl-share-dialog> calls acl's JSON API; in tests we either call
# acl's grant()/revoke() Python helpers directly (what those endpoints do) or
# hit the acl HTTP API to exercise the full dialog path.
# ---------------------------------------------------------------------------


def auth_cookie(ds, actor_id):
    """Return kwargs that authenticate ds.client requests as actor_id."""
    return {"cookies": {"ds_actor": ds.client.actor_cookie({"id": actor_id})}}


async def create_query(
    ds,
    actor_id,
    *,
    database="test",
    title="Test Query",
    description="",
    sql="select 1",
):
    """Create a query via the town API; returns its id."""
    resp = await ds.client.post(
        f"/{database}/-/api/town/queries/new",
        json={"title": title, "description": description, "sql": sql},
        **auth_cookie(ds, actor_id),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    return data["id"]


async def grant_role(ds, query_id, actor_id, role, *, database="test", by="owner1"):
    """Grant an actor a role (Viewer/Editor/Manager) on a query via acl."""
    await grant(
        ds,
        TOWN_QUERY_RESOURCE_TYPE,
        database,
        query_id,
        principal=Principal.actor(str(actor_id)),
        role=role,
        by_actor=by,
    )


async def grant_public(
    ds, query_id, *, database="test", principal_type="everyone", by="owner1"
):
    """Make a query viewable by a public audience (everyone/authenticated)."""
    await grant(
        ds,
        TOWN_QUERY_RESOURCE_TYPE,
        database,
        query_id,
        principal=Principal.public(principal_type),
        role="Viewer",
        by_actor=by,
    )


async def revoke_actor(ds, query_id, actor_id, *, database="test", by="owner1"):
    """Revoke all of an actor's grants on a query via acl."""
    await revoke(
        ds,
        TOWN_QUERY_RESOURCE_TYPE,
        database,
        query_id,
        principal=Principal.actor(str(actor_id)),
        by_actor=by,
    )
