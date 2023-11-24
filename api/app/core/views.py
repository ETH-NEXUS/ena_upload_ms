import threading
import time
import yaml
from os.path import join, isfile
from rest_framework import status, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from django.conf import settings
from core import log
from .serializers import (
    JobSerializer,
    AnalysisJobSerializer,
    FileSerializer,
    AnalysisFileSerializer,
)
from .models import Job, AnalysisJob
from .ena_helpers import ena_upload, webin_upload, apply_template, SCHEMAS
from .helpers import merge
from ena_upload import ena_upload as ena
from django.utils.translation import gettext_lazy as _


###
# Background thread to upload the jobs
###
def upload_process():
    while True:
        # log.debug("Handling queued jobs...")
        queued_jobs = Job.objects.filter(status="QUEUED")
        for queued_job in queued_jobs:
            log.info(f"Handling queued job {queued_job}...")
            try:
                queued_job.status = "RUNNING"
                queued_job.save()
                ena_upload(queued_job)
            except Exception as ex:
                queued_job.status = "ERROR"
                queued_job.raw_result = ex
                queued_job.save()
                log.exception(ex)
                log.exception(ex.__traceback__)

        queued_analysisjobs = AnalysisJob.objects.filter(status="QUEUED")
        for queued_analysisjob in queued_analysisjobs:
            log.info(f"Handling queued analysis job {queued_analysisjob}...")
            try:
                if queued_analysisjob.analysisjob_files.count() > 0:
                    queued_analysisjob.status = "RUNNING"
                    queued_analysisjob.save()
                    webin_upload(queued_analysisjob)
                else:
                    log.warning(
                        f"Analysis job {queued_analysisjob} has no assigned files!"
                    )
            except Exception as ex:
                queued_analysisjob.status = "QUEUED"
                queued_analysisjob.raw_result = ex
                queued_analysisjob.save()
                log.exception(ex)
                log.exception(ex.__traceback__)
        time.sleep(settings.ENA_UPLOAD_FREQ_SECS)


upload_thread = threading.Thread(target=upload_process, args=(), kwargs={})
upload_thread.setDaemon(True)
upload_thread.start()


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

    ###
    # SPECIAL ACTIONS FOR JOBS
    ###

    def __release_cancel(self, request, pk, action: str):
        job = Job.objects.get(pk=pk)
        new_job = job.clone(request.user, action)
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
        for schema in SCHEMAS:
            if schema not in data and schema in new_job.data:
                del new_job.data[schema]
        new_job.data = merge(new_job.data, data)
        new_job.save()
        result = JobSerializer(new_job, context={"request": request})
        return Response(result.data)


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
            job.save()
            return job
        else:
            raise ValidationError("Template file {template_file} does not exist.")

    def perform_destroy(self, instance):
        if instance.status == "QUEUED":
            return super().perform_destroy(instance)
        else:
            raise DeleteNotAllowed()

    @action(detail=True, methods=["get"])
    def requeue(self, request, pk=None):
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
