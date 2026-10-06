"""Trusted control-repository checker. Never checks out or executes target PR code."""
import base64
import json
import os
import urllib.request
import urllib.error

REPO = 'glyad/shell-web-components'
CHECK = 'trusted-independent-ai-review'
SEED = '731d72ca1a9511981f1053b8d230f34719d3c23e'
BOOTSTRAP = '20c3a12bd1d9d1152456dd280351a7cd7719e1e4'


def api(path, body=None):
    request = urllib.request.Request('https://api.github.com/' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28',
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def pages(path):
    page = 1
    while True:
        batch = api(f'{path}?per_page=100&page={page}')
        yield from batch
        if len(batch) < 100:
            return
        page += 1


def approved(pr, policy, reviews):
    if not isinstance(policy, dict):
        raise ValueError('Authoritative policy must be a JSON object')
    allowed = policy.get('allowed_ai_reviewers')
    if not isinstance(allowed, list) or not allowed or any(not isinstance(x, str) for x in allowed):
        raise ValueError('Invalid authoritative reviewer policy')
    latest = {}
    for review in sorted(reviews, key=lambda r: r['id']):
        user = review['user']
        if user['login'] in allowed and user['type'] == 'Bot' and user['login'] != pr['user']['login']:
            if review['state'] in {'APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'}:
                latest[user['login']] = review
    # Any current blocking decision requires another independent review cycle.
    if any(r['state'] == 'CHANGES_REQUESTED' for r in latest.values()):
        return False
    return any(r['state'] == 'APPROVED' and r['commit_id'] == pr['head']['sha']
               for r in latest.values())


def evaluate(number):
    root = f'repos/{REPO}'
    pr = api(f'{root}/pulls/{number}')
    head, base = pr['head']['sha'], pr['base']['sha']
    passed = False
    detail = 'An independent allowed AI bot must approve the current head.'
    try:
        try:
            content = api(f'{root}/contents/.github/ai-dlc.json?ref={base}')
        except urllib.error.HTTPError as error:
            if error.code != 404 or base != SEED:
                raise
            content = api(f'{root}/contents/.github/ai-dlc.json?ref={BOOTSTRAP}')
        policy = json.loads(base64.b64decode(content['content']))
        passed = approved(pr, policy, list(pages(f'{root}/pulls/{number}/reviews')))
        if passed:
            detail = 'Allowed independent AI approval matches this exact head.'
        if any(other['number'] != number and other['head']['sha'] == head
               for other in pages(f'{root}/pulls')):
            passed = False
            detail = 'Multiple open PRs share this head; create a distinct commit before approval.'
        fresh = api(f'{root}/pulls/{number}')
        if fresh['state'] != 'open' or fresh['draft'] or (fresh['head']['sha'], fresh['base']['sha']) != (head, base):
            passed = False
            detail = 'PR is draft, closed, or changed during verification; retry.'
    except (ValueError, KeyError, urllib.error.HTTPError, urllib.error.URLError) as error:
        passed = False
        detail = 'Verification failed closed: ' + type(error).__name__
    api(f'{root}/check-runs', {'name': CHECK, 'head_sha': head,
        'status': 'completed', 'conclusion': 'success' if passed else 'failure',
        'external_id': f'{REPO}:{number}:{head}:{base}',
        'output': {'title': 'Independent AI approval verified' if passed else 'AI approval blocked',
                   'summary': f'PR #{number}; head {head}; protected base {base}.\n{detail}'}})
    return passed


if __name__ == '__main__':
    for pr in pages(f'repos/{REPO}/pulls'):
        if not pr['draft']:
            print(json.dumps({'pr': pr['number'], 'approved': evaluate(pr['number'])}))
