"""AI-operator merge gate. Run trusted code outside all target PR workflows.

The operator's existing GitHub CLI credentials perform the merge; the verifier
App has no merge permission. GitHub native protections must remain enforced.
"""
import argparse
import base64
import json
import subprocess
import verifier

REPOS = {'glyad/shell-web-components', 'glyad/shell-web-components-governance'}

def api(path, body=None):
    args = ['gh', 'api', path]
    if body is not None: args += ['--method', 'PUT', '--input', '-']
    return json.loads(subprocess.check_output(args,
        input=json.dumps(body) if body is not None else None, text=True))

def authorize(repo, number, expected_head):
    if repo not in REPOS: raise ValueError('Repository outside authorized scope')
    root = f'repos/{repo}'
    pr = api(f'{root}/pulls/{number}')
    if pr['state'] != 'open' or pr['draft'] or pr['head']['sha'] != expected_head:
        raise ValueError('PR is not open/ready at the expected commit')
    if repo == verifier.REPO:
        base = pr['base']['sha']
        try: policy_file = api(f'{root}/contents/.github/ai-dlc.json?ref={base}')
        except subprocess.CalledProcessError:
            if base != verifier.SEED: raise
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
    if (fresh['head']['sha'], fresh['base']['sha']) != (pr['head']['sha'], pr['base']['sha']):
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
