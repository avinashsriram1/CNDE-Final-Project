#!/usr/bin/env bash
# One-time GitHub setup for K2 / ADM-04 / GOV-02. Run by the repo admin (Avinash)
# AFTER the scaffold PR has merged and CI has run at least once on main
# (the required check "lint-and-test" must exist before it can be required).
#
# Usage: bash Scripts/deploy/github_repo_setup.sh <gh-user-1> <gh-user-2> <gh-user-3>
# Requires: GitHub CLI (`gh auth login`) with admin rights on the repo.
set -euo pipefail

REPO="avinashsriram1/CNDE-Final-Project"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <teammate-github-username> [...]" >&2
  exit 1
fi

echo "==> Inviting collaborators with write access"
for user in "$@"; do
  gh api -X PUT "repos/${REPO}/collaborators/${user}" -f permission=push >/dev/null
  echo "    invited ${user} (they must accept the email/GitHub invite)"
done

echo "==> Protecting main: PR + 1 approval + green CI, no force pushes"
gh api -X PUT "repos/${REPO}/branches/main/protection" \
  -H "Accept: application/vnd.github+json" --input - <<'JSON'
{
  "required_status_checks": { "strict": false, "contexts": ["lint-and-test"] },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

echo "==> Enabling secret scanning + push protection (free on public repos)"
gh api -X PATCH "repos/${REPO}" --input - <<'JSON' >/dev/null || \
  echo "    Could not enable via API; turn on in Settings > Code security instead."
{
  "security_and_analysis": {
    "secret_scanning": { "status": "enabled" },
    "secret_scanning_push_protection": { "status": "enabled" }
  }
}
JSON

echo "Done. Verify under Settings > Branches and Settings > Collaborators."
