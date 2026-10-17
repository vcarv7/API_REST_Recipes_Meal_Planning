from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Reads are public; writes require being the recipe's creator.

    Works for Recipe and RecipeIngredient objects (resolves the parent
    recipe). Recipes without an owner (created_by=None) are staff-only.
    """

    message = "Solo el creador puede modificar esta receta."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        recipe = getattr(obj, "recipe", obj)
        if recipe.created_by is None:
            return bool(request.user and request.user.is_staff)
        return recipe.created_by == request.user
