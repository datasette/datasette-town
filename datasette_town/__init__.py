from datasette import hookimpl
from datasette.permissions import Action
from datasette_vite import vite_entry
from sqlite_utils import Database
import os

from .internal_migrations import internal_migrations
from .router import (
    router,
    TOWN_ACCESS_NAME,
    TOWN_CREATE_NAME,
    TOWN_VIEW_SHARED_NAME,
    TOWN_EDIT_SHARED_NAME,
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
            name=TOWN_VIEW_SHARED_NAME,
            description="Can view queries shared with them",
        ),
        Action(
            name=TOWN_EDIT_SHARED_NAME,
            description="Can edit queries where they have edit access",
        ),
    ]


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
