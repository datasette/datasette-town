from typing import Annotated

from datasette import Response
from datasette_plugin_router import Body

from ..page_data import (
    CreateQueryRequest,
    UpdateQueryRequest,
    PatchQueryRequest,
)
from ..router import (
    router,
    check_permission,
    TOWN_CREATE_NAME,
    TOWN_EDIT_NAME,
    TOWN_MANAGE_NAME,
)
from ..resources import TownQueryResource
from ..permissions import seed_owner_manager_grant
from ..internal_db import InternalDB
from .pages import ensure_migrations


async def _get_actor_id(request):
    if request.actor:
        return request.actor.get("id")
    return None


async def _check_resource_permission(datasette, request, database, query_id, action):
    """Check resource-level permission via datasette.allowed(). Returns (query, error_response)."""
    idb = InternalDB(datasette.get_internal_database())
    query = await idb.get_query(query_id)
    if query is None:
        return None, Response.json(
            {"ok": False, "error": "Query not found"}, status=404
        )
    resource = TownQueryResource(database, query_id)
    if not await datasette.allowed(
        action=action, resource=resource, actor=request.actor
    ):
        return None, Response.json(
            {"ok": False, "error": "Permission denied"}, status=403
        )
    return query, None


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/new$")
@check_permission(action=TOWN_CREATE_NAME)
async def api_create_query(
    datasette, request, database: str, body: Annotated[CreateQueryRequest, Body()]
):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json(
            {"ok": False, "error": "Authentication required"}, status=401
        )

    idb = InternalDB(datasette.get_internal_database())

    query_id = await idb.create_query(
        database_name=database,
        actor_id=actor_id,
        title=body.title,
        description=body.description,
        sql=body.sql,
    )

    # Ownership is an acl Manager grant rather than an actor_id SQL rule: it
    # gives the creator view/edit/manage and lets them re-share via the dialog.
    await seed_owner_manager_grant(datasette, database, query_id, actor_id)

    return Response.json({"ok": True, "id": query_id})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/update$")
async def api_update_query(
    datasette,
    request,
    database: str,
    query_id: str,
    body: Annotated[UpdateQueryRequest, Body()],
):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json(
            {"ok": False, "error": "Authentication required"}, status=401
        )

    query, err = await _check_resource_permission(
        datasette, request, database, query_id, TOWN_EDIT_NAME
    )
    if err:
        return err

    idb = InternalDB(datasette.get_internal_database())
    await idb.update_query(
        query_id=query_id,
        title=body.title,
        description=body.description,
        sql=body.sql,
    )

    return Response.json({"ok": True})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/patch$")
async def api_patch_query(
    datasette,
    request,
    database: str,
    query_id: str,
    body: Annotated[PatchQueryRequest, Body()],
):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json(
            {"ok": False, "error": "Authentication required"}, status=401
        )

    query, err = await _check_resource_permission(
        datasette, request, database, query_id, TOWN_EDIT_NAME
    )
    if err:
        return err

    fields = body.model_dump(exclude_none=True)
    if fields:
        idb = InternalDB(datasette.get_internal_database())
        await idb.patch_query(query_id=query_id, **fields)

    return Response.json({"ok": True})


@router.POST("/(?P<database>[^/]+)/-/api/town/queries/(?P<query_id>[^/]+)/delete$")
async def api_delete_query(datasette, request, database: str, query_id: str):
    await ensure_migrations(datasette)
    actor_id = await _get_actor_id(request)
    if not actor_id:
        return Response.json(
            {"ok": False, "error": "Authentication required"}, status=401
        )

    query, err = await _check_resource_permission(
        datasette, request, database, query_id, TOWN_MANAGE_NAME
    )
    if err:
        return err

    idb = InternalDB(datasette.get_internal_database())
    await idb.delete_query(query_id)
    return Response.json({"ok": True})


@router.GET("/-/town/api/profile_queries$")
@check_permission()
async def api_profile_queries(datasette, request):
    await ensure_migrations(datasette)
    actor_id = request.args.get("actorId")
    if not actor_id:
        return Response.json({"data": []})

    db = datasette.get_internal_database()
    results = await db.execute(
        """
        SELECT
          id,
          database_name,
          title,
          description,
          updated_at,
          (strftime('%s', 'now') - strftime('%s', updated_at)) as updated_duration_seconds
        FROM datasette_town_queries
        WHERE actor_id = :actor_id
        ORDER BY updated_at DESC
        LIMIT 100
        """,
        {"actor_id": actor_id},
    )
    data = [dict(row) for row in results.rows]
    return Response.json({"data": data})
