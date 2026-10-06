import copy
import unittest
from verifier import approved

BOT = 'copilot-pull-request-reviewer[bot]'
class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.pr = {'user': {'login': 'glyad'}, 'head': {'sha': 'current'}}
        self.policy = {'allowed_ai_reviewers': [BOT]}
        self.review = {'id': 1, 'user': {'login': BOT, 'type': 'Bot'}, 'state': 'APPROVED', 'commit_id': 'current'}
    def check(self, reviews):
        return approved(self.pr, self.policy, reviews)
    def test_current_approval(self):
        self.assertTrue(self.check([self.review]))
    def test_comment_does_not_revoke(self):
        comment = dict(self.review, id=2, state='COMMENTED')
        self.assertTrue(self.check([comment, self.review]))
    def test_stale_approval(self):
        self.assertFalse(self.check([dict(self.review, commit_id='old')]))
    def test_dismissed(self):
        self.assertFalse(self.check([self.review, dict(self.review, id=2, state='DISMISSED')]))
    def test_changes_requested(self):
        self.assertFalse(self.check([self.review, dict(self.review, id=2, state='CHANGES_REQUESTED')]))
    def test_human_impersonation(self):
        r = copy.deepcopy(self.review); r['user']['type'] = 'User'
        self.assertFalse(self.check([r]))
    def test_self_approval(self):
        self.pr['user']['login'] = BOT
        self.assertFalse(self.check([self.review]))
    def test_revoked_policy(self):
        self.policy['allowed_ai_reviewers'] = ['different[bot]']
        self.assertFalse(self.check([self.review]))
if __name__ == '__main__': unittest.main()

class SnapshotTests(unittest.TestCase):
    def test_checks_are_bound_and_races_fail(self):
        import verifier, base64, json
        from unittest.mock import patch
        for changed, denied, expected in [(False, False, True), (True, False, False), (False, True, False)]:
            calls = []; reads = [0]
            def api(path, body=None):
                if body is not None: calls.append(body); return {}
                if '/contents/' in path:
                    if denied:
                        import urllib.error
                        raise urllib.error.HTTPError(path,403,'Denied',{},None)
                    self.assertIn('ref=protected',path)
                    return {'content':base64.b64encode(json.dumps({'allowed_ai_reviewers':[BOT]}).encode()).decode()}
                if '/reviews?' in path:
                    return [{'id':1,'user':{'login':BOT,'type':'Bot'},'state':'APPROVED','commit_id':'current'}]
                reads[0] += 1
                return {'state':'open','draft':False,'user':{'login':'glyad'},'head':{'sha':'new' if changed and reads[0]>1 else 'current'},'base':{'sha':'protected'}}
            with patch.object(verifier,'api',api): self.assertEqual(verifier.evaluate(2),expected)
            self.assertEqual(calls[0]['head_sha'],'current')
            self.assertEqual(calls[0]['conclusion'],'success' if expected else 'failure')
