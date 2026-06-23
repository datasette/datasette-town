"""Throwaway seed + actor-name plugin for the doc screenshot script.

Loaded via ``datasette --plugins-dir`` from ``scripts/screenshots.mjs`` so the
self-contained shots run against deterministic data without the Node driver
having to reimplement the query / grant APIs.

It does two things, both dev/screenshot-only (NOT shipped):

1. ``actors_from_ids`` — friendly display names ("Alice Ada", …) so the share
   dialog's people list and the query author rows render real names instead of
   raw actor ids.

2. ``startup`` — seeds a demo ``sales`` table (so saved queries return real
   rows when executed) plus a handful of town queries with acl grants that
   populate every screenshot:
     * alice owns several queries (My Queries),
     * one query owned by bob is shared to alice as Editor (Shared with Me),
     * the headline query is shared to bob (Editor) + carol (Viewer) so the
       share dialog's people list has rows,
     * one query is shared with the public (everyone).
   Idempotent — skips a database that already has queries, so a re-run against
   a fresh throwaway DB always produces the same content.
"""

from datasette import hookimpl
from sqlite_utils import Database

DISPLAY_NAMES = {
    "alice": "Alice Ada",
    "bob": "Bob Babbage",
    "carol": "Carol Shaw",
}

DB_NAME = "data"

# Demo table so executing a saved query returns real rows in the results shot.
_SALES_ROWS = [
    ("West", "2026-Q1", 42000),
    ("West", "2026-Q2", 48000),
    ("East", "2026-Q1", 31000),
    ("East", "2026-Q2", 36000),
    ("North", "2026-Q1", 27000),
    ("South", "2026-Q2", 59000),
]

HEADLINE_SQL = (
    "select region, sum(revenue) as total_revenue\n"
    "from sales\n"
    "group by region\n"
    "order by total_revenue desc"
)

# (title, description, sql) for queries owned by alice.
_ALICE_QUERIES = [
    (
        "Revenue by region",
        "Total booked revenue per region across 2026.",
        HEADLINE_SQL,
    ),
    (
        "Q2 sales detail",
        "Every Q2 line item, largest first.",
        "select region, period, revenue\nfrom sales\nwhere period = '2026-Q2'\norder by revenue desc",
    ),
    (
        "Regions tracked",
        "Distinct regions currently reporting.",
        "select distinct region from sales order by region",
    ),
]


@hookimpl
def actors_from_ids(actor_ids):
    out = {}
    for aid in actor_ids:
        sid = str(aid)
        actor = {"id": sid}
        if sid in DISPLAY_NAMES:
            actor["name"] = DISPLAY_NAMES[sid]
        out[sid] = actor
    return out


@hookimpl
def startup(datasette):
    async def inner():
        from datasette_town.internal_migrations import internal_migrations
        from datasette_town.internal_db import InternalDB
        from datasette_town.permissions import seed_owner_manager_grant
        from datasette_town.resources import TOWN_QUERY_RESOURCE_TYPE
        from datasette_acl.internal_migrations import (
            internal_migrations as acl_migrations,
        )
        from datasette_acl.grants import grant, Principal

        internal = datasette.get_internal_database()

        # Ensure town + acl internal schemas exist regardless of plugin startup
        # order.
        def _migrate(conn):
            internal_migrations.apply(Database(conn))
            acl_migrations.apply(Database(conn))

        await internal.execute_write_fn(_migrate)

        idb = InternalDB(internal)

        for name, db_obj in datasette.databases.items():
            if name == "_internal" or not db_obj.is_mutable:
                continue

            # Demo data table (idempotent).
            def _seed_sales(conn):
                db = Database(conn)
                if "sales" not in db.table_names():
                    db["sales"].insert_all(
                        [
                            {"region": r, "period": p, "revenue": v}
                            for (r, p, v) in _SALES_ROWS
                        ]
                    )

            await db_obj.execute_write_fn(_seed_sales)

            # Skip query seeding if this database already has town queries.
            existing = await idb.list_queries_for_actor(name, "alice")
            if existing:
                continue

            async def make(actor_id, title, description, sql):
                qid = await idb.create_query(
                    database_name=name,
                    actor_id=actor_id,
                    title=title,
                    description=description,
                    sql=sql,
                )
                await seed_owner_manager_grant(datasette, name, qid, actor_id)
                return qid

            # alice's own queries. The first is the headline query used by the
            # detail / results / share-dialog shots.
            headline_id = None
            for title, description, sql in _ALICE_QUERIES:
                qid = await make("alice", title, description, sql)
                if headline_id is None:
                    headline_id = qid

            # Headline query shared with collaborators so the share dialog's
            # people-with-access list renders rows.
            await grant(
                datasette,
                TOWN_QUERY_RESOURCE_TYPE,
                name,
                headline_id,
                principal=Principal.actor("bob"),
                role="Editor",
                by_actor="alice",
            )
            await grant(
                datasette,
                TOWN_QUERY_RESOURCE_TYPE,
                name,
                headline_id,
                principal=Principal.actor("carol"),
                role="Viewer",
                by_actor="alice",
            )
            # And shared publicly so it carries a "public" grant too.
            await grant(
                datasette,
                TOWN_QUERY_RESOURCE_TYPE,
                name,
                headline_id,
                principal=Principal.everyone(),
                role="Viewer",
                by_actor="alice",
            )

            # A query owned by bob, shared to alice as Editor → shows up in
            # alice's "Shared with Me" section.
            shared_id = await make(
                "bob",
                "Pipeline by stage",
                "Open opportunities grouped by sales stage.",
                "select region, count(*) as deals\nfrom sales\ngroup by region",
            )
            await grant(
                datasette,
                TOWN_QUERY_RESOURCE_TYPE,
                name,
                shared_id,
                principal=Principal.actor("alice"),
                role="Editor",
                by_actor="bob",
            )

    return inner
