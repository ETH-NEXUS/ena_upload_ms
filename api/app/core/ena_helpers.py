import pandas as pd
import yaml
import re
import json
import tempfile
from sh import Command, ErrorReturnCode
from os.path import abspath, basename, dirname, isfile, join, splitext
from core import log
from box import Box
from django.conf import settings
from ena_upload import ena_upload as ena
from rest_framework.exceptions import ValidationError
from lxml import etree
from datetime import datetime as dt
from django.utils import timezone as tz
from .models import Job, File, AnalysisJob
from .helpers import merge

SCHEMAS = ["study", "sample", "experiment", "run"]
STATUS_CHANGES = {
    "ADD": "ADDED",
    "MODIFY": "MODIFIED",
    "CANCEL": "CANCELLED",
    "RELEASE": "RELEASED",
}


def apply_template(job: Job):
    if not job.template:
        job.template = "default"

    template_file = join(settings.TEMPLATE_DIR, f"{job.template}.yml")
    log.debug(f"Template file: {template_file}")
    if isfile(template_file):
        log.debug("Template file found.")
        with open(template_file, "r") as cf:
            # We use BaseLoader to handle all values as string
            template = yaml.load(cf, Loader=yaml.BaseLoader)
            # Remove the ignored parts
            for ignore in job.ignore:
                if ignore in template:
                    del template[ignore]
            # now merge the data
            new_data = merge(template, job.data)
            # Replace all {} in the alias values with the timestamp
            ts = dt.strftime(tz.now(), "%Y%m%d%H%M%S%f")
            for schema in SCHEMAS:
                if schema in new_data:
                    for key, value in new_data[schema].items():
                        if key.endswith("alias"):
                            new_data[schema][key] = value.replace("{}", ts)
            # remove all sections that are not in the extended schema list
            for key in set(new_data.keys()).difference(
                set(SCHEMAS + ["center_name", "laboratory", "checklist"])
            ):
                del new_data[key]
            job.data = new_data
    else:
        log.warning(f"Template file not found: {template_file}")
        # Template not found
        raise ValidationError(f"Template file not found: {template_file}")


def to_dataframe(job: Job):
    """Converts the config to the required dataframe"""
    data = Box(job.data)
    schema_dataframe = {}
    for schema in SCHEMAS:
        if schema in job.ignore:
            continue
        if schema not in data:
            continue
        df = pd.DataFrame.from_dict([data[schema]], orient="columns")
        df = df.dropna(how="all")
        df = ena.check_columns(
            df,
            schema,
            job.action,
            settings.ENA_USE_DEV_ENDPOINT,
            auto_action=False,
        )
        schema_dataframe[schema] = df
    return schema_dataframe


def handle_run(job: Job, schema_target):
    df = schema_target
    file_paths = {}
    if job.files:
        for file in job.files:
            log.debug(f"Handle file {file}...")
            if not isfile(file):
                raise ValidationError(f"File does not exist: {file}.")
            File.objects.update_or_create(
                file_name=abspath(file),
                defaults={
                    "job": job,
                    "file_type": splitext(file)[1].replace(".", ""),
                    "md5sum": ena.get_md5(file),
                },
            )
            file_paths[basename(file)] = abspath(file)

        file_md5 = {
            filename: ena.get_md5(path) for filename, path in file_paths.items()
        }
        pd.concat([df] * len(file_md5), ignore_index=True)
        df["file_name"] = file_md5.keys()
        df["file_type"] = [
            splitext(file)[1].replace(".", "") for file in file_md5.keys()
        ]
        df["file_checksum"] = file_md5.values()

        ena.submit_data(file_paths, settings.ENA_PASSWORD, settings.ENA_USERNAME)
        return df
    else:
        return None


def handle_sample(job: Job, schema_target):
    df = schema_target
    log.info("Retrieving taxon IDs and scientific names if needed")
    for index, row in df.iterrows():
        if pd.notna(row["scientific_name"]) and pd.isna(row["taxon_id"]):
            # retrieve taxon id using scientific name
            taxonID = ena.get_taxon_id(row["scientific_name"])
            df.loc[index, "taxon_id"] = taxonID
        elif pd.notna(row["taxon_id"]) and pd.isna(row["scientific_name"]):
            # retrieve scientific name using taxon id
            scientificName = ena.get_scientific_name(row["taxon_id"])
            df.loc[index, "scientific_name"] = scientificName
        elif pd.isna(row["taxon_id"]) and pd.isna(row["scientific_name"]):
            raise ValidationError(
                f"No taxon_id or scientific_name was given with sample {row['alias']}."
            )
    log.info("Taxon IDs and scientific names are retrieved")
    return df


