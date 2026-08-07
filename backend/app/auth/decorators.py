from functools import wraps

from flask_login import current_user

from app.utils.errors import ForbiddenError


def require_role(*roles):
    """Gate a route to one or more UserRole values."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                raise ForbiddenError("You do not have permission to perform this action")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_wgtk(fn):
    """Gate a route to any WGTK staff role."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.role.is_wgtk:
            raise ForbiddenError("WGTK staff only")
        return fn(*args, **kwargs)

    return wrapper


def require_client(fn):
    """Gate a route to any client-side role."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.role.is_client:
            raise ForbiddenError("Client portal users only")
        return fn(*args, **kwargs)

    return wrapper
