from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim.tracks import COMPILED_TRACKS
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/review-data/'):
            tid=self.path.rsplit('/',1)[-1]
            data=([{'id':t.id,'name':t.name} for t in COMPILED_TRACKS] if tid=='list' else next(t for t in COMPILED_TRACKS if t.id==tid).to_client_payload())
            blob=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(blob);return
        self.path='/scratch/scenery_review.html' if self.path=='/review' else '/public'+self.path
        return super().do_GET()
    def log_message(self,*args):pass
print('Starting review server',flush=True)
ThreadingHTTPServer(('127.0.0.1',int(sys.argv[1]) if len(sys.argv)>1 else 8091),lambda *a,**kw:Handler(*a,directory=str(ROOT),**kw)).serve_forever()
