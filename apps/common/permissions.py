from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    """
    Permission check for system Owner / Admin only.
    """
    message = "Access restricted to Owner only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == "OWNER" or request.user.is_superuser)
        )


class IsManagerOrOwner(permissions.BasePermission):
    """
    Permission check for Manager or Owner.
    """
    message = "Access restricted to Manager or Owner."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role in ["OWNER", "MANAGER"] or request.user.is_superuser)
        )


class IsDriver(permissions.BasePermission):
    """
    Permission check for Drivers only.
    """
    message = "Access restricted to Drivers."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "DRIVER"
        )


class IsAssignedDriverOrManagerOwner(permissions.BasePermission):
    """
    Object-level permission allowing:
    - Owners & Managers full access
    - Assigned Driver access only to their own deliveries/orders/routes.
    """
    message = "You do not have permission to access records belonging to other drivers or routes."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Owners and managers have full access
        if request.user.is_superuser or request.user.role in ["OWNER", "MANAGER"]:
            return True

        # Drivers can only access records assigned to them
        if request.user.role == "DRIVER":
            # Check obj directly or through related driver attribute
            if hasattr(obj, "driver") and obj.driver:
                return obj.driver.user_id == request.user.id
            if hasattr(obj, "user"):
                return obj.user_id == request.user.id
            if hasattr(obj, "order") and hasattr(obj.order, "driver") and obj.order.driver:
                return obj.order.driver.user_id == request.user.id

        return False
