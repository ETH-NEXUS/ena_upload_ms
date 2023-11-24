import logging
from os import makedirs
from rich.logging import RichHandler

###
# Logging
###
FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%Y-%m-%d %X]", handlers=[RichHandler()]
)  # set level=20 or logging.INFO to turn off debug
log = logging.getLogger("rich")

###
# Directory creation
###
TMP = "tmp"
makedirs(TMP, exist_ok=True)
