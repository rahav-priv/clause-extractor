#!/usr/bin/env bash

# Usage: ./test_extract.sh [pdf_file]
# Default: test_contracts/nda_1.pdf

FILE="${1:-test_contracts/nda_1.pdf}"
API_URL="http://localhost:6363/api/extract"

if [ ! -f "$FILE" ]; then
  echo "Error: file not found: $FILE"
  exit 1
fi

echo "Uploading: $FILE"
echo "Endpoint:  $API_URL"
echo "---"

curl -s -X POST "$API_URL" \
  -F "file=@$FILE" \
  -H "Accept: application/json" \
  | python3 -m json.tool
