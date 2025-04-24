import re
from datetime import datetime as dt
from os import listdir
from os.path import isdir, isfile, join

import yaml
from constance import config
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone as tz
from django.utils.translation import gettext_lazy as _
from ena_upload import ena_upload as ena
from ena_upload_ms.dynamic_settings import dynamic_settings
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .ena_helpers import SCHEMAS, apply_template, webin_validate
from .filters import JobFilterSet
from .helpers import merge
from .models import AnalysisJob, Job
from .serializers import (
    AnalysisFileSerializer,
    AnalysisJobSerializer,
    FileSerializer,
    JobSerializer,
)


###
# Exceptions
###
class DeleteNotAllowed(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Delete is not allowed.")
    default_code = "delete_not_allowed"


###
# Main Viewsets
###
class JobViewset(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = JobSerializer
    filterset_class = JobFilterSet

    def perform_create(self, serializer: JobSerializer):
        job = serializer.save(owner=self.request.user)
        apply_template(job)
        job.save()
        return job

    ###
    # SPECIAL ACTIONS TO ONLY SUBMIT SINGLE OBJECTS
    ###

    def __perform_create_with_ignore(self, request, ignore: list):
        data = request.data
        data["ignore"] = ignore
        serializer = JobSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            result = JobSerializer(
                self.perform_create(serializer), context={"request": request}
            )
            return Response(result.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def study(self, request):
        return self.__perform_create_with_ignore(
            request, ["sample", "experiment", "run"]
        )

    @action(detail=False, methods=["post"])
    def sample(self, request):
        return self.__perform_create_with_ignore(
            request, ["study", "experiment", "run"]
        )

    @action(detail=False, methods=["post"])
    def experiment(self, request):
        return self.__perform_create_with_ignore(request, ["study", "sample", "run"])

    @action(detail=False, methods=["post"])
    def run(self, request):
        return self.__perform_create_with_ignore(
            request, ["study", "sample", "experiment"]
        )

    @action(detail=False, methods=["post"])
    def ser(self, request):
        """sample, experiment, run"""
        return self.__perform_create_with_ignore(request, ["study"])

    @action(detail=True, methods=["get"])
    def enqueue(self, request, pk=None):
        job = Job.objects.get(pk=pk)
        if job.status != "SUBMITTED" or ("force" in request.query_params):
            job.status = "QUEUED"
            job.save()
            serializer = JobSerializer(instance=job, context={"request": request})
            return Response(serializer.data)
        else:
            return Response(
                "Requeue not allowed on successfully submitted jobs.",
                status=status.HTTP_400_BAD_REQUEST,
            )

    ###
    # SPECIAL ACTIONS FOR JOBS
    ###

    def __release_cancel(self, request, pk, action: str):
        job = Job.objects.get(pk=pk)
        new_job = job.clone(request.user, action, filter_none_accession=True)
        new_job.save()
        serializer = JobSerializer(instance=new_job, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def release(self, request, pk=None):
        return self.__release_cancel(request, pk, "RELEASE")

    @action(detail=True, methods=["get"])
    def cancel(self, request, pk=None):
        """cancel submission"""
        return self.__release_cancel(request, pk, "CANCEL")

    @action(detail=True, methods=["post"])
    def modify(self, request, pk=None):
        """modify submission"""
        job = Job.objects.get(pk=pk)
        new_job = job.clone(self.request.user, "MODIFY")
        data = request.data.get("data")
        # We filter out all irrelevant schemas for the modification
        if data is not None:
            for schema in SCHEMAS:
                if schema not in data and schema in new_job.data:
                    del new_job.data[schema]
            new_job.data = merge(new_job.data, data)
        new_job.save()
        result = JobSerializer(new_job, context={"request": request})
        return Response(result.data)

    @action(detail=False, methods=["get"])
    def release_all(self, request):
        """Release all not yet released jobs"""
        jobs = (
            Job.objects.filter(status="SUBMITTED", action="ADD")
            .annotate(
                children_with_released=Count(
                    "children", filter=Q(children__action="RELEASE")
                )
            )
            .filter(children_with_released=0)
        )
        for job in jobs:
            self.__release_cancel(request, job.id, "RELEASE")
        return Response(
            f"{len(jobs)} jobs triggered for release.",
            status=status.HTTP_200_OK,
        )


class AnalysisJobViewset(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AnalysisJobSerializer

    def perform_create(self, serializer: AnalysisJobSerializer):
        template_file = join(
            settings.TEMPLATE_DIR, f"{serializer.validated_data['template']}.yml"
        )
        if isfile(template_file):
            job = serializer.save(owner=self.request.user)
            with open(template_file, "r") as tf:
                template = yaml.load(tf, Loader=yaml.BaseLoader)
                if "analysis" in template:
                    job.data = merge(template["analysis"], job.data)
                # Replace {} in the name with the timestamp
                ts = dt.strftime(tz.now(), "%Y%m%d%H%M%S%f")
                if "name" in job.data:
                    job.data["name"] = job.data["name"].replace("{}", ts)
            job.save()
            return job
        else:
            raise ValidationError(f"Template file {template_file} does not exist.")

    def perform_destroy(self, instance):
        if instance.status == "QUEUED":
            return super().perform_destroy(instance)
        else:
            raise DeleteNotAllowed()

    @action(detail=True, methods=["get"])
    def enqueue(self, request, pk=None):
        job = AnalysisJob.objects.get(pk=pk)
        if job.status != "SUBMITTED":
            job.status = "QUEUED"
            job.save()
            serializer = AnalysisJobSerializer(
                instance=job, context={"request": request}
            )
            return Response(serializer.data)
        else:
            return Response(
                "Requeue not allowed on successfully submitted jobs.",
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def validate(self, request, pk=None):
        def read_lines(file):
            with open(file, "r") as rf:
                return [line.replace("\n", "") for line in rf.readlines()]

        job = AnalysisJob.objects.get(pk=pk)
        out = webin_validate(job).split("\n")
        infos = []
        errors = []
        files = {}
        for line in out:
            if line.startswith("INFO"):
                infos.append(line.replace("INFO : ", "").split(". "))
            if line.startswith("ERROR"):
                sentences = line.replace("ERROR: ", "").split(". ")
                for sentence in sentences:
                    match = re.search(r'(/tmp/[^," ]+)', sentence)
                    if match:
                        report_file = match.group(1)
                        if isfile(report_file):
                            files[report_file] = read_lines(report_file)
                        elif isdir(report_file):
                            for file in listdir(report_file):
                                files[join(report_file, file)] = read_lines(
                                    join(report_file, file)
                                )
                        else:
                            files[report_file] = "ERROR: not found"
                    errors.append(sentence)
        return Response(
            {
                "Job": {"id": job.id},
                "Validation": {
                    "OUT": out,
                    "INFO": infos,
                    "ERROR": errors,
                    "REPORTS": files,
                },
            }
        )


class FileViewset(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FileSerializer


class AnalysisFileViewset(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AnalysisFileSerializer

    def perform_create(self, serializer: AnalysisFileSerializer):
        file = serializer.save()
        if isfile(file.file_name):
            file.md5sum = ena.get_md5(file.file_name)
            file.save()
            return file
        else:
            raise ValidationError(f"File {file.file_name} does not exist.")


class ToggleDev(APIView):
    def get(self, request, *args, **kwargs):
        value = request.query_params.get("value")

        if value is not None:
            if isinstance(value, bool):
                new_value = value
            elif isinstance(value, str) and value.lower() in ["true", "false"]:
                new_value = value.lower() == "true"
            else:
                return Response(
                    {"error": "Invalid 'value' parameter. Must be 'true' or 'false'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            setattr(config, "ENA_USE_DEV_ENDPOINT", new_value)

        return Response(
            {
                "ENA_USE_DEV_ENDPOINT": config.ENA_USE_DEV_ENDPOINT,
                "ENA_ENDPOINT": dynamic_settings.ENA_ENDPOINT(),
                "ENA_DB": Job.objects.db,
            }
        )
