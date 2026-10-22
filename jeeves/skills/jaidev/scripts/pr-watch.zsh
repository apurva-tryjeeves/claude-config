#!/usr/bin/env zsh
# Watch PRs and print one line per change: new head, CI result, review decision, merge or close.
# Usage (from the target repo's directory, so gh picks the right account):
#   scripts/pr-watch.zsh <interval-seconds> <pr-number> [<pr-number> ...]
# Exits when every PR is merged or closed.
interval=$1; shift
typeset -A last
while true; do
  open=0
  for pr in "$@"; do
    row=$(gh pr view "$pr" --json number,state,headRefOid,reviewDecision,statusCheckRollup 2>/dev/null | jq -r '
      (.statusCheckRollup // []) as $c
      | (if ($c | length) == 0 then "none"
         elif any($c[]; (.conclusion // .state) | IN("FAILURE","ERROR","TIMED_OUT","CANCELLED")) then "failed"
         elif any($c[]; (.status // "") | IN("IN_PROGRESS","QUEUED","PENDING")) or any($c[]; (.state // "") == "PENDING") then "pending"
         else "passed" end) as $ci
      | "PR #\(.number) \(.state) head=\(.headRefOid[0:7]) ci=\($ci) review=\(.reviewDecision | if . == null or . == "" then "none" else . end)"')
    [[ -z $row ]] && continue
    [[ $row != *" OPEN "* ]] || open=1
    if [[ ${last[$pr]} != $row ]]; then
      last[$pr]=$row
      print -- "$row"
    fi
  done
  (( open )) || break
  sleep $interval
done
