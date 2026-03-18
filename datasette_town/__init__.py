from datasette import hookimpl
from datasette.permissions import Action, PermissionSQL
from datasette_vite import vite_entry
from sqlite_utils import Database
import os

from .internal_migrations import internal_migrations
from .resources import TownQueryResource
from .router import (
    router,
    TOWN_ACCESS_NAME,
    TOWN_CREATE_NAME,
    TOWN_VIEW_NAME,
    TOWN_EDIT_NAME,
    TOWN_MANAGE_NAME,
)

# Import route modules to trigger route registration on the shared router
from .routes import pages, api

_ = (pages, api)


@hookimpl
async def startup(datasette):
    def migrate(connection):
        db = Database(connection)
        internal_migrations.apply(db)

    await datasette.get_internal_database().execute_write_fn(migrate)


@hookimpl
def register_routes():
    return router.routes()


@hookimpl
def extra_template_vars(datasette):
    entry = vite_entry(
        datasette=datasette,
        plugin_package="datasette_town",
        vite_dev_path=os.environ.get("DATASETTE_TOWN_VITE_PATH"),
    )
    return {"datasette_town_vite_entry": entry}


@hookimpl
def register_actions(datasette):
    return [
        Action(
            name=TOWN_ACCESS_NAME,
            description="Can access the town feature",
        ),
        Action(
            name=TOWN_CREATE_NAME,
            description="Can create new queries for a database",
        ),
        Action(
            name=TOWN_VIEW_NAME,
            description="Can view/execute a town query",
            resource_class=TownQueryResource,
        ),
        Action(
            name=TOWN_EDIT_NAME,
            description="Can edit a town query",
            resource_class=TownQueryResource,
            also_requires=TOWN_VIEW_NAME,
        ),
        Action(
            name=TOWN_MANAGE_NAME,
            description="Can share/delete a town query",
            resource_class=TownQueryResource,
            also_requires=TOWN_EDIT_NAME,
        ),
    ]


@hookimpl
def permission_resources_sql(datasette, actor, action):
    actor_id = actor.get("id") if actor else None

    if action == TOWN_VIEW_NAME:
        return PermissionSQL(
            sql="""
                SELECT q.database_name AS parent, q.id AS child, 1 AS allow, 'query owner' AS reason
                FROM datasette_town_queries q WHERE q.actor_id = :actor_id
                UNION ALL
                SELECT q.database_name AS parent, q.id AS child, 1 AS allow, 'shared with actor' AS reason
                FROM datasette_town_queries q JOIN datasette_town_shares s ON s.query_id = q.id
                WHERE s.actor_id = :actor_id
                UNION ALL
                SELECT q.database_name AS parent, q.id AS child, 1 AS allow, 'public query' AS reason
                FROM datasette_town_queries q WHERE q.is_public = 1
            """,
            params={"actor_id": actor_id},
        )
    elif action == TOWN_EDIT_NAME:
        return PermissionSQL(
            sql="""
                SELECT q.database_name AS parent, q.id AS child, 1 AS allow, 'query owner' AS reason
                FROM datasette_town_queries q WHERE q.actor_id = :actor_id
                UNION ALL
                SELECT q.database_name AS parent, q.id AS child, 1 AS allow, 'editor share' AS reason
                FROM datasette_town_queries q JOIN datasette_town_shares s ON s.query_id = q.id
                WHERE s.actor_id = :actor_id AND s.can_edit = 1
            """,
            params={"actor_id": actor_id},
        )
    elif action == TOWN_MANAGE_NAME:
        return PermissionSQL(
            sql="""
                SELECT q.database_name AS parent, q.id AS child, 1 AS allow, 'query owner' AS reason
                FROM datasette_town_queries q WHERE q.actor_id = :actor_id
            """,
            params={"actor_id": actor_id},
        )
    return None


@hookimpl
def database_actions(datasette, actor, database):
    async def inner():
        if actor and (await datasette.allowed(action=TOWN_ACCESS_NAME, actor=actor)):
            return [
                {
                    "href": datasette.urls.path(f"/{database}/-/town"),
                    "label": "Town",
                    "description": "Write and share SQL queries",
                }
            ]
        return []

    return inner
