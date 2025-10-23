#!/usr/bin/env bash
# generate_kb_cors.sh
# Usage: export ALLOW_CORG_ORIGIN and optionally CORS_ALLOW_CUSTM_SCHEME, then run:
# ./generate_kb_cors.sh /path/to/kb.conf

set -euo pipefail

KB_CONF=${1:-"./kb.conf"}
if [ ! -f "$KB_CONF" ]; then
  echo "kb.conf not found: $KB_CONF" >&2
  exit 2
fi

# Read env vars
ALLOW_ORIGINS=${ALLOW_CORG_ORIGIN:-}
CUSTM_SCHEMES=${CORS_ALLOW_CUSTM_SCHEME:-}

# Build the map entries for origins (comma-separated list)
ORIG_MAP_ENTRIES=""
if [ -n "$ALLOW_ORIGINS" ]; then
  IFS=',' read -ra ORIGS <<< "$ALLOW_ORIGINS"
  for o in "${ORIGS[@]}"; do
    o_trim=$(echo "$o" | sed -e 's/^\s*//' -e 's/\s*$//')
    if [ -n "$o_trim" ]; then
      ORIG_MAP_ENTRIES+="    \"$o_trim\" 1;\n"
    fi
  done
fi

# Build custom-scheme map entries from schemes list (semicolon-separated)
CUSTM_MAP_ENTRIES=""
if [ -n "$CUSTM_SCHEMES" ]; then
  IFS=';' read -ra SS <<< "$CUSTM_SCHEMES"
  for s in "${SS[@]}"; do
    s_trim=$(echo "$s" | sed -e 's/^\s*//' -e 's/\s*$//' | tr -d '"')
    if [ -n "$s_trim" ]; then
      # produce a regex entry that matches scheme://
      CUSTM_MAP_ENTRIES+="    \"~^${s_trim}://\" 1;\n"
    fi
  done
fi

# Prepare the new map block
NEW_MAP_BLOCK="        map $http_origin $cors_allowed {\n            default 0;\n"
if [ -n "$ORIG_MAP_ENTRIES" ]; then
  NEW_MAP_BLOCK+="$ORIG_MAP_ENTRIES"
fi
NEW_MAP_BLOCK+="        }\n"

# Replace between markers CORS-MAP-START and CORS-MAP-END
awk -v newblock="$NEW_MAP_BLOCK" '
  BEGIN { inblock=0 }
  /# CORS-MAP-START/ { print; inblock=1; print newblock; next }
  /# CORS-MAP-END/ { inblock=0; print; next }
  { if (!inblock) print }
' "$KB_CONF" > "$KB_CONF.tmp" && mv "$KB_CONF.tmp" "$KB_CONF"

# Now also update the custom-scheme templated map entries section
if [ -n "$CUSTM_MAP_ENTRIES" ]; then
  # Insert custom scheme entries into the map $http_origin $cors_custom_scheme_allowed
  awk -v entries="$CUSTM_MAP_ENTRIES" '
    BEGIN { inblock=0 }
    /map \$http_origin \$cors_custom_scheme_allowed/ { print; inblock=1; next }
    /^\s*# Final custom-scheme allowance:/ { inblock=0; print; next }
    { if (inblock) { print entries; inblock=0 } print }
  ' "$KB_CONF" > "$KB_CONF.tmp" && mv "$KB_CONF.tmp" "$KB_CONF"
fi

echo "Updated $KB_CONF"
