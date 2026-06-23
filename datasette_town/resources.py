from datasette.permissions import Resource

# Resource type name registered with datasette-acl. A town query is addressed
# as (resource_type="town-query", parent=database_name, child=query_id).
TOWN_QUERY_RESOURCE_TYPE = "town-query"


class TownDatabaseResource(Resource):
    """Parent level: the database a query lives in.

    Exists to satisfy datasette-acl's two-level resource hierarchy (it inspects
    ``parent_class`` to decide whether to pass a child). Not granted directly.
    """

    name = "town-database"
    parent_class = None

    @classmethod
    async def resources_sql(cls, datasette, actor=None) -> str:
        return (
            "SELECT DISTINCT database_name AS parent, NULL AS child "
            "FROM datasette_town_queries"
        )


class TownQueryResource(Resource):
    name = TOWN_QUERY_RESOURCE_TYPE
    parent_class = TownDatabaseResource  # parent=database_name, child=query_id

    def __init__(self, parent, child=None):
        # Accept (database, query_id) positionally so datasette-acl's
        # build_resource(rc, parent, child) works, while existing call sites
        # pass (database, query_id).
        super().__init__(
            parent=str(parent),
            child=str(child) if child is not None else None,
        )

    @classmethod
    async def resources_sql(cls, datasette, actor=None) -> str:
        return "SELECT database_name AS parent, id AS child FROM datasette_town_queries"
