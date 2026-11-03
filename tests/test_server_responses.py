"""Large scenery responses must arrive intact on transports with bounded writes."""
import io
import json
import unittest

from server import F1RequestHandler


class LimitedTransport(io.BytesIO):
    def write(self, data):
        if len(data)>65536:
            raise OSError('Transport cannot accept a single oversized write')
        return super().write(data)


class ServerResponseTests(unittest.TestCase):
    def test_large_scenery_state_is_complete_and_has_correct_content_length(self):
        handler=object.__new__(F1RequestHandler)
        handler.wfile=LimitedTransport()
        headers={}
        statuses=[]
        handler.send_response=lambda status:statuses.append(status)
        handler.send_header=lambda name,value:headers.__setitem__(name,value)
        handler.end_headers=lambda:None
        payload={'track':{'name':'Jeddah — الواجهة البحرية','objects':[
            {'x':i*.3,'y':i*1.7,'name':'Waterfront landscaping'} for i in range(15000)]}}
        handler._send_json(payload)
        body=handler.wfile.getvalue()
        self.assertEqual(statuses,[200])
        self.assertGreater(len(body),500000)
        self.assertEqual(len(body),int(headers['Content-Length']))
        self.assertEqual(json.loads(body),payload)
        self.assertEqual(headers['Cache-Control'],'no-store')


if __name__=='__main__':
    unittest.main()
