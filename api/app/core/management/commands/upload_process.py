import time
from django.core.management.base import BaseCommand
from django.conf import settings
from core import log
from core.models import Job, AnalysisJob
from core.ena_helpers import ena_upload, webin_upload


class Command(BaseCommand):
    def handle(self, *args, **options):
        while True:
            log.debug("Handling queued jobs...")
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
