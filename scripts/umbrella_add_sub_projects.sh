#!/usr/bin/env bash
set -euo pipefail

WEBIN_USER="${WEBIN_USER:-Username}"
WEBIN_PASS="${WEBIN_PASS:-Password}"

ASS1="PRJEB112346"
ASS2="PRJEB83635"
ASS3="PRJEB112345"

# Use test first; switch to production after validation:
ENA_URL="${ENA_URL:-https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/}"

cat > add.xml <<EOF
<SUBMISSION>
   <ACTIONS>
      <ACTION>
         <ADD/>
      </ACTION>
   </ACTIONS>
</SUBMISSION>
EOF

cat > umbrella.xml <<EOF
<PROJECT_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <PROJECT alias="revseq_unbrella_study">
        <TITLE>Respiratory Virus Sequencing</TITLE>
        <DESCRIPTION>Umbrella study grouping related Respiratory Virus Sequencing studies.</DESCRIPTION>
        <UMBRELLA_PROJECT/>
        <RELATED_PROJECTS>
            <RELATED_PROJECT>
                <CHILD_PROJECT accession="${ASS1}"/>
            </RELATED_PROJECT>
            <RELATED_PROJECT>
                <CHILD_PROJECT accession="${ASS2}"/>
            </RELATED_PROJECT>
            <RELATED_PROJECT>
                <CHILD_PROJECT accession="${ASS3}"/>
            </RELATED_PROJECT>
        </RELATED_PROJECTS>
    </PROJECT>
</PROJECT_SET>
EOF

echo "Creating umbrella study and linking child projects..."
curl -u "${WEBIN_USER}:${WEBIN_PASS}" \
    -F "SUBMISSION=@add.xml" \
    -F "PROJECT=@umbrella.xml" \
    "${ENA_URL}" | tee umbrella_receipt.xml