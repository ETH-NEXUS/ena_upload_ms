#!/usr/bin/env bash
set -euo pipefail

WEBIN_USER="${WEBIN_USER:-Username}"
WEBIN_PASS="${WEBIN_PASS:-Password}"
AUTH_TOKEN="Basic V2ViaW4tNjU4NTQ6UkhxcFV3ZDVBVnVoMkVIYmtpanloWGFKZXY0bWJGd1ZD"

NEW_STUDY_ID="ERP192904"
NEW_STUDY_ID2="PRJEB112346"
IGNORE_SAMPLE_IDS=("ERS22647945" "ERS22647826" "ERS22642104" "ERS22640230" "ERS22587783" "ERS22583720" "ERS22583719" "ERS22583360")

# Use test first; switch to production after validation:
ENA_API="${ENA_URL:-https://wwwdev.ebi.ac.uk/ena/submit/report}"
ENA_URL="${ENA_URL:-https://wwwdev.ebi.ac.uk/ena/submit/drop-box}"

ERX_IDS=$(curl -s -X 'GET' \
  -H 'accept: */*' \
  -H "Authorization: ${AUTH_TOKEN}" \
  "${ENA_API}/experiments?status=PUBLIC&format=json&max-results=1000" | jq -r '.[].report.id'
)

cat > modify.xml <<EOF
<SUBMISSION>
  <ACTIONS>
    <ACTION>
      <MODIFY/>
    </ACTION>
  </ACTIONS>
</SUBMISSION>
EOF

echo "<EXPERIMENT_SET>" > experiments.xml
for erx in $ERX_IDS
do
    # Download current full experiment XML
    current_exp=$(curl -s -u "${WEBIN_USER}:${WEBIN_PASS}" "${ENA_URL}/experiments/${erx}")
    sample_id=$(echo "${current_exp}" | sed -n 's/.*<SAMPLE_DESCRIPTOR accession="\([^"]*\)".*/\1/p')
    if [[ " ${IGNORE_SAMPLE_IDS[*]} " =~ " ${sample_id} " ]]; then
        echo "ignoring ${sample_id}"
        continue
    fi
    modified_exp=$(echo "${current_exp}" | sed -E "
/<STUDY_REF accession=\"[^\"]+\">/,/<\/STUDY_REF>/c\\
      <STUDY_REF accession=\"${NEW_STUDY_ID}\">\\
         <IDENTIFIERS>\\
            <PRIMARY_ID>${NEW_STUDY_ID}</PRIMARY_ID>\\
            <SECONDARY_ID>${NEW_STUDY_ID2}</SECONDARY_ID>\\
         </IDENTIFIERS>\\
      </STUDY_REF>
" | sed -E 's#</?EXPERIMENT_SET[^>]*>##g')
    echo "${modified_exp}" >> experiments.xml
done
echo "</EXPERIMENT_SET>" >> experiments.xml

curl -s -u "${WEBIN_USER}:${WEBIN_PASS}" \
    -F "SUBMISSION=@modify.xml" \
    -F "EXPERIMENT=@experiments.xml" \
    "${ENA_URL}/submit/" | tee modify_experiments_receipt.xml
