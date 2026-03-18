from pydantic import BaseModel

from datasette import Response

from ..page_data import (
    TownListPageData,
    NewQueryPageData,
    QueryDetailPageData,
    QuerySummary,
    ShareInfo,
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


async def _get_actor_pics(datasette, actor_ids):
    """Look up profile_picture_url for a set of actor IDs. Returns {id: url_or_None}."""
    unique_ids = set(actor_ids)
    if not unique_ids:
        return {}
    actors = await datasette.actors_from_ids(unique_ids)
    return {
        aid: actor.get("profile_picture_url") if isinstance(actor, dict) else None
        for aid, actor in actors.items()
    }


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

    # Look up profile pictures for all authors
    all_queries = my_queries + shared_queries + public_queries
    pics = await _get_actor_pics(datasette, [q.actor_id for q in all_queries])
    for q in all_queries:
        q.actor_profile_picture_url = pics.get(q.actor_id)

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
async def query_detail_page(datasette, request, database: str, query_id: str):
    await ensure_migrations(datasette)
    idb = InternalDB(datasette.get_internal_database())

    query = await idb.get_query(query_id)
    if query is None:
        return Response.text("Query not found", status=404)

    resource = TownQueryResource(database=database, query_id=query_id)

    # Check view permission (also_requires chain handles datasette-town-access)
    can_view = await datasette.allowed(action=TOWN_VIEW_NAME, resource=resource, actor=request.actor)
    if not can_view:
        return Response.text("Permission denied", status=403)

    can_edit = await datasette.allowed(action=TOWN_EDIT_NAME, resource=resource, actor=request.actor)
    is_owner = await datasette.allowed(action=TOWN_MANAGE_NAME, resource=resource, actor=request.actor)

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
            query=QuerySummary(
                **query,
                can_edit=can_edit,
                actor_profile_picture_url=(await _get_actor_pics(datasette, [query["actor_id"]])).get(query["actor_id"]),
            ),
            shares=shares,
            is_owner=is_owner,
            can_edit=can_edit,
        ),
    )
