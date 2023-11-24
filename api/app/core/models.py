from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.conf import settings
from copy import copy
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
        )
    )
    template = models.CharField(
        max_length=50, default="default", null=False, blank=True
    )
    data = models.JSONField(null=False)
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
            "experiment": f"{settings.ENA_BROWSER_URL}/{self.result['experiment'][0]['accession']}"
            if "experiment" in self.result
            else "",
            "sample": f"{settings.ENA_BROWSER_URL}/{self.result['sample'][0]['accession']}"
            if "sample" in self.result
            else "",
            "run": f"{settings.ENA_BROWSER_URL}/{self.result['run'][0]['accession']}"
            if "run" in self.result
            else "",
            "study": f"{settings.ENA_BROWSER_URL}/{self.result['study'][0]['accession']}"
            if "study" in self.result
            else "",
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
    ):
        new_job = copy(self)
        new_job.pk = None
        new_job.owner = user
        new_job.parent = self
        # can be moved to model
        new_job.action = new_action
        new_job.status = new_status
        result = {}
        for key in new_job.result.keys():
            new_job.result[key][0]["status"] = new_action
            result[key] = new_job.result[key][0]
        new_job.data = merge(new_job.data, result)
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
            ("QUEUED", "QUEUED"),
            ("SUBMITTED", "SUBMITTED"),
            ("ERROR", "ERROR"),
        ),
        default="QUEUED",
    )
    template = models.CharField(
        max_length=50, default="default", null=False, blank=True
    )
    data = models.JSONField(null=False)
    result = models.JSONField(null=True, blank=True)
    raw_result = models.TextField(null=True, blank=True)

    @property
    def manifest(self):
        manifest_text = f"""STUDY {self.job.result['experiment'][0]['study_alias']}
SAMPLE {self.job.result['experiment'][0]['sample_alias']}
RUN_REF {self.job.result['run'][0]['accession']}
"""
        for key, value in self.data.items():
            manifest_text += f"{key.upper()} {value}\n"
        for file in self.analysisjob_files.all():
            manifest_text += f"{file.file_type} {file.file_name}\n"
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
