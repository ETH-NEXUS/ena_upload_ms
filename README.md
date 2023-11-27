# ENA (European Nucleotide Archive) Upload Microservice

## Overview

The ENA Metadata model foresees the following elements to be uploaded:

![ENA Metadata model](https://ena-docs.readthedocs.io/en/latest/_images/metadata_model_whole.png)

To support the uploading process the **ENA Upload Microservice** (`ena_upload_ms`) is built. You can register upload jobs of data and metadata and the microservice will handle the jobs in the background and updates the job information with additional data that is received by the ena upload procedure.
Mainly there are three different uploads available:

- Study definition upload (`/jobs/study`)
- Sample-Experiment-Run upload (`/jobs/ser`)
- Analysis upload (`/analysisjobs`)

Often the majority of metadata for one project are the same for all upload jobs. Therefore you can add a project related template that contains all the metadata that is static during the project. This information is stored in a `yaml` file in the `templates` directory:

```yaml
checklist: ERC000033
center_name: My Center
laboratory: My Laboratory

# Overall ENA research project
study:
  alias: my_study_alias
  title: My Study Title
  study_type: studyType
  study_abstract: My Study Abstract
  pubmed_id: pubmedId (if available)

# Sequenced Biomaterial
sample:
  alias: my_sample_{}
  title: My Sample Title
  taxon_id: The Taxon ID
  sample_description: My Sample Description
  host subject id: 0000001
  collection date: 2023-11-27
  geographic location (country and/or sea): Switzerland
  host common name: Human
  host health state: "missing: human-identifiable"
  host sex: "missing: human-identifiable"
  host scientific name: Homo Sapiens
  collector name: ""
  collecting institution: Collecting institution
  isolate: ""

# Raw Reads
experiment:
  alias: my_experiment_{}
  title: My Experiment
  study_alias: my_study_alias
  sample_alias: my_sample_{}
  design_description: "None"
  library_name: "None"
  library_strategy: RNA-Seq
  library_source: METAGENOMIC
  library_selection: cDNA
  library_layout: "paired"
  insert_size: 250
  library_construction_protocol: "None"
  platform: illumina
  instrument_model: Illumina MiSeq

# Files
run:
  alias: my_run_{}
  experiment_alias: my_experiment_{}

# Data Analysis
analysis:
  name: my_analysis_{}
  assembly_type: clone
  coverage: <float with the coverage>
  program: TODO
  platform: TODO
```

The `{}` will be replace with a timestamp of nanoseconds accuracy (`strftime("%Y%m%d%H%M%S%f")`). Before you can create an analysis job you need to create a job, preferably including a Sample-Experiment-Run component. The Analysis Job will then point (Foreign key) to this job. This is because you need to have reference a run and a sample from the analysis and thats only possible if they already exist. That leads to the following order of uploads:

1. Upload the study (this is needed only once): `/jobs/study/`
2. Upload Sample-Experiment-Run-Tripple: `/jobs/ser/`
3. Upload an Analysis: `/analysisjobs/`
4. Attach files to this job `/analysisfiles/`

## Installation

### Integrate it as a service in your `docker-compose.yml`

```yaml
version: "3"
volumes:
  pg_data:
services:
  ena:
    image: ethnexus/ena-upload-ms
    hostname: ena
    restart: unless-stopped
    volumes:
      # - ./api/app:/app
      - ./templates:/templates
      - ./data:/data
    env_file: .env
    depends_on:
      - db
  db:
    image: postgres:15-bookworm
    hostname: db
    restart: unless-stopped
    env_file: .env
    volumes:
      - pg_data:/var/lib/postgresql/data
```
