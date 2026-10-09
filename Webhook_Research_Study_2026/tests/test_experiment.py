import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from experiment import connect,handle,run
class StudyTests(unittest.TestCase):
 def test_baseline_duplicates(self):
  c=connect();self.assertTrue(handle(c,'x','baseline',{})[0]);handle(c,'x','baseline',{})
  self.assertEqual(c.execute('SELECT COUNT(*) FROM effects').fetchone()[0],2)
 def test_idempotent(self):
  c=connect();handle(c,'x','idempotent',{});handle(c,'x','idempotent',{})
  self.assertEqual(c.execute('SELECT COUNT(*) FROM effects').fetchone()[0],1)
 def test_retry_recovers_transient_failure(self):
  c=connect();self.assertTrue(handle(c,'x','idempotent_retry',{'x':1})[0])
 def test_no_retry_fails_transient(self):
  c=connect();self.assertFalse(handle(c,'x','idempotent',{'x':1})[0])
 def test_reproducible_counts(self):
  a=run('baseline',100,seed=12);b=run('baseline',100,seed=12)
  for k in ('duplicate_effects','unique_effects','successful_requests'):
   self.assertEqual(a[k],b[k])
if __name__=='__main__':unittest.main()
