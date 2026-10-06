import copy
import subprocess
import unittest
from unittest.mock import patch
import merge_guard

class MergeGuardTests(unittest.TestCase):
    def setUp(self):
        self.pr={'state':'open','draft':False,'body':'Refs #1','head':{'sha':'head','ref':'feature/1-test'},'base':{'sha':'base','ref':'main'},'user':{'login':'glyad'}}
        self.reviews=[{'id':1,'user':{'login':'copilot-pull-request-reviewer[bot]','type':'Bot'},'state':'APPROVED','commit_id':'head'}]
        self.calls=[];self.reads=0;self.race=False;self.error=False;self.final_change={}
    def api(self,path,body=None):
        self.calls.append((path,body))
        if self.error: raise subprocess.CalledProcessError(1,['gh','api'])
        if body is not None: return {'merged':True,'sha':'merged'}
        if '/reviews?' in path:return self.reviews
        self.reads+=1;pr=copy.deepcopy(self.pr)
        if self.race and self.reads>1:pr['head']['sha']='new'
        if self.reads>1: pr.update(self.final_change)
        return pr
    def run_guard(self, execute=False):
        with patch.object(merge_guard,'api',self.api), patch.object(merge_guard,'native_issue_links',return_value={1}):
            return merge_guard.merge('glyad/shell-web-components-governance',2,'head',execute)
    def test_unprotected_base_blocks_merge(self):
        self.pr['base']['ref']='feature/unprotected'
        with self.assertRaises(ValueError): self.run_guard(True)
        self.assertTrue(all(b is None for _, b in self.calls))
    def test_missing_native_issue_link_blocks(self):
        with patch.object(merge_guard,'api',self.api), patch.object(merge_guard,'native_issue_links',return_value=set()):
            with self.assertRaises(ValueError): merge_guard.merge('glyad/shell-web-components-governance',2,'head',True)
        self.assertTrue(all(b is None for _,b in self.calls))
    def test_final_state_or_metadata_changes_block(self):
        for change in [{'state':'closed'},{'draft':True},{'body':'Refs #99'}, {'title':'Changed'}, {'base':{'sha':'base','ref':'develop'}}]:
            with self.subTest(change=change):
                self.reads=0;self.calls=[];self.final_change=change
                with self.assertRaises(ValueError): self.run_guard(True)
                self.assertTrue(all(b is None for _,b in self.calls))
    def test_issue_lookup_failure_blocks(self):
        with patch.object(merge_guard,'api',self.api), patch.object(merge_guard,'native_issue_links',side_effect=merge_guard.ApiError(403)):
            with self.assertRaises(merge_guard.ApiError): merge_guard.merge('glyad/shell-web-components-governance',2,'head',True)
        self.assertTrue(all(b is None for _,b in self.calls))
    def test_wrong_issue_reference_blocks(self):
        self.pr['body']='Refs #2'
        with self.assertRaises(ValueError): self.run_guard(True)
        self.assertTrue(all(b is None for _,b in self.calls))
    def test_preflight_does_not_merge(self):
        self.assertFalse(self.run_guard()['merged']);self.assertTrue(all(b is None for _,b in self.calls))
    def test_exact_sha_merge(self):
        self.assertTrue(self.run_guard(True)['merged']);self.assertEqual(self.calls[-1][1]['sha'],'head')
    def test_revoked_approval_blocks(self):
        self.reviews.append(dict(self.reviews[0],id=2,state='DISMISSED'))
        with self.assertRaises(ValueError):self.run_guard(True)
        self.assertTrue(all(b is None for _,b in self.calls))
    def test_api_failure_blocks(self):
        self.error=True
        with self.assertRaises(subprocess.CalledProcessError):self.run_guard(True)
        self.assertTrue(all(b is None for _,b in self.calls))
    def test_changed_head_blocks(self):
        self.race=True
        with self.assertRaises(ValueError):self.run_guard(True)
        self.assertTrue(all(b is None for _,b in self.calls))

class FallbackTests(unittest.TestCase):
    def test_only_seed_404_uses_bootstrap(self):
        import verifier, base64, json
        for base,status,expected in [(verifier.SEED,404,True),(verifier.SEED,403,False),(verifier.SEED,500,False),('other',404,False)]:
            calls=[]
            pr={'state':'open','draft':False,'body':'Refs #1','user':{'login':'glyad'},'head':{'sha':'head','ref':'feature/1-test'},'base':{'sha':base,'ref':'develop'}}
            def api(path,body=None):
                calls.append(path)
                if '/contents/' in path:
                    if verifier.BOOTSTRAP not in path:raise merge_guard.ApiError(status)
                    return {'content':base64.b64encode(json.dumps({'allowed_ai_reviewers':['copilot-pull-request-reviewer[bot]']}).encode()).decode()}
                if '/reviews?' in path:return [{'id':1,'user':{'login':'copilot-pull-request-reviewer[bot]','type':'Bot'},'state':'APPROVED','commit_id':'head'}]
                return pr
            with patch.object(merge_guard,'api',api), patch.object(merge_guard,'native_issue_links',return_value={1}):
                if expected: self.assertTrue(merge_guard.merge(verifier.REPO,2,'head')['authorized'])
                else:
                    with self.assertRaises(merge_guard.ApiError):merge_guard.merge(verifier.REPO,2,'head')
            self.assertEqual(any(verifier.BOOTSTRAP in p for p in calls),expected)

class NativeLinkTests(unittest.TestCase):
    def test_cross_repository_link_is_not_accepted(self):
        import json
        payload={'data':{'repository':{'pullRequest':{'closingIssuesReferences':{'pageInfo':{'hasNextPage':False},'nodes':[{'number':1,'repository':{'nameWithOwner':'other/repo'}}]}}}}}
        result=subprocess.CompletedProcess([],0,json.dumps(payload),'')
        with patch.object(merge_guard.subprocess,'run',return_value=result):
            self.assertEqual(merge_guard.native_issue_links('glyad/shell-web-components',2),set())
    def test_graphql_error_and_truncated_links_fail_closed(self):
        import json
        for payload in [{'errors':[{'message':'denied'}]},{'data':{'repository':{'pullRequest':{'closingIssuesReferences':{'pageInfo':{'hasNextPage':True},'nodes':[]}}}}}]:
            result=subprocess.CompletedProcess([],0,json.dumps(payload),'')
            with patch.object(merge_guard.subprocess,'run',return_value=result):
                with self.assertRaises((merge_guard.ApiError,ValueError)):merge_guard.native_issue_links('glyad/shell-web-components',2)

if __name__=="__main__":unittest.main()
