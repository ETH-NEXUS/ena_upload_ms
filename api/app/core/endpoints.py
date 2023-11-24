from drf_auto_endpoint.endpoints import Endpoint
from .models import Job, File, AnalysisJob, AnalysisFile
from .views import JobViewset, FileViewset, AnalysisJobViewset, AnalysisFileViewset
from drf_auto_endpoint.router import register


class DefaultEndpoint(Endpoint):
    """The default Endpoint"""

    include_str = False

    def get_url(self):
        """The core endpoint defaults to not include the application name in the apis url."""
        if hasattr(self, "url") and self.url is not None:
            return self.url

        return "{}".format(self.model_name.replace("_", "-"))


@register
class JobEndpoint(DefaultEndpoint):
    model = Job
    base_viewset = JobViewset
    filter_fields = ("status",)


@register
class FileEndpoint(DefaultEndpoint):
    model = File
    base_viewset = FileViewset


@register
class AnalysisJobEndpoint(DefaultEndpoint):
    model = AnalysisJob
    base_viewset = AnalysisJobViewset
    filter_fields = ("status",)


@register
class AnalysisFileEndpoint(DefaultEndpoint):
    model = AnalysisFile
    base_viewset = AnalysisFileViewset