def ena_upload(job: Job):
    schema_dataframe = to_dataframe(job)
    schema_targets = ena.extract_targets(job.action, schema_dataframe)
    if not schema_targets:
        raise ValidationError(
            f"There is no table submitted having at least one row with {job.action} as action in the status column."
        )

    if job.action == "ADD":
        if "run" in schema_targets:
            schema_targets["run"] = handle_run(job, schema_targets["run"])
            if schema_targets["run"] is None:
                del schema_targets["run"]

        if "sample" in schema_targets:
            schema_targets["sample"] = handle_sample(job, schema_targets["sample"])

    base_path = abspath(dirname(ena.__file__))
    template_path = join(base_path, "templates")

    center = job.data.get("center_name")
    log.debug(f"Using center {center}")
    if not center:
        raise ValidationError(
            "Center is not defined. Please specify 'center_name' in the config."
        )
    checklist = job.data.get("checklist")
    log.debug(f"Using checklist {checklist}")
    if not checklist:
        raise ValidationError(
            "Checklist is not defined. Please specify 'checklist' in the config."
        )
    tool = {"tool_name": "ena_upload_ms", "tool_version": 0.1}

    if job.action in ["ADD", "MODIFY"]:
        schema_xmls = ena.run_construct(
            template_path,
            schema_targets,
            center,
            checklist,
            tool,
        )

        submission_xml = ena.construct_submission(
            template_path, job.action, schema_xmls, center, checklist, tool
        )
    elif job.action in ["CANCEL", "RELEASE"]:
        schema_xmls = {}
        submission_xml = ena.construct_submission(
            template_path, job.action, schema_targets, center, checklist, tool
        )
    else:
        raise ValidationError(f"The action {job.action} is not supported.")

    job.submission = {
        schema: json.loads(target.to_json(orient="records"))[0]
        for schema, target in schema_targets.items()
    }
    with open(submission_xml, "r") as sf:
        job.raw_submission = sf.read()
    schema_xmls["submission"] = submission_xml

    url = settings.ENA_ENDPOINT
    log.info(f"Submitting XMLs to ENA server: {url}")
    receipt = ena.send_schemas(
        schema_xmls, url, settings.ENA_USERNAME, settings.ENA_PASSWORD
    ).text
    job.raw_result = receipt
    schema_update = process_receipt(receipt.encode("utf-8"), job.action)

    if job.action in ["ADD", "MODIFY"]:
        schema_dataframe = ena.update_table(
            schema_dataframe, schema_targets, schema_update
        )
    else:
        schema_dataframe = ena.update_table_simple(
            schema_dataframe, schema_targets, job.action
        )
    job.result = {
        schema: json.loads(dataframe.to_json(orient="records"))[0]
        for schema, dataframe in schema_dataframe.items()
    }
    job.status = "SUBMITTED"
    job.save()


def webin_upload(job: AnalysisJob):
    webin = Command("/usr/bin/java")
    webin = webin.bake("-jar", "/opt/webin-cli.jar")
    with tempfile.NamedTemporaryFile(delete_on_close=False) as mf:
        mf.write(job.manifest.encode("utf-8"))
        mf.close()
        try:
            out = webin(
                "-context",
                "genome",
                "-username",
                settings.ENA_USERNAME,
                "-password",
                settings.ENA_PASSWORD,
                "-manifest",
                mf.name,
                "-submit",
                "-ascp",
                "-test" if settings.ENA_USE_DEV_ENDPOINT else "",
                _err_to_out=True,
            )
            log.debug(f"Submission output: {out}")
            accession = re.findall("ERZ[0-9]+", out, flags=re.MULTILINE)
            log.debug(f"Accessions: {accession}")
            if len(accession) > 0:
                log.debug(f"Found accession: {accession[0]}")
                job.result = {"accession": accession[0]}
            else:
                log.debug("No accession found :(")
            job.raw_result = out
            job.status = "SUBMITTED"
        except ErrorReturnCode as e:
            if isinstance(e, str):
                job.raw_result = e
            else:
                job.raw_result = e.stdout + e.stderr
            job.status = "ERROR"

    job.save()


def process_receipt(receipt, action):
    receipt_root = etree.fromstring(receipt)
    success = receipt_root.get("success")
    if success == "true":
        log.info("Submission was done successfully")
    else:
        errors = []
        for element in receipt_root.findall("MESSAGES/ERROR"):
            error = element.text
            errors.append(error)
        errors = " ".join(errors)
        raise ValidationError(errors.replace('"', "'"))

    def make_update(update, ena_type):
        update_list = []
        log.info(f"\n{ena_type.capitalize()} accession details:")
        for element in update:
            extract = (
                element.get("alias"),
                element.get("accession"),
                receiptDate,
                STATUS_CHANGES[action],
            )
            log.info("\t".join(extract))
            update_list.append(extract)
        # used for labelling dataframe
        labels = ["alias", "accession", "submission_date", "status"]
        df = pd.DataFrame.from_records(update_list, columns=labels)
        return df

    receiptDate = receipt_root.get("receiptDate")
    schema_update = {}  # schema as key, dataframe as value
    if action in ["ADD", "MODIFY"]:
        study_update = receipt_root.findall("STUDY")
        sample_update = receipt_root.findall("SAMPLE")
        experiment_update = receipt_root.findall("EXPERIMENT")
        run_update = receipt_root.findall("RUN")

        if study_update:
            schema_update["study"] = make_update(study_update, "study")

        if sample_update:
            schema_update["sample"] = make_update(sample_update, "sample")

        if experiment_update:
            schema_update["experiment"] = make_update(experiment_update, "experiment")

        if run_update:
            schema_update["run"] = make_update(run_update, "run")
        return schema_update

    # release does have the accession numbers that are released in the recipe
    elif action == "RELEASE":
        receipt_info = {}
        infoblocks = receipt_root.findall("MESSAGES/INFO")
        for element in infoblocks:
            match = re.search('(.+?) accession "(.+?)"', element.text)
            if match and match.group(1) in receipt_info:
                receipt_info[match.group(1)].append(match.group(2))
            elif match and match.group(1) not in receipt_info:
                receipt_info[match.group(1)] = [match.group(2)]
        for ena_type, accessions in receipt_info.items():
            log.info(f"\n{ena_type.capitalize()} accession details:")
            update_list = []
            for accession in accessions:
                extract = (accession, receiptDate, STATUS_CHANGES[action])
                update_list.append(extract)
                log.info("\t".join(extract))
