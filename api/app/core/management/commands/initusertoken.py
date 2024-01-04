from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from os import environ
from core import log
from uuid import uuid4


class Command(BaseCommand):
    def handle(self, *args, **options):
        username = environ.get("ENA_USER", "ena")
        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            user = User.objects.create(username=username, password=uuid4().hex)
            log.debug("User account created")
            userkey = environ.get("ENA_TOKEN", uuid4().hex)
            Token.objects.create(user=user, key=userkey)
            log.debug("Token created")
        else:
            log.warning("User account exists")
