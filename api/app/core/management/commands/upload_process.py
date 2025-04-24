import time

from constance import config
from core import log
from core.ena_helpers import ena_upload, webin_upload
from core.models import AnalysisJob, Job
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        while True:
            log.debug(
                f"{'[DEV] ' if config.ENA_USE_DEV_ENDPOINT else ''}Handling queued jobs..."
            )
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
                finally:
                    time.sleep(settings.ENA_UPLOAD_THROTTLE_SECS)

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
                        queued_analysisjob.status = "ERROR"
                        queued_analysisjob.raw_result = (
                            "Analysis job has no assigned files!"
                        )
                        queued_analysisjob.save()
                except Exception as ex:
                    queued_analysisjob.status = "ERROR"
                    queued_analysisjob.raw_result = ex
                    queued_analysisjob.save()
                    log.exception(ex)
                    log.exception(ex.__traceback__)
                finally:
                    time.sleep(settings.ENA_UPLOAD_THROTTLE_SECS)

            time.sleep(settings.ENA_UPLOAD_FREQ_SECS)
