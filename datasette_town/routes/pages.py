from pydantic import BaseModel

from datasette import Response

from ..page_data import (
    TownListPageData,
    NewQueryPageData,
    QueryDetailPageData,
    QuerySummary,
    ActorInfo,
)
from ..router import (
    router,
    check_permission,
    TOWN_CREATE_NAME,
    TOWN_VIEW_NAME,
    TOWN_EDIT_NAME,
    TOWN_MANAGE_NAME,
)
from ..resources import TownQueryResource
from ..internal_migrations import internal_migrations
from ..internal_db import InternalDB

from sqlite_utils import Database as SqliteUtilsDatabase


async def ensure_migrations(datasette):
    def migrate(connection):
        db = SqliteUtilsDatabase(connection)
        internal_migrations.apply(db)

    await datasette.get_internal_database().execute_write_fn(migrate)


def _actor_info(request) -> ActorInfo | None:
    actor = request.actor
    if not actor or not actor.get("id"):
        return None
    return ActorInfo(
        id=actor["id"],
        name=actor.get("name") or actor.get("display") or actor.get("username"),
    )


async def render_page(
    datasette, request, *, page_title: str, entrypoint: str, page_data: BaseModel
) -> Response:
    return Response.html(
        await datasette.render_template(
            "town_base.html",
            {
                "page_title": page_title,
                "entrypoint": entrypoint,
                "page_data": page_data.model_dump(),
            },
            request=request,
        )
    )


@router.GET("/(?P<database>[^/]+)/-/town$")
@check_permission()
async def town_list_page(datasette, request, database: str):
    await ensure_migrations(datasette)
    idb = InternalDB(datasette.get_internal_database())

    actor_id = request.actor.get("id") if request.actor else None

    # datasette-acl decides which queries this actor may view (owner grant,
    # shares with them, group grants, and public/everyone grants all flow
    # through here). Filter to the current database via the parent.
    page = await datasette.allowed_resources(
        action=TOWN_VIEW_NAME,
        actor=request.actor,
        parent=database,
        limit=1000,
    )
    viewable_ids = [r.child for r in page.resources if r.child is not None]

    rows = await idb.get_queries_by_ids(viewable_ids)

    my_queries = []
    shared_queries = []
    for row in rows:
        is_mine = actor_id is not None and row["actor_id"] == actor_id
        summary = QuerySummary(**row, can_edit=is_mine)
        (my_queries if is_mine else shared_queries).append(summary)

    return await render_page(
        datasette,
        request,
        page_title="Town",
        entrypoint="src/pages/town_list/index.ts",
        page_data=TownListPageData(
            database_name=database,
            my_queries=my_queries,
            shared_queries=shared_queries,
        ),
    )


@router.GET("/(?P<database>[^/]+)/-/town/new$")
@check_permission(action=TOWN_CREATE_NAME)
async def new_query_page(datasette, request, database: str):
    await ensure_migrations(datasette)
    return await render_page(
        datasette,
        request,
        page_title="New Query",
        entrypoint="src/pages/new_query/index.ts",
        page_data=NewQueryPageData(database_name=database),
    )


@router.GET("/(?P<database>[^/]+)/-/town/q/(?P<query_id>[^/]+)$")
async def query_detail_page(datasette, request, database: str, query_id: str):
    await ensure_migrations(datasette)
    idb = InternalDB(datasette.get_internal_database())

    query = await idb.get_query(query_id)
    if query is None:
        return Response.text("Query not found", status=404)

    resource = TownQueryResource(database, query_id)

    can_view = await datasette.allowed(
        action=TOWN_VIEW_NAME, resource=resource, actor=request.actor
    )
    if not can_view:
        return Response.text("Permission denied", status=403)

    can_edit = await datasette.allowed(
        action=TOWN_EDIT_NAME, resource=resource, actor=request.actor
    )
    # "Owner" == can manage sharing (acl Manager role).
    is_owner = await datasette.allowed(
        action=TOWN_MANAGE_NAME, resource=resource, actor=request.actor
    )

    return await render_page(
        datasette,
        request,
        page_title=query["title"] or "Untitled Query",
        entrypoint="src/pages/query_detail/index.ts",
        page_data=QueryDetailPageData(
            database_name=database,
            query=QuerySummary(**query, can_edit=can_edit),
            is_owner=is_owner,
            can_edit=can_edit,
            actor=_actor_info(request),
        ),
    )
