from rest_framework import serializers

from apps.plan.models import Plan


class PlanSerializer(serializers.ModelSerializer):
    """Plan owned by the requesting user.

    ``user`` is not a field: the view injects it from ``request.user``.
    ``start_Date`` defaults to now and ``end_Date`` to start + 7 days.
    """

    class Meta:
        model = Plan
        fields = ["id", "start_Date", "end_Date"]
