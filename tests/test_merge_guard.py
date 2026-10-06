import copy
import subprocess
import unittest
from unittest.mock import patch
import merge_guard

class MergeGuardTests(unittest.TestCase):
    def setUp(self):
        self.pr={'state':'open','draft':False,'head':{'sha':'head'},'base':{'sha':'base'},'user':{'login':'glyad'}}
        self.reviews=[{'id':1,'user':{'login':'copilot-pull-request-reviewer[bot]','type':'Bot'},'state':'APPROVED','commit_id':'head'}]
        self.calls=[];self.reads=0;self.race=False;self.error=False
    def api(self,path,body=None):
        self.calls.append((path,body))
        if self.error: raise subprocess.CalledProcessError(1,['gh','api'])
        if body is not None: return {'merged':True,'sha':'merged'}
        if '/reviews?' in path:return self.reviews
        self.reads+=1;pr=copy.deepcopy(self.pr)
        if self.race and self.reads>1:pr['head']['sha']='new'
        return pr
    def run_guard(self, execute=False):
        with patch.object(merge_guard,'api',self.api):
            return merge_guard.merge('glyad/shell-web-components-governance',2,'head',execute)
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
if __name__=='__main__':unittest.main()
