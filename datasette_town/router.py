from functools import wraps

from datasette import Forbidden
from datasette_plugin_router import Router

router = Router()

TOWN_ACCESS_NAME = "datasette-town-access"
TOWN_CREATE_NAME = "datasette-town-create"
TOWN_VIEW_SHARED_NAME = "datasette-town-view-shared"
TOWN_EDIT_SHARED_NAME = "datasette-town-edit-shared"


def check_permission(action=None):
    """Decorator for routes requiring town access."""
    action_name = action or TOWN_ACCESS_NAME

    def decorator(func):
        @wraps(func)
        async def wrapper(datasette, request, **kwargs):
            result = await datasette.allowed(
                action=action_name, actor=request.actor
            )
            if not result:
                raise Forbidden(f"Permission denied for {action_name}")
            return await func(datasette=datasette, request=request, **kwargs)

        return wrapper

    return decorator
