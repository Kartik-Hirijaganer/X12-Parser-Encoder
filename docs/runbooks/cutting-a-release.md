# Cutting A Release

You should be done in < 5 min once the version is chosen and the repository
settings below are already configured.

GitHub Releases are the canonical distribution channel. The validated tag
workflow publishes the Python package, GHCR image, Lambda zip plus SHA256, and
Terraform modules tarball plus SHA256. The modules tarball excludes any local
`.terraform` working directories.

## Decide The Version

- RC from a final release: `python scripts/bump_version.py rc`
- Next RC from an existing RC: `python scripts/bump_version.py rc`
- Final from an RC: `python scripts/bump_version.py final`
- Patch from a final release: `python scripts/bump_version.py patch`
- Explicit version: `python scripts/bump_version.py 1.0.1`

## Cut The Tag

```bash
python scripts/bump_version.py <target>
python -m unittest discover -s scripts/tests -p "test_*.py"
python scripts/check_version_sync.py
python scripts/validate_release.py "v$(cat VERSION)"
export VERSION="$(cat VERSION)"
export BRANCH="release/v${VERSION}"
git switch -c "${BRANCH}"
git diff -- VERSION CHANGELOG.md README.md \
  packages/x12-edi-tools/pyproject.toml \
  packages/x12-edi-tools/src/x12_edi_tools/__about__.py \
  apps/api/pyproject.toml \
  apps/web/package.json \
  apps/web/package-lock.json
git add VERSION CHANGELOG.md README.md \
  packages/x12-edi-tools/pyproject.toml \
  packages/x12-edi-tools/src/x12_edi_tools/__about__.py \
  apps/api/pyproject.toml \
  apps/web/package.json \
  apps/web/package-lock.json
git commit -m "Release v$(cat VERSION)"
git push -u origin "${BRANCH}"
gh pr create --fill --base main --head "${BRANCH}"
gh pr merge --squash --delete-branch
git switch main
git pull --ff-only
git tag "v${VERSION}"
```

With release tag protection enabled, push the tag through the approved release
automation GitHub App identity, not a personal token:

```bash
export OWNER="<owner>"
export REPO="<repo>"
export RELEASE_APP_TOKEN="<installation-token>"
git push "https://x-access-token:${RELEASE_APP_TOKEN}@github.com/${OWNER}/${REPO}.git" "v$(cat VERSION)"
```

Watch the workflow:

```bash
gh run watch --repo "${OWNER}/${REPO}" --workflow release.yml
gh release view "v$(cat VERSION)" --repo "${OWNER}/${REPO}" --web
```

## Roll Back A Bad Release

```bash
export VERSION="<bad-version>"
gh release delete "v${VERSION}" --cleanup-tag --yes
git revert <release-bump-commit-sha>
git push origin HEAD:rollback/v${VERSION}
gh pr create --fill --base main --head "rollback/v${VERSION}"
gh pr merge --squash --delete-branch
```

If the tag ruleset blocks cleanup, repeat the delete or tag deletion with the
release automation GitHub App token:

```bash
git push "https://x-access-token:${RELEASE_APP_TOKEN}@github.com/${OWNER}/${REPO}.git" ":refs/tags/v${VERSION}"
```

## Repository Settings

Run these once per repository. Prefer the GitHub UI if the organization has a
central ruleset template; the commands below are the equivalent `gh` API path.

Protect release tags so only the release automation GitHub App can create,
update, or delete `v*.*.*` tags. Set `RELEASE_APP_INTEGRATION_ID` to the GitHub
App integration id that owns the release-token minting path.

```bash
export RELEASE_APP_INTEGRATION_ID="<github-app-integration-id>"
gh api --method POST "repos/${OWNER}/${REPO}/rulesets" --input - <<JSON
{
  "name": "Protect release tags",
  "target": "tag",
  "enforcement": "active",
  "bypass_actors": [
    {
      "actor_id": ${RELEASE_APP_INTEGRATION_ID},
      "actor_type": "Integration",
      "bypass_mode": "always"
    }
  ],
  "conditions": {
    "ref_name": {
      "include": ["refs/tags/v*.*.*"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "creation" },
    { "type": "update" },
    { "type": "deletion" }
  ]
}
JSON
```

Protect `main` and require the release and docs checks before merge. In the UI,
use the exact check names GitHub shows for this repository: `release-validate`
from `Release Validate` and `docs-drift` from `Docs Drift`.

```bash
gh api --method POST "repos/${OWNER}/${REPO}/rulesets" --input - <<'JSON'
{
  "name": "Protect main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "release-validate" },
          { "context": "docs-drift" }
        ]
      }
    }
  ]
}
JSON
```

Require a reviewer before production deploys:

```bash
export REVIEWER_USER="<github-username>"
export REVIEWER_ID="$(gh api "users/${REVIEWER_USER}" --jq .id)"
gh api --method PUT "repos/${OWNER}/${REPO}/environments/production" --input - <<JSON
{
  "wait_timer": 0,
  "reviewers": [
    {
      "type": "User",
      "id": ${REVIEWER_ID}
    }
  ]
}
JSON
```

Verify the tag rule by attempting a personal tag push. It should be rejected:

```bash
git tag v1.0.2
git push origin v1.0.2
git tag -d v1.0.2
```
