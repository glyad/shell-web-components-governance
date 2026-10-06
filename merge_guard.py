"""AI-operator merge gate. Run trusted code outside all target PR workflows.

The protected worker's restricted App token performs target merges. The AI
operator may preflight or bootstrap the control repository with existing CLI
credentials. GitHub native protections must remain enforced.
"""
import argparse
import base64
import json
import re
import subprocess
import verifier

REPOS = {'glyad/shell-web-components', 'glyad/shell-web-components-governance'}

class ApiError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f'GitHub API failed (HTTP {status or "unknown"})')

def api(path, body=None):
    args = ['gh', 'api', '--include', path]
    if body is not None: args += ['--method', 'PUT', '--input', '-']
    result = subprocess.run(args, input=json.dumps(body) if body is not None else None,
                            text=True, capture_output=True)
    statuses = re.findall(r'^HTTP/\S+\s+(\d{3})', result.stdout, re.MULTILINE)
    status = int(statuses[-1]) if statuses else None
    if result.returncode or status is None or not 200 <= status < 300:
        raise ApiError(status)
    return json.loads(result.stdout.replace('\r\n','\n').split('\n\n',1)[1])

def authorize(repo, number, expected_head):
    if repo not in REPOS: raise ValueError('Repository outside authorized scope')
    root = f'repos/{repo}'
    pr = api(f'{root}/pulls/{number}')
    if pr['state'] != 'open' or pr['draft'] or pr['head']['sha'] != expected_head:
        raise ValueError('PR is not open/ready at the expected commit')
    target = pr['base']['ref']
    protected = target in {'main', 'develop'} or target.startswith(('release/', 'hotfix/'))
    if (repo == verifier.REPO and not protected) or (repo != verifier.REPO and target != 'main'):
        raise ValueError('PR base branch is outside protected merge scope')
    if repo == verifier.REPO:
        base = pr['base']['sha']
        try: policy_file = api(f'{root}/contents/.github/ai-dlc.json?ref={base}')
        except ApiError as error:
            if error.status != 404 or base != verifier.SEED: raise
            policy_file = api(f'{root}/contents/.github/ai-dlc.json?ref={verifier.BOOTSTRAP}')
        policy = json.loads(base64.b64decode(policy_file['content']))
    else:
        policy = {'allowed_ai_reviewers': ['copilot-pull-request-reviewer[bot]']}
    reviews = []; page = 1
    while True:
        batch = api(f'{root}/pulls/{number}/reviews?per_page=100&page={page}')
        reviews += batch
        if len(batch) < 100: break
        page += 1
    if not verifier.approved(pr, policy, reviews):
        raise ValueError('Live current-head independent AI approval is missing or revoked')
    fresh = api(f'{root}/pulls/{number}')
    if (fresh['head']['sha'], fresh['base']['sha'], fresh['base']['ref']) != (pr['head']['sha'], pr['base']['sha'], target):
        raise ValueError('PR changed during merge authorization')
    return pr

def merge(repo, number, expected_head, execute=False):
    authorize(repo, number, expected_head)
    if not execute: return {'authorized': True, 'merged': False, 'head': expected_head}
    # Exact SHA plus native approval/check/thread rules protect the final mutation.
    result = api(f'repos/{repo}/pulls/{number}/merge',
                 {'sha': expected_head, 'merge_method': 'merge'})
    if not result.get('merged'): raise RuntimeError('GitHub refused protected merge')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('repository', choices=sorted(REPOS))
    parser.add_argument('number', type=int)
    parser.add_argument('head')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(merge(args.repository, args.number, args.head, args.execute)))
