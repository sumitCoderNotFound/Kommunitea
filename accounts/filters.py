import django_filters
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileFilter(django_filters.FilterSet):
    """Rich filters for member discovery."""
    university = django_filters.CharFilter(field_name="university", lookup_expr="icontains")
    city = django_filters.CharFilter(field_name="city", lookup_expr="icontains")
    course = django_filters.CharFilter(field_name="course", lookup_expr="icontains")
    status = django_filters.CharFilter(field_name="status")  # visa/status
    skill = django_filters.CharFilter(method="filter_skill")
    looking_for = django_filters.CharFilter(method="filter_looking_for")

    class Meta:
        model = User
        fields = ["university", "city", "course", "status"]

    def filter_skill(self, queryset, name, value):
        return queryset.filter(skills__icontains=value)

    def filter_looking_for(self, queryset, name, value):
        return queryset.filter(looking_for__icontains=value)
