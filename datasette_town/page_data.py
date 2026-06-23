from pydantic import BaseModel


class QuerySummary(BaseModel):
    id: str
    database_name: str
    actor_id: str
    title: str
    description: str
    sql: str
    created_at: str
    updated_at: str
    can_edit: bool = False


# Minimal actor info seeded for the <datasette-acl-share-dialog> ("(you)" row).
class ActorInfo(BaseModel):
    id: str
    name: str | None = None


# /{db}/-/town — list page
class TownListPageData(BaseModel):
    database_name: str
    my_queries: list[QuerySummary] = []
    shared_queries: list[QuerySummary] = []


# /{db}/-/town/new — new query form
class NewQueryPageData(BaseModel):
    database_name: str


# /{db}/-/town/q/{id} — query detail
class QueryDetailPageData(BaseModel):
    database_name: str
    query: QuerySummary
    is_owner: bool = False
    can_edit: bool = False
    actor: ActorInfo | None = None


# API request/response models
class CreateQueryRequest(BaseModel):
    title: str = ""
    description: str = ""
    sql: str = ""


class UpdateQueryRequest(BaseModel):
    title: str = ""
    description: str = ""
    sql: str = ""


class PatchQueryRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    sql: str | None = None


class ExecuteQueryResponse(BaseModel):
    columns: list[str] = []
    rows: list[list] = []
    truncated: bool = False
    error: str | None = None


__exports__ = [
    TownListPageData,
    NewQueryPageData,
    QueryDetailPageData,
]
