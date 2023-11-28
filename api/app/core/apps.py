import threading
import time
from django.apps import AppConfig


class UploadThread:
    """Allow only one instance of ghe Upload Thread"""

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = threading.Thread(*args, **kwargs)
        return cls.instance


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from core import log
        from core.ena_helpers import ena_upload, webin_upload
        from django.conf import settings
        from core.models import Job, AnalysisJob

        ###
        # Background thread to upload the jobs
        ###
        def upload_process():
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

        upload_thread = UploadThread(target=upload_process, args=(), kwargs={})
        upload_thread.setDaemon(True)
        upload_thread.start()
        log.debug("########## BACKGROUND THREAD STARTED ##########")
        return super().ready()
