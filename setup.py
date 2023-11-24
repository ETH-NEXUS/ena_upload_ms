from setuptools import setup
from ena_upload_ng._version import __version__

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt", "r") as f:
    required = f.read().splitlines()

setup(
    name="ena_upload_ms",
    version=__version__,
    keywords=["pip", "ena_upload-ms", "ena-upload-cli", "cli", "ENA", "upload"],
    description="Command Line Interface to upload data to the European Nucleotide Archive",
    author="David Meyer",
    author_email="meyer@nexus.ethz.ch",
    long_description_content_type="text/markdown",
    packages=["ena_upload_ms"],
    package_dir={"ena_upload_ms": "ena_upload_ms"},
    package_data={"ena_upload_ms": ["templates/*.xml", "templates/*.xsd"]},
    long_description=long_description,
    url="https://github.com/usegalaxy-eu/ena-upload-cli",
    license="MIT",
    install_requires=[required],
    classifiers=["Operating System :: OS Independent"],
    python_requires=">=3.10",
    entry_points={"console_scripts": ["ena=ena_upload_ms.ena_upload_ms:main"]},
)
