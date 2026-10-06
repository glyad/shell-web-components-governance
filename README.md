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

Run `python3 -m unittest discover -s tests -v`. Tests cover current-head approval, stale approval, comments, dismissal, requested changes, human impersonation, self-review and revoked policy. Once a PR head is known, the checker attempts to replace its prior result with failure when verification fails. An initial read failure or inability to publish can leave an older result visible; a cached successful check alone is not fresh merge authorization. Scheduled execution can be delayed by GitHub; main-only manual dispatch provides a recovery path. Native stale-review dismissal and strict base checks remain required to cover updates occurring after a verification snapshot.

Deployment is pending account authorization, App registration, key provisioning, environment restrictions, control-repository protection, App-source ruleset binding, and live end-to-end verification. This directory does not claim the trust finding resolved.

## Event-driven revalidation and bootstrap sequence

The target repository must install a trusted, default-branch `workflow_run` relay for the diagnostic Independent AI review gate. On completion of review-triggered or PR-update runs it dispatches `verify.yml` on `main` in this control repository. The relay never checks out code or downloads artifacts from the triggering run. A narrowly scoped fine-grained token permits Actions write only on the control repository; it cannot publish the verifier App's check, edit code, or merge. Store that relay token in a target environment restricted to `main`. The verifier re-reads GitHub API state and ignores dispatch payloads. Scheduled polling is recovery, not the primary revocation path.

Until relay deployment and a live revocation exercise pass, this verifier is not production-ready. Native approval requirements, stale-review dismissal and strict checks remain mandatory. All bootstrap merges are AI-operated and must re-read live reviews immediately before the SHA-bound merge; API errors stop that operation. GitHub dispatch/runner outages can delay invalidation, so cached checks must not be described as guaranteed fail-closed authorization.

## Mandatory live merge authorization

AI operators must use trusted `merge_guard.py` outside target PR workflows for every merge into either repository. It reads live GitHub reviews immediately before an exact-head-SHA merge, rejects revoked/stale/self/human approvals and changed refs, and stops on API errors. GitHub's native approval, strict-check and conversation requirements remain enforced; the guard never bypasses them. The operator's existing authenticated GitHub CLI performs the merge; the verifier App has no merge rights and no additional merge credential is provisioned.

Run `python3 merge_guard.py <repository> <pr-number> <expected-head-sha>` for preflight; only an authorized AI operator adds `--execute` after validation. Cached successful verifier checks are evidence, never sufficient merge authorization. This operator contract is mandatory even when event notification or scheduled recovery is delayed. Account owners retain administrative power to change rules; human engineering approvals or merges violate the project's product-management-only policy.
