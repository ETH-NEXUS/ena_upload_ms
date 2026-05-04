#!/usr/bin/env bash
set -euo pipefail

WEBIN_USER="${WEBIN_USER:-Username}"
WEBIN_PASS="${WEBIN_PASS:-Password}"

PRJ="PRJEB112381"

# Use test first; switch to production after validation:
ENA_URL="${ENA_URL:-https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/}"

cat > release.xml <<EOF
<SUBMISSION>
    <ACTIONS>
        <ACTION>
            <RELEASE target="${PRJ}" />
        </ACTION>
    </ACTIONS>
</SUBMISSION>
EOF

echo "Releasing umbrella study ${PRJ}..."
curl -u "${WEBIN_USER}:${WEBIN_PASS}" \
    -F "SUBMISSION=@release.xml" \
    "${ENA_URL}" | tee umbrella_release_receipt.xml