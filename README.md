# Trusted AI approval verifier — deployment proposal

This control repository runs trusted main-branch code and reads GitHub's review records. It never checks out, imports, or executes shell-web-components PR code.

## Account authorization needed

Create a dedicated GitHub App installed only on glyad/shell-web-components:
- Contents: read (read authoritative policy at the protected base commit).
- Pull requests: read (read PR head and independent AI reviews).
- Checks: write (publish the trusted check).
- Metadata: read (GitHub's mandatory permission).
No repository code-write, merge, administration, or organization permission. No external hosting service is required.

Store its private key only in this control repository's `trusted-verifier` environment, restricted to the main branch. Do not store it in shell-web-components or disclose it in logs/chat. Keep workflow token permissions read-only. Protect control main against direct writes, deletions and force pushes; require independent AI-reviewed PRs for changes. No target-PR trigger may execute with the key.

Only after installation and a real check appear, replace the target ruleset's diagnostic `independent-ai-review` requirement with `trusted-independent-ai-review`, binding its expected source to this App's numeric integration ID. Keep governance, native approval, stale-review dismissal and conversation-resolution requirements. No bypass actors.

The target's original review workflow remains diagnostic. A similarly named GitHub Actions job cannot satisfy the App-bound check.

## Validation and operational limits

Run `python3 -m unittest discover -s tests -v`. Tests cover current-head approval, stale approval, comments, dismissal, requested changes, human impersonation, self-review and revoked policy. API failures produce failure checks or no success; both block merge. Scheduled execution can be delayed by GitHub; main-only manual dispatch provides a recovery path. Native stale-review dismissal and strict base checks remain required to cover updates occurring after a verification snapshot.

Deployment is pending account authorization, App registration, key provisioning, environment restrictions, control-repository protection, App-source ruleset binding, and live end-to-end verification. This directory does not claim the trust finding resolved.
