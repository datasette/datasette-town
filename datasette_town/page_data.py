from pydantic import BaseModel


class QuerySummary(BaseModel):
    id: str
    database_name: str
    actor_id: str
    title: str
    description: str
    sql: str
    is_public: bool
    created_at: str
    updated_at: str
    can_edit: bool = False


class ShareInfo(BaseModel):
    id: str
    query_id: str
    actor_id: str
    can_edit: bool
    created_at: str


# /{db}/-/town — list page
class TownListPageData(BaseModel):
    database_name: str
    my_queries: list[QuerySummary] = []
    shared_queries: list[QuerySummary] = []
    public_queries: list[QuerySummary] = []


# /{db}/-/town/new — new query form
class NewQueryPageData(BaseModel):
    database_name: str


# /{db}/-/town/q/{id} — query detail
class QueryDetailPageData(BaseModel):
    database_name: str
    query: QuerySummary
    shares: list[ShareInfo] = []
    is_owner: bool = False
    can_edit: bool = False


# API request/response models
class CreateQueryRequest(BaseModel):
    title: str = ""
    description: str = ""
    sql: str = ""
    is_public: bool = False


class UpdateQueryRequest(BaseModel):
    title: str = ""
    description: str = ""
    sql: str = ""
    is_public: bool = False


class AddShareRequest(BaseModel):
    actor_id: str
    can_edit: bool = False


class UpdateShareRequest(BaseModel):
    can_edit: bool


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
