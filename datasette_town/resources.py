from datasette.permissions import Resource


class TownQueryResource(Resource):
    name = "town-query"
    parent_class = None  # Top-level: parent=database_name, child=query_id

    def __init__(self, database: str, query_id: str):
        super().__init__(parent=database, child=query_id)

    @classmethod
    def resources_sql(cls) -> str:
        return "SELECT database_name AS parent, id AS child FROM datasette_town_queries"
