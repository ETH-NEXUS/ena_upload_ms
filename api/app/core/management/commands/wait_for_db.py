import time

import psycopg2
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import OperationalError, connections


class Command(BaseCommand):
    """Django command to pause execution until database is available"""

    def handle(self, *args, **options):
        self.stdout.write("Waiting for database...")
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections["default"]
            except OperationalError:
                self.stdout.write("Database unavailable, waiting 1 second...")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database available!"))

        # Check if the database exists, and create it if it does not
        self.create_database_if_not_exists()

    def create_database_if_not_exists(self):
        db_name = settings.DATABASES["default"]["NAME"]
        db_user = settings.DATABASES["default"]["USER"]
        db_password = settings.DATABASES["default"]["PASSWORD"]
        db_host = settings.DATABASES["default"]["HOST"]
        db_port = settings.DATABASES["default"]["PORT"]

        conn = psycopg2.connect(
            dbname="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        exists = cursor.fetchone()
        if not exists:
            self.stdout.write(f"Database '{db_name}' does not exist. Creating...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            self.stdout.write(
                self.style.SUCCESS(f"Database '{db_name}' created successfully!")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Database '{db_name}' already exists.")
            )

        cursor.close()
        conn.close()
