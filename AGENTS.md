# Trusted governance control repository

Humans provide product management and account authorization only. All architecture, implementation, testing, review and release work is AI-operated. Do not implement Web Components here.

Use short-lived Issue-linked feature branches and pull requests into protected main. Preserve independent Copilot approval, stale-review dismissal, strict verifier-tests checks and resolved review conversations. Never bypass rulesets or reduce approval requirements to unblock a merge.

Execute reviewed merge_guard.py outside PR-controlled workflows for every merge in either governed repository. Re-read live current-head independent AI approval and merge only the exact authorized SHA. Stop on API errors, changed refs or revoked approval. Cached successful checks do not authorize merging.

Never print, commit or expose App private keys or workflow-notification tokens. Only protected main workflows may access trusted-verifier environment secrets. Never execute target PR code with these credentials. The notification token has Actions permission only in this control repository; the verifier App has no code-write or merge permission.

Superpowers skills are opt-in; use them only when explicitly requested for the current task.
