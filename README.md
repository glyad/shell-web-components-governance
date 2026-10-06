# Trusted AI review and merge service

Status: the initial worker was reviewed and deployed through PR #2. The worker is currently disabled pending review and deployment of PR #4, which adds live native Issue-link enforcement and final PR-state checks. Required target merge protections remain active. No Web Components or product release is implemented here.

## Why a trusted merge service is required

GitHub check results attach to commits and do not expire when an approval is revoked. Event notification and scheduled recovery can be delayed. A cached successful check cannot be the final authorization for a merge.

The protected-main worker checks actual AI reviews, publishes an App-source-bound check, then re-reads current approval immediately before a SHA-bound merge. API errors, revoked/stale/self/human approvals or changed refs stop the merge. Native approval, strict status checks and conversation requirements stay enforced.

A separate target ruleset restricts protected branch updates to this App through PRs. Its App exception applies only to that update restriction; the existing review/check ruleset retains no bypass actors. Thus other actors cannot merge using a cached result, and the App cannot bypass the independent review requirements. Account owners can still administer rulesets, which is an explicit account-authorization responsibility.

## Permissions requiring account approval

The installed Shell WC Trusted AI Verifier App (ID 5210232), only on glyad/shell-web-components, needs:
- Contents: read and write, so it can perform protected PR merges.
- Pull requests: read, to read PR state and actual reviews.
- Checks: write, to publish approval evidence.
- Metadata: mandatory read.

Contents write is broader than a merge-only permission: it can also edit repository files. The worker is confined to independently reviewed protected-main code, a main-only environment and GitHub-native required PR/check rules. It never checks out or executes target PR code. The account owner accepted Contents write on October 6, 2026. Do not expand permissions without explicit account authorization.

The App key is stored only in this control repository's trusted-verifier environment, restricted to main. The relay's separate fine-grained token has Actions read/write only on this control repository, expires November 5, 2026, and cannot edit or merge code. Store it in the target's main-only trusted-review-relay environment. No external hosting or additional subscription is needed.

## Deployment sequence

1. Obtain account approval for App Contents write and the target's App-only update restriction.
2. Verify all control PR tests, independent current-head Copilot approval and resolved conversations; merge this control PR through its native gates using live merge_guard preflight and exact SHA. This bootstraps the trusted worker; it does not weaken target protection.
3. Before dispatching the worker, apply deployment/target-merge-actor-ruleset.json as a separate target ruleset. Preserve the other target ruleset without any App bypass. Bind required trusted-independent-ai-review to App ID 5210232, retaining governance, native approval, stale dismissal and strict checks.
4. Dispatch verify.yml on main. Verify a missing/revoked approval cannot merge and the published check belongs to the expected App. Only an independently approved target PR can merge.
5. Promote Phase 0 governance to target main through its documented protected PR. Its workflow_run relay then dispatches current review-state revalidation; scheduled polling remains recovery.
6. Test live approval/revocation, actor restrictions and required-check source before closing Phase 0. Do not claim deployment complete from local tests alone.

## Validation

Run python3 -m unittest discover -s tests -v. The 25 verifier tests cover live native Issue associations, final draft/closed/metadata races, review identity, current head, revocation, comments, changes requested, shared-commit rejection, policy types, exact seed/404 fallback, authorization races, API errors and SHA-bound merge calls. API failures may leave older status evidence visible; App-only merges with fresh authorization prevent that evidence alone from granting a merge. The App's scheduled scan cannot merge control-repository PRs because its installation is restricted to the target repository.

Superpowers skills are opt-in. Human engineering approvals and merges violate the product-management-only contract.

## Review batching
Automatic Copilot review rules are disabled on both repositories. Consolidate fixes and pass local tests plus CI before requesting one review with user authorization. No spending-limit increase is authorized. The disabled worker must not be re-enabled until PR #4 is independently approved and merged, and native Issue lookup is verified with its restricted App token.
