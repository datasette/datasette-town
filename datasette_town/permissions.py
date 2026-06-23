"""ACL integration: roles + ownership grant seeding.

Per-query access (view / edit / manage) is owned by datasette-acl. Town
registers the resource type + actions (see ``resources.py`` / ``__init__.py``)
and seeds the creator a Manager grant; everything else (sharing with people,
groups, or the public) flows through datasette-acl's JSON API and the
``<datasette-acl-share-dialog>`` component.
"""

from datasette_acl.grants import grant, Principal
from datasette_acl.roles import standard_roles

from .resources import TOWN_QUERY_RESOURCE_TYPE
from .router import TOWN_VIEW_NAME, TOWN_EDIT_NAME, TOWN_MANAGE_NAME


def town_query_roles():
    """Viewer / Editor / Manager roles for the town-query resource type."""
    return standard_roles(
        TOWN_QUERY_RESOURCE_TYPE,
        view=TOWN_VIEW_NAME,
        edit=TOWN_EDIT_NAME,
        manage=TOWN_MANAGE_NAME,
        descriptions={
            "Viewer": "Can view and run the query",
            "Editor": "Can view and edit the query",
            "Manager": "Can view, edit, and manage sharing",
        },
    )


async def seed_owner_manager_grant(datasette, database, query_id, actor_id):
    """Grant the query's creator the Manager role (= ownership) on a new query.

    No-op for anonymous creates (no actor_id). Replaces the old created_by /
    shares-table ownership rule with an acl grant.
    """
    if not actor_id:
        return
    await grant(
        datasette,
        TOWN_QUERY_RESOURCE_TYPE,
        str(database),
        str(query_id),
        principal=Principal.actor(str(actor_id)),
        role="Manager",
        by_actor=str(actor_id),
    )
