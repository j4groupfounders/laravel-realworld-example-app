"""Independent route mutations; preserve source, tests, and empty DB baseline."""
import pathlib,subprocess,json,os,signal,time,xml.etree.ElementTree as ET
root=pathlib.Path('.')
mutations=[
 ('tags-status','app/Http/Controllers/Api/TagController.php','respondWithTransformer($tags);','respondWithTransformer($tags, 201);'),
 ('article-count','app/RealWorld/Transformers/Transformer.php','$countName => $paginated->getTotal()','$countName => -1'),
 ('unauthorized-status','app/Http/Middleware/AuthenticateWithJWT.php','], 401);','], 200);'),
 ('missing-route-status','app/Exceptions/Handler.php','$statusCode = $this->getStatusCode($exception);','$statusCode = $this->getStatusCode($exception); if ($statusCode === 404) { $statusCode = 200; }'),
 ('login-error-status','app/Exceptions/Handler.php',"return response()->json(['errors' => $validationErrors], 422);","return response()->json(['errors' => $validationErrors], 200);")]
results=[]
for name,file,old,new in mutations:
 p=root/file;original=p.read_text();assert old in original
 dest=root/'seed-evidence'/name;dest.mkdir(parents=True,exist_ok=True);server=None
 try:
  p.write_text(original.replace(old,new,1))
  with (dest/'tests.log').open('w') as log:
   test=subprocess.run(['vendor/bin/phpunit','--log-junit',str(dest/'tests.xml')],stdout=log,stderr=subprocess.STDOUT,timeout=120)
  tree=ET.parse(dest/'tests.xml');cases=tree.findall('.//testcase');assert len(cases)==56,'test inventory changed'
  errors=tree.findall('.//error');assert not errors,'test infrastructure/runtime failure is not mutation detection'
  subprocess.run(['php','artisan','migrate','--force'],check=True,stdout=subprocess.DEVNULL)
  with (dest/'boot.log').open('w') as log:
   server=subprocess.Popen(['php','artisan','serve','--host=127.0.0.1','--port=3000'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   with (dest/'probe.log').open('w') as probe:
    check=subprocess.run(['python3','j4_probe.py'],stdout=probe,stderr=subprocess.STDOUT,timeout=90)
   output=(dest/'probe.log').read_text();assert 'CHARACTERIZATION DRIFT' in output and 'BOOT FAILED' not in output
   pathlib.Path('surface.actual.json').replace(dest/'surface.json')
  results.append(dict(fault=name,project_detected=test.returncode!=0,harness_detected=check.returncode!=0,project_failures=len(tree.findall('.//failure'))))
 finally:
  p.write_text(original)
  if server:os.killpg(server.pid,signal.SIGTERM);server.wait(timeout=15)
  time.sleep(1)
pathlib.Path('seed-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
a=sum(r['project_detected'] for r in results);b=sum(r['project_detected'] or r['harness_detected'] for r in results)
assert b>=4 and 5-b<=(5-a)/2
