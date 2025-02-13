from django_filters import rest_framework as filters

from .models import Job


class JobFilterSet(filters.FilterSet):
    """Filterset to allow filtering file names"""

    def accession_filter(queryset, name, value):
        return queryset.filter(**{f"result__{name}__accession__icontains": value})

    def alias_filter(queryset, name, value):
        return queryset.filter(**{f"submission__{name}__icontains": value})

    files = filters.CharFilter(lookup_expr="icontains")

    # Accession filters
    sample = filters.CharFilter(label="Sample", method=accession_filter)
    experiment = filters.CharFilter(label="Experiment", method=accession_filter)
    run = filters.CharFilter(label="Run", method=accession_filter)

    # Alias filters
    sample__alias = filters.CharFilter(label="Sample alias", method=alias_filter)
    experiment__alias = filters.CharFilter(
        label="Experiment alias", method=alias_filter
    )
    run__alias = filters.CharFilter(label="Run alias", method=alias_filter)

    class Meta:
        model = Job
        fields = ("status", "action", "sample", "experiment", "run", "files")
