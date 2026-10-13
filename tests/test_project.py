import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from core import Ticketing, BookingError
from app import create_app

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.system=Ticketing();self.client=create_app(self.system).test_client()
    def book(self,event='event-001',seat='A1'):
        return self.client.post('/api/bookings',json={'event_id':event,'seat':seat})
    def test_event_discovery(self):self.assertEqual(len(self.client.get('/api/events').json['events']),2)
    def test_seat_selection(self):self.assertEqual(len(self.client.get('/api/events/event-001/seats').json['seats']),12)
    def test_successful_booking(self):self.assertEqual(self.book().status_code,201)
    def test_booked_seat_unavailable(self):
        self.book();self.assertEqual(self.book().json['error'],'SEAT_UNAVAILABLE')
    def test_invalid_event(self):self.assertEqual(self.book('bad').status_code,404)
    def test_invalid_seat(self):self.assertEqual(self.book(seat='Z99').json['error'],'SEAT_NOT_FOUND')
    def test_invalid_input(self):self.assertEqual(self.client.post('/api/bookings',json={'seat':3}).status_code,400)
    def test_trace_log_correlation(self):
        response=self.book();trace=self.client.get('/api/traces/'+response.json['trace_id']).json
        spans={s['span_id'] for s in trace['trace']['spans']}
        self.assertTrue(trace['logs']);self.assertTrue(all(l['span_id'] in spans for l in trace['logs']))
        self.assertEqual({l['trace_id'] for l in trace['logs']},{response.json['trace_id']})
    def test_nested_spans(self):
        self.book();spans=self.system.traces[0]['spans'];root=next(s for s in spans if s['parent_span_id'] is None)
        self.assertTrue(all(s['parent_span_id']==root['span_id'] for s in spans if s!=root))
    def test_high_alert(self):
        for _ in range(3):self.book('bad')
        self.assertEqual(self.system.alerts[0]['severity'],'HIGH')
        self.assertIn(self.system.alerts[0]['trace_id'],[t['trace_id'] for t in self.system.traces])
    def test_alert_deduplication(self):
        for _ in range(7):self.book('bad')
        self.assertEqual(len(self.system.alerts),1)
    def test_failure_window_expires(self):
        time=[0];system=Ticketing(clock=lambda:time[0])
        for tick in [0,61,122]:
            time[0]=tick
            try:
                with system.request('booking') as trace:system.book(trace,'bad','A1')
            except BookingError:pass
        self.assertEqual(system.alerts,[])
    def test_distinct_sources_not_combined(self):
        for user in ['a','b','c']:
            try:
                with self.system.request('booking') as trace:self.system.book(trace,'bad','A1',user)
            except BookingError:pass
        self.assertEqual(self.system.alerts,[])
    def test_data_minimization(self):
        with self.system.request('test') as trace:
            self.system.log(trace,'INFO','Safe fixed message',email='private@example.com',phone='123',card='secret',address='hidden')
        text=json.dumps(self.system.logs)
        for forbidden in ['private@example.com','secret','hidden','email','phone','card','address']:self.assertNotIn(forbidden,text)
        for _ in range(3):self.book('bad')
        self.assertNotIn('127.0.0.1',json.dumps(self.system.alerts+self.system.logs))
    def test_concurrent_seat_reservation(self):
        def attempt(_):
            try:
                with self.system.request('booking') as trace:self.system.book(trace,'event-001','A1')
                return 'ok'
            except BookingError:return 'conflict'
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(8)))
        self.assertEqual(results.count('ok'),1);self.assertEqual(len(self.system.bookings),1)
    def test_trace_missing(self):self.assertEqual(self.client.get('/api/traces/no').status_code,404)
    def test_json_persistence(self):
        with tempfile.TemporaryDirectory() as path:
            system=Ticketing(path)
            with system.request('booking') as trace:system.book(trace,'event-001','A1')
            for filename in ['logs.jsonl','traces.jsonl']:
                self.assertTrue([json.loads(line) for line in (Path(path)/filename).read_text().splitlines()])
    def test_cross_origin_blocked(self):
        self.assertEqual(self.client.post('/api/bookings',json={'event_id':'event-001','seat':'A1'},headers={'Origin':'https://evil.test'}).status_code,403)
    def test_security_headers(self):
        r=self.client.get('/');self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])
    def test_health_summary(self):
        self.book();self.book();d=self.system.snapshot();self.assertEqual(d['requests'],2);self.assertEqual(d['errors'],1)

if __name__=='__main__':unittest.main()
