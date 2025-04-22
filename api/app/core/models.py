from copy import copy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models

from .helpers import merge


class Job(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(to=get_user_model(), null=True, on_delete=models.SET_NULL)
    status = models.CharField(
        max_length=20,
        choices=(
            ("QUEUED", "QUEUED"),
            ("SUBMITTED", "SUBMITTED"),
            ("RUNNING", "RUNNING"),
            ("ERROR", "ERROR"),
        ),
        default="QUEUED",
    )
    action = models.TextField(
        choices=(
            ("ADD", "ADD"),
            ("MODIFY", "MODIFY"),
            ("CANCEL", "CANCEL"),
            ("RELEASE", "RELEASE"),
        ),
        default="ADD",
    )
    template = models.CharField(
        max_length=50, default="default", null=False, blank=True
    )
    data = models.JSONField(null=False, default=dict)
    ignore = ArrayField(
        models.CharField(
            max_length=10,
            choices=(
                ("study", "study"),
                ("sample", "sample"),
                ("experiment", "experiment"),
                ("run", "run"),
            ),
        ),
        null=True,
        blank=True,
    )
    files = ArrayField(
        models.CharField(max_length=255),
        null=True,
        blank=True,
    )
    submission = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    raw_submission = models.TextField(null=True, blank=True)
    raw_result = models.TextField(null=True, blank=True)
    parent = models.ForeignKey(
        to="Job", on_delete=models.SET_NULL, null=True, related_name="children"
    )

    @property
    def links(self):
        if not self.result:
            return {}
        return {
            "experiment": (
                f"{settings.ENA_BROWSER_URL}/{self.result['experiment']['accession']}"
                if "experiment" in self.result
                else ""
            ),
            "sample": (
                f"{settings.ENA_BROWSER_URL}/{self.result['sample']['accession']}"
                if "sample" in self.result
                else ""
            ),
            "run": (
                f"{settings.ENA_BROWSER_URL}/{self.result['run']['accession']}"
                if "run" in self.result
                else ""
            ),
            "study": (
                f"{settings.ENA_BROWSER_URL}/{self.result['study']['accession']}"
                if "study" in self.result
                else ""
            ),
        }

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Job: {self.id}"

    def clone(
        self,
        user: get_user_model(),
        new_action: str,
        new_status: str = "QUEUED",
        filter_none_accession: bool = False,
    ):
        new_job = copy(self)
        new_job.pk = None
        new_job.owner = user
        new_job.parent = self
        # can be moved to model
        new_job.action = new_action
        new_job.status = new_status
        if new_job.result:
            for key in new_job.result.keys():
                new_job.result[key]["status"] = new_action
        new_job.data = merge(new_job.data, new_job.result)
        # filter out keys without accession
        if filter_none_accession:
            keys_to_delete = []
            for key in new_job.data.keys():
                if (
                    "accession" in new_job.data[key]
                    and new_job.data[key]["accession"] is None
                ):
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del new_job.data[key]
        new_job.result = None
        new_job.raw_result = None
        new_job.submission = None
        new_job.raw_submission = None
        return new_job


class File(models.Model):
    job = models.ForeignKey(
        to=Job, null=False, on_delete=models.CASCADE, related_name="job_files"
    )
    file_name = models.CharField(max_length=255, unique=True)
    file_type = models.CharField(
        choices=(("bam", "bam"), ("cram", "cram"), ("fastq", "fastq"))
    )
    md5sum = models.CharField(max_length=32)


class AnalysisJob(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(to=get_user_model(), null=True, on_delete=models.SET_NULL)
    job = models.ForeignKey(
        to=Job, null=False, on_delete=models.CASCADE, related_name="jobs"
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ("DRAFT", "DRAFT"),
            ("QUEUED", "QUEUED"),
            ("SUBMITTED", "SUBMITTED"),
            ("ERROR", "ERROR"),
        ),
        default="DRAFT",
    )
    template = models.CharField(
        max_length=50, default="default", null=False, blank=True
    )
    data = models.JSONField(null=False, default=dict)
    result = models.JSONField(null=True, blank=True)
    raw_result = models.TextField(null=True, blank=True)

    @property
    def manifest(self):
        try:
            manifest_text = ""
            if self.job.result:
                # Merge different results from different child jobs
                consolidated_job_result = self.job.result
                for child in self.job.children.all().order_by("created_at"):
                    if child.status != "ERROR" and child.result:
                        consolidated_job_result = merge(
                            consolidated_job_result, child.result
                        )
                if "experiment" in consolidated_job_result:
                    manifest_text = (
                        f"STUDY {consolidated_job_result['experiment']['study_alias']}\n"
                        f"SAMPLE {consolidated_job_result['experiment']['sample_alias']}\n"
                    )
                if "run" in consolidated_job_result:
                    manifest_text += (
                        f"RUN_REF {consolidated_job_result['run']['accession']}\n"
                    )

                for key, value in self.data.items():
                    manifest_text += f"{key.upper()} {value}\n"
                for file in self.analysisjob_files.all():
                    manifest_text += f"{file.file_type} {file.file_name}\n"
        except Exception as ex:
            return f"ERROR generating manifest: {ex}"
        return manifest_text

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"AnalysisJob: {self.id}"


class AnalysisFile(models.Model):
    job = models.ForeignKey(
        to=AnalysisJob,
        null=True,
        on_delete=models.CASCADE,
        related_name="analysisjob_files",
    )
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(
        choices=(
            ("FASTA", "FASTA"),
            ("CHROMOSOME_LIST", "CHROMOSOME_LIST"),
            ("FLATFILE", "FLATFILE"),
            ("AGP", "AGP"),
            ("UNLOCALISED_LIST", "UNLOCALISED_LIST"),
            ("BAM", "BAM"),
            ("CRAM", "CRAM"),
            ("FASTQ", "FASTQ"),
        )
    )
    md5sum = models.CharField(max_length=32)

    class Meta:
        unique_together = ("job", "file_name")

    def __str__(self):
        return self.file_name
