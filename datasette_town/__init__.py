from datasette import hookimpl
from datasette.permissions import Action, PermissionSQL
from datasette_vite import vite_entry, vite_js_urls, vite_css_urls
from sqlite_utils import Database

try:
    from datasette_sidebar.hookspecs import SidebarApp

    _has_sidebar = True
except ImportError:
    _has_sidebar = False

try:
    from datasette_user_profiles.hookspecs import ProfileSection

    _has_user_profiles = True
except ImportError:
    _has_user_profiles = False

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
        internal_migrations.apply(db)  # ty: ignore[unresolved-attribute]

    await datasette.get_internal_database().execute_write_fn(migrate)


@hookimpl
def register_routes():
    return router.routes()  # ty: ignore[unresolved-attribute]


@hookimpl
def extra_template_vars(datasette):
    entry = vite_entry(
        datasette=datasette,
        plugin_package="datasette_town",
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


if _has_sidebar:

    @hookimpl
    def datasette_sidebar_apps(datasette):
        databases = [
            db for db in datasette.databases.values() if db.name != "_internal"
        ]
        if len(databases) == 1:
            href = f"/{databases[0].name}/-/town"
        else:
            href = "/-/town"
        return [
            SidebarApp(
                label="Town",
                description="Write and share SQL queries",
                href=href,
                icon='<svg viewBox="0 0 16 16" fill="currentColor"><path d="M14.763.075A.5.5 0 0 1 15 .5v15a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5V14h-1v1.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5V10a.5.5 0 0 1 .342-.474L6 7.64V4.5a.5.5 0 0 1 .276-.447l8-4a.5.5 0 0 1 .487.022M6 8.694 1 10.36V15h5zM7 15h2v-1.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5V15h2V1.309l-7 3.5z"/><path d="M2 11h1v1H2zm2 0h1v1H4zm-2 2h1v1H2zm2 0h1v1H4zm4-4h1v1H8zm2 0h1v1h-1zm-2 2h1v1H8zm2 0h1v1h-1zm2-2h1v1h-1zm0 2h1v1h-1zM8 7h1v1H8zm2 0h1v1h-1zm2 0h1v1h-1zM8 5h1v1H8zm2 0h1v1h-1zm2 0h1v1h-1zm0-2h1v1h-1z"/></svg>',
                color="#6d28d9",
            ),
        ]


PROFILE_SECTION_ENTRYPOINT = "src/pages/profile_section/index.ts"

if _has_user_profiles:

    @hookimpl
    def datasette_user_profile_sections(datasette):
        js_urls = [
            u["url"]
            for u in vite_js_urls(
                datasette,
                entrypoint=PROFILE_SECTION_ENTRYPOINT,
                plugin_package="datasette_town",
            )
        ]
        css_urls = vite_css_urls(
            datasette,
            entrypoint=PROFILE_SECTION_ENTRYPOINT,
            plugin_package="datasette_town",
        )
        return [
            ProfileSection(
                id="town-queries",
                label="Saved Queries",
                tag_name="profile-town-queries",
                js_urls=js_urls,
                css_urls=css_urls,
                sort_order=60,
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
