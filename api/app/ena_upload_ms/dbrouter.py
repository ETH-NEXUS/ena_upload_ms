from constance import config
from django.db import DEFAULT_DB_ALIAS


class DynamicDbRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == "core" and config.ENA_USE_DEV_ENDPOINT:
            return "dev"
        return DEFAULT_DB_ALIAS

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, *args, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == DEFAULT_DB_ALIAS or app_label == "core" and db == "dev"
