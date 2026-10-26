#!/usr/bin/env bash
# Print one line per ticket when its Jaidev PR opens: "ACC-<n> PR opened: #<pr> <state> head=<sha7>".
# Usage (from the target repo's directory, so gh picks the right account):
#   scripts/pr-open-watch.sh <interval-seconds> <ticket-number> [<ticket-number> ...]
# Exits when every ticket has been seen.
interval=$1; shift
pending=("$@")
while ((${#pending[@]})); do
  still=()
  for n in "${pending[@]}"; do
    row=$(gh pr list --head "jai-dev/acc-$n" --state all --json number,headRefOid,state \
      --jq 'if length == 0 then "" else .[0] | "#\(.number) \(.state) head=\(.headRefOid[0:7])" end' 2>/dev/null)
    if [[ -n $row ]]; then
      echo "ACC-$n PR opened: $row"
    else
      still+=("$n")
    fi
  done
  pending=("${still[@]}")
  if ((${#pending[@]})); then sleep "$interval"; fi
done
