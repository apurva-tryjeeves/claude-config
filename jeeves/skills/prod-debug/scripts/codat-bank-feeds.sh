#!/usr/bin/env bash
# Debug and remap Codat bank feeds (Xero) for one Codat company and connection.
#
# Usage:
#   codat-bank-feeds.sh read  <companyId> <connectionId> [pushOperationKey]
#   codat-bank-feeds.sh remap <companyId> <connectionId> --map <sourceId> <targetId> <feedStartDate> [--map ...] [--yes]
#
#   read   Runs every read-only GET and saves each response as JSON.
#   remap  Posts one bank-feed mapping per --map (this writes to Codat), then polls until each is connected.
#
# Arguments:
#   companyId, connectionId  Codat ids: accounting.integration.externalCompanyId and .connectionId.
#   sourceId                 Codat source account id = accounting.bank_feeds_account.id.
#   targetId                 Xero bank account id = accounting.account.externalAccountId.
#   feedStartDate            YYYY-MM-DDTHH:MM:SS in UTC. Use the time of the last line already in Xero
#                            plus one second, so Xero imports only the lines after it.
#
# API key: the script asks for it when it starts, with typing hidden. Paste the raw Codat API key
# or the full "Basic <base64>" value. The key stays in this process and in a private temp file
# that curl reads; the file is deleted on exit.
#
# Output: $CODAT_LOG_ROOT/codat-<command>-<timestamp>/, default
# ${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/.dev/drafts/codat-logs. It holds customer bank data.
#
# Example:
#   codat-bank-feeds.sh remap <companyId> <connectionId> --map <sourceId> <targetId> <YYYY-MM-DDTHH:MM:SS>

set -euo pipefail

BASE_URL="${CODAT_BASE_URL:-https://api.codat.io}"
LOG_ROOT="${CODAT_LOG_ROOT:-${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/.dev/drafts/codat-logs}"
POLL_INTERVAL=10
POLL_ATTEMPTS=30

usage() {
  awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0" >&2
  exit 1
}

