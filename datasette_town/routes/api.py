from typing import Annotated

from datasette import Response
from datasette_plugin_router import Body

from ..page_data import (
    CreateQueryRequest,
    UpdateQueryRequest,
    AddShareRequest,
    UpdateShareRequest,
)
from ..router import router, check_permission, TOWN_CREATE_NAME
from ..internal_db import InternalDB
from .pages import ensure_migrations


async def _get_actor_id(request):
    if request.actor:
        return request.actor.get("id")
    return None


async def _check_owner(idb, query_id, actor_id):
    """Returns (query, error_response). If error_response is not None, return it."""
    query = await idb.get_query(query_id)
    if query is None:
        return None, Response.json({"ok": False, "error": "Query not found"}, status=404)
    if query["actor_id"] != actor_id:
        return None, Response.json({"ok": False, "error": "Permission denied"}, status=403)
    return query, None


async def _check_can_edit(idb, query_id, actor_id):
    """Returns (query, error_response). Allows owner or can_edit share."""
    query = await idb.get_query(query_id)
    if query is None:
        return None, Response.json({"ok": False, "error": "Query not found"}, status=404)
    if query["actor_id"] == actor_id:
        return query, None
    share = await idb.get_share_for_actor(query_id, actor_id)
    if share and share["can_edit"]:
        return query, None
    return None, Response.json({"ok": False, "error": "Permission denied"}, status=403)


async def _check_can_view(idb, query_id, actor_id):
    """Returns (query, error_response). Allows owner, shared, or public."""
    query = await idb.get_query(query_id)
    if query is None:
        return None, Response.json({"ok": False, "error": "Query not found"}, status=404)
    if query["is_public"]:
        return query, None
    if actor_id and query["actor_id"] == actor_id:
        return query, None
    if actor_id:
        share = await idb.get_share_for_actor(query_id, actor_id)
        if share:
            return query, None
    return None, Response.json({"ok": False, "error": "Permission denied"}, status=403)


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/new$")
@check_permission(action=TOWN_CREATE_NAME)
async def api_create_query(
    datasette, request, database: str, body: Annotated[CreateQueryRequest, Body()]
):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json({"ok": False, "error": "Authentication required"}, status=401)

    idb = InternalDB(datasette.get_internal_database())

    query_id = await idb.create_query(
        database_name=database,
        actor_id=actor_id,
        title=body.title,
        description=body.description,
        sql=body.sql,
        is_public=body.is_public,
    )

    return Response.json({"ok": True, "id": query_id})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/update$")
@check_permission()
async def api_update_query(
    datasette, request, database: str, query_id: str, body: Annotated[UpdateQueryRequest, Body()]
):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json({"ok": False, "error": "Authentication required"}, status=401)

    idb = InternalDB(datasette.get_internal_database())
    query, err = await _check_can_edit(idb, query_id, actor_id)
    if err:
        return err

    await idb.update_query(
        query_id=query_id,
        title=body.title,
        description=body.description,
        sql=body.sql,
        is_public=body.is_public,
    )

    return Response.json({"ok": True})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/delete$")
@check_permission()
async def api_delete_query(datasette, request, database: str, query_id: str):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json({"ok": False, "error": "Authentication required"}, status=401)

    idb = InternalDB(datasette.get_internal_database())
    query, err = await _check_owner(idb, query_id, actor_id)
    if err:
        return err

    await idb.delete_query(query_id)
    return Response.json({"ok": True})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/execute$")
@check_permission()
async def api_execute_query(datasette, request, database: str, query_id: str):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)

    idb = InternalDB(datasette.get_internal_database())
    query, err = await _check_can_view(idb, query_id, actor_id)
    if err:
        return err

    target_db = datasette.get_database(database)
    try:
        result = await target_db.execute(query["sql"], truncate=True)
        columns = [d[0] for d in result.description] if result.description else []
        rows = [list(row) for row in result.rows]
        truncated = result.truncated
        return Response.json({
            "ok": True,
            "columns": columns,
            "rows": rows[:1000],
            "truncated": truncated or len(rows) > 1000,
        })
    except Exception as e:
        return Response.json({"ok": True, "columns": [], "rows": [], "truncated": False, "error": str(e)})


@router.GET("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/shares$")
@check_permission()
async def api_list_shares(datasette, request, database: str, query_id: str):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json({"ok": False, "error": "Authentication required"}, status=401)

    idb = InternalDB(datasette.get_internal_database())
    query, err = await _check_owner(idb, query_id, actor_id)
    if err:
        return err

    shares = await idb.list_shares(query_id)
    return Response.json({"ok": True, "shares": shares})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/shares/add$")
@check_permission()
async def api_add_share(
    datasette, request, database: str, query_id: str, body: Annotated[AddShareRequest, Body()]
):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json({"ok": False, "error": "Authentication required"}, status=401)

    idb = InternalDB(datasette.get_internal_database())
    query, err = await _check_owner(idb, query_id, actor_id)
    if err:
        return err

    share_id = await idb.add_share(query_id, body.actor_id, body.can_edit)
    return Response.json({"ok": True, "id": share_id})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/shares/(?P<share_id>[^/]+)/remove$")
@check_permission()
async def api_remove_share(datasette, request, database: str, query_id: str, share_id: str):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json({"ok": False, "error": "Authentication required"}, status=401)

    idb = InternalDB(datasette.get_internal_database())
    query, err = await _check_owner(idb, query_id, actor_id)
    if err:
        return err

    await idb.remove_share(share_id)
    return Response.json({"ok": True})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/shares/(?P<share_id>[^/]+)/update$")
@check_permission()
async def api_update_share(
    datasette, request, database: str, query_id: str, share_id: str,
    body: Annotated[UpdateShareRequest, Body()]
):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json({"ok": False, "error": "Authentication required"}, status=401)

    idb = InternalDB(datasette.get_internal_database())
    query, err = await _check_owner(idb, query_id, actor_id)
    if err:
        return err

    await idb.update_share(share_id, body.can_edit)
    return Response.json({"ok": True})
