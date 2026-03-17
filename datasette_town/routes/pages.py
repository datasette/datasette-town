from pydantic import BaseModel

from datasette import Response

from ..page_data import (
    TownListPageData,
    NewQueryPageData,
    QueryDetailPageData,
    QuerySummary,
    ShareInfo,
)
from ..router import router, check_permission, TOWN_ACCESS_NAME, TOWN_CREATE_NAME
from ..internal_migrations import internal_migrations
from ..internal_db import InternalDB

from sqlite_utils import Database as SqliteUtilsDatabase


async def ensure_migrations(datasette):
    def migrate(connection):
        db = SqliteUtilsDatabase(connection)
        internal_migrations.apply(db)

    await datasette.get_internal_database().execute_write_fn(migrate)


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
    my_queries = []
    shared_queries = []

    if actor_id:
        my_raw = await idb.list_queries_for_actor(database, actor_id)
        my_queries = [QuerySummary(**q, can_edit=True) for q in my_raw]

        shared_raw = await idb.list_shared_queries_for_actor(database, actor_id)
        shared_queries = [
            QuerySummary(**{k: v for k, v in q.items() if k != "can_edit"}, can_edit=q.get("can_edit", False))
            for q in shared_raw
        ]

    public_raw = await idb.list_public_queries(database)
    public_queries = [QuerySummary(**q) for q in public_raw]

    return await render_page(
        datasette,
        request,
        page_title="Town",
        entrypoint="src/pages/town_list/index.ts",
        page_data=TownListPageData(
            database_name=database,
            my_queries=my_queries,
            shared_queries=shared_queries,
            public_queries=public_queries,
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
@check_permission()
async def query_detail_page(datasette, request, database: str, query_id: str):
    await ensure_migrations(datasette)
    idb = InternalDB(datasette.get_internal_database())

    query = await idb.get_query(query_id)
    if query is None:
        return Response.text("Query not found", status=404)

    actor_id = request.actor.get("id") if request.actor else None
    is_owner = actor_id is not None and query["actor_id"] == actor_id

    can_edit = is_owner
    if not is_owner and actor_id:
        share = await idb.get_share_for_actor(query_id, actor_id)
        if share and share["can_edit"]:
            can_edit = True
        elif not share and not query["is_public"]:
            return Response.text("Permission denied", status=403)
    elif not actor_id and not query["is_public"]:
        return Response.text("Permission denied", status=403)

    shares = []
    if is_owner:
        shares_raw = await idb.list_shares(query_id)
        shares = [ShareInfo(**s) for s in shares_raw]

    return await render_page(
        datasette,
        request,
        page_title=query["title"] or "Untitled Query",
        entrypoint="src/pages/query_detail/index.ts",
        page_data=QueryDetailPageData(
            database_name=database,
            query=QuerySummary(**query, can_edit=can_edit),
            shares=shares,
            is_owner=is_owner,
            can_edit=can_edit,
        ),
    )