[[ $# -ge 3 ]] || usage
COMMAND="$1" COMPANY_ID="$2" CONNECTION_ID="$3"
shift 3
[[ "$COMMAND" == "read" || "$COMMAND" == "remap" ]] || usage
command -v jq >/dev/null || { echo "❌ jq is required." >&2; exit 1; }

# --- Arguments -------------------------------------------------------------

PUSH_OPERATION_KEY=""
ASSUME_YES=false
declare -a MAPS=()

if [[ "$COMMAND" == "read" ]]; then
  PUSH_OPERATION_KEY="${1:-}"
else
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --map)
        [[ $# -ge 4 ]] || { echo "❌ --map takes <sourceId> <targetId> <feedStartDate>." >&2; exit 1; }
        MAPS+=("$2|$3|$4"); shift 4 ;;
      --yes) ASSUME_YES=true; shift ;;
      *) echo "❌ Unknown argument: $1" >&2; usage ;;
    esac
  done
  [[ ${#MAPS[@]} -gt 0 ]] || { echo "❌ remap takes at least one --map." >&2; exit 1; }
fi

# --- API key: read with typing hidden, keep in a private header file --------

if [[ -t 0 ]]; then
  read -r -s -p "Codat API key: " CODAT_KEY </dev/tty
  echo >&2
else
  read -r CODAT_KEY
fi
[[ -n "$CODAT_KEY" ]] || { echo "❌ Enter a Codat API key." >&2; exit 1; }

if [[ "$CODAT_KEY" == Basic\ * ]]; then
  AUTH_VALUE="$CODAT_KEY"
else
  AUTH_VALUE="Basic $(printf '%s' "$CODAT_KEY" | base64 | tr -d '\n')"
fi
unset CODAT_KEY

HEADER_FILE="$(umask 077; mktemp)"
trap 'rm -f "$HEADER_FILE"' EXIT
printf 'Authorization: %s\nAccept: application/json\n' "$AUTH_VALUE" >"$HEADER_FILE"
unset AUTH_VALUE

# curl reads the Authorization header from the file, so the key stays out of `ps` and the logs.
codat() {
  curl -sS -H @"$HEADER_FILE" "$@"
}

# --- Output folder ---------------------------------------------------------

OUT_DIR="$LOG_ROOT/codat-$COMMAND-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"
exec > >(tee -a "$OUT_DIR/run.log") 2>&1
echo "Company $COMPANY_ID · connection $CONNECTION_ID · log folder $OUT_DIR"

C="$BASE_URL/companies/$COMPANY_ID"
CONN="$C/connections/$CONNECTION_ID"
MAPPING_URL="$CONN/bankFeedAccounts/mapping"

status_icon() {
  [[ "$1" =~ ^2 ]] && echo "✅" || echo "❌"
}

check_key() {
  local status
  status=$(codat -o /dev/null -w '%{http_code}' "$C")
  case "$status" in
    2*) echo "✅ Codat accepted the API key." ;;
    401|403) echo "❌ Codat rejected the API key (HTTP $status)." >&2; exit 1 ;;
    *) echo "❌ Codat company lookup returned HTTP $status." >&2; exit 1 ;;
  esac
}

fetch() {
  local name="$1" url="$2" status
  status=$(codat -o "$OUT_DIR/$name.json" -w '%{http_code}' "$url")
  printf '%s %-22s HTTP %s  %s\n' "$(status_icon "$status")" "$name" "$status" "$OUT_DIR/$name.json"
}

show_mapping() {
  codat "$MAPPING_URL" | jq -r '.[] | [.sourceAccountName, .sourceAccountId, .status,
    (.targetAccountId // "-"), (.targetAccountName // "-"), (.feedStartDate // "-")] | @tsv'
}

# --- read ------------------------------------------------------------------

run_read() {
  fetch company              "$C"
  fetch connections          "$C/connections"
  fetch connection           "$CONN"
  fetch source-accounts      "$CONN/connectionInfo/bankFeedAccounts"
  fetch account-mapping      "$MAPPING_URL"
  fetch xero-bank-accounts   "$CONN/data/bankAccounts?page=1&pageSize=100"
  fetch bank-account-options "$CONN/options/bankAccounts"
  fetch push-history         "$C/push?page=1&pageSize=50&orderBy=-requestedOnUtc"
  fetch sync-config          "$C/sync/banking/config"
  [[ -n "$PUSH_OPERATION_KEY" ]] && fetch push-operation "$C/push/$PUSH_OPERATION_KEY"

  echo
  echo "Connection:"
  jq -c '{id, status, platformName, lastSync, created}' "$OUT_DIR/connection.json" || true
  echo "Source accounts:"
  jq -r '(if type == "array" then . else .results // [] end)[]
    | [.id, .accountName, .currency, .status, (.feedStartDate // "-")] | @tsv' "$OUT_DIR/source-accounts.json" || true
  echo "Account mapping:"
  jq -r '(if type == "array" then . else .results // [] end)[]
    | [.sourceAccountId, (.targetAccountId // "-"), (.targetAccountName // "-"), (.status // "-"), (.feedStartDate // "-")] | @tsv' \
    "$OUT_DIR/account-mapping.json" || true
  echo "Push history (latest 50):"
  jq -r '(.results // [])[] | [.requestedOnUtc, .dataType, .status, (.errorMessage // "-" | tostring | .[0:120])] | @tsv' \
    "$OUT_DIR/push-history.json" || true
  if [[ -n "$PUSH_OPERATION_KEY" ]]; then
    echo "Push operation $PUSH_OPERATION_KEY:"
    jq -c '{status, statusCode, errorMessage, requestedOnUtc, completedOnUtc, validation}' "$OUT_DIR/push-operation.json" || true
  fi
}

# --- remap -----------------------------------------------------------------

map_account() {
  local source="$1" target="$2" start="$3" body status file
  file="$OUT_DIR/map-$source.json"
  body=$(jq -n --arg s "$source" --arg t "$target" --arg d "$start" \
    '{sourceAccountId: $s, targetAccountId: $t, feedStartDate: $d}')
  echo "⏳ POST mapping: $body"
  status=$(codat -o "$file" -w '%{http_code}' -X POST -H "Content-Type: application/json" -d "$body" "$MAPPING_URL")
  echo "$(status_icon "$status") HTTP $status → $file"
  jq -c '{status, error, sourceAccountId, targetAccountId, feedStartDate}' "$file" 2>/dev/null || cat "$file"
  [[ "$status" =~ ^2 ]]
}

wait_connected() {
  local source="$1" status=""
  for ((i = 1; i <= POLL_ATTEMPTS; i++)); do
    status=$(codat "$MAPPING_URL" | jq -r --arg s "$source" '.[] | select(.sourceAccountId == $s) | .status')
    if [[ "$status" == "connected" ]]; then
      echo "✅ $source connected (poll $i/$POLL_ATTEMPTS)"
      return 0
    fi
    echo "⏳ $source poll $i/$POLL_ATTEMPTS: $status"
    sleep "$POLL_INTERVAL"
  done
  echo "❌ $source ended at status '$status' after $POLL_ATTEMPTS polls." >&2
  return 1
}

run_remap() {
  echo "Current mapping:"
  show_mapping | tee "$OUT_DIR/mapping-before.tsv"
  echo
  echo "Plan:"
  for item in "${MAPS[@]}"; do
    IFS='|' read -r source target start <<<"$item"
    echo "  source $source → target $target, feedStartDate $start"
  done

  if ! $ASSUME_YES; then
    read -r -p "Proceed with these Codat writes? [y/N] " answer </dev/tty
    [[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "⛔ Stopped before any Codat write."; exit 0; }
  fi

  local failed=0
  for item in "${MAPS[@]}"; do
    IFS='|' read -r source target start <<<"$item"
    echo
    if map_account "$source" "$target" "$start"; then
      wait_connected "$source" || failed=1
    else
      echo "❌ Mapping request for $source returned an error; its response is in $OUT_DIR/map-$source.json." >&2
      failed=1
    fi
  done

  echo
  echo "Mapping after:"
  show_mapping | tee "$OUT_DIR/mapping-after.tsv"
  return "$failed"
}

check_key
if [[ "$COMMAND" == "read" ]]; then
  run_read
else
  run_remap
fi
echo
echo "Responses saved in $OUT_DIR/"
