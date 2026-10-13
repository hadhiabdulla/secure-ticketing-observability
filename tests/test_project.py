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
    def test_event_discovery(self):self.assertEqual(len(self.client.get('/api/events').json['events']),6)
    def test_event_metadata(self):
        for event in self.client.get('/api/events').json['events']:
            self.assertIsInstance(event['price'],int);self.assertGreater(event['price'],0)
            self.assertTrue(event['category']);self.assertTrue(event['venue']);self.assertTrue(event['date'])
    def test_seat_selection(self):self.assertEqual(len(self.client.get('/api/events/event-001/seats').json['seats']),50)
    def test_booking_site_page(self):
        body=self.client.get('/').get_data(as_text=True)
        self.assertIn('ticmint',body);self.assertNotIn('prototype',body.lower())
    def test_dashboard_page(self):
        response=self.client.get('/dashboard');body=response.get_data(as_text=True)
        self.assertEqual(response.status_code,200);self.assertIn('Observability',body)
    def test_brand_logo_on_both_pages(self):
        for route in ('/', '/dashboard'):
            body=self.client.get(route).get_data(as_text=True)
            self.assertIn('src="/static/ticmint-logo.png"',body)
            self.assertNotIn('<small>observability</small>',body.lower())
        self.assertEqual(self.client.get('/static/ticmint-logo.png').status_code,200)
    def test_local_sidebar_icons(self):
        body=self.client.get('/dashboard').get_data(as_text=True)
        for icon in ('home','logs','traces','metrics','security','services'):
            self.assertIn('icon-'+icon,body)
            self.assertEqual(self.client.get('/static/icons/'+icon+'.svg').status_code,200)
    def test_local_event_photos(self):
        files=('echo-valley','tech-summit','comedy-night','cricket-final','classical-fusion','film-premiere')
        total=0
        for name in files:
            response=self.client.get('/static/events/'+name+'.webp')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.mimetype,'image/webp')
            self.assertTrue(response.data.startswith(b'RIFF'))
            total+=len(response.data);response.close()
        self.assertLess(total,180_000)
    def test_event_photo_wiring(self):
        script=Path('static/booking.js').read_text()
        for event in self.system.events:
            self.assertIn(event['id'],script)
        self.assertIn("img.loading='lazy'",script)
        self.assertIn('id="ev-image"',self.client.get('/').get_data(as_text=True))
    def test_successful_booking(self):
        response=self.book();self.assertEqual(response.status_code,201)
        self.assertEqual(response.json['booking']['price'],1499)
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
    def test_burst_alert(self):
        for i in range(8):
            try:
                with self.system.request('booking.submit') as trace:self.system.book(trace,'event-001',f'Z{i+1}')
            except BookingError:pass
        rules={(a['rule'],a['severity']) for a in self.system.alerts}
        self.assertIn(('request_burst','MEDIUM'),rules)
    def test_alert_deduplication(self):
        for _ in range(7):self.book('bad')
        self.assertEqual(len([a for a in self.system.alerts if a['rule']=='repeated_booking_failures']),1)
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

class ValidationAndScenarioTests(unittest.TestCase):
    def setUp(self):
        self.system=Ticketing(); self.client=create_app(self.system).test_client()
    def test_client_owns_all_nine_scenarios(self):
        body=self.client.get('/').get_data(as_text=True)
        for key in ('browse','checkout','rush','failures','burst','malformed','duplicate','multiseat','invalidseat'):
            self.assertIn('data-scenario="'+key+'"',body)
        self.assertIn('id="request-flow"',body)
        dashboard=self.client.get('/dashboard').get_data(as_text=True)
        self.assertNotIn('data-scenario',dashboard)
        self.assertNotIn("method:'POST'",Path('static/app.js').read_text())
    def test_invalid_payloads_observed_and_private(self):
        payloads=[{'seat':3},{'event_id':'event-001'},'not-an-object',{'event_id':'secret@private.example'*10,'seat':'A1'},None,[]]
        for payload in payloads:
            r=self.client.post('/api/bookings',data=json.dumps(payload),content_type='application/json')
            self.assertEqual(r.status_code,400);self.assertEqual(r.json['error'],'INVALID_INPUT')
            d=self.client.get('/api/traces/'+r.json['trace_id']).json
            self.assertEqual(d['trace']['status'],'error')
            validation=next(s for s in d['trace']['spans'] if s['name']=='request.validate')
            self.assertEqual(validation['error_code'],'INVALID_INPUT')
            self.assertTrue(any(l['span_id']==validation['span_id'] and l['error_code']=='INVALID_INPUT' for l in d['logs']))
        self.assertEqual(self.system.snapshot()['errors'],len(payloads));self.assertEqual(self.system.bookings,[])
        self.assertNotIn('secret@private.example',json.dumps(self.system.snapshot()))
        self.assertEqual(len([a for a in self.system.alerts if a['rule']=='malformed_input']),1)
    def test_broken_json_observed(self):
        r=self.client.post('/api/bookings',data='{"event_id":',content_type='application/json')
        self.assertEqual(r.status_code,400);self.assertIn('trace_id',r.json)
    def test_oversized_observed(self):
        r=self.client.post('/api/bookings',data=json.dumps({'event_id':'x'*9000,'seat':'A1'}),content_type='application/json')
        self.assertEqual(r.status_code,413);self.assertEqual(r.json['error'],'PAYLOAD_TOO_LARGE')
        self.assertEqual(self.system.traces[0]['status'],'error');self.assertEqual(self.system.logs[0]['error_code'],'PAYLOAD_TOO_LARGE')
    def test_cross_origin_observed(self):
        r=self.client.post('/api/bookings',json={'event_id':'event-001','seat':'A1'},headers={'Origin':'https://evil.test'})
        self.assertEqual(r.status_code,403);self.assertEqual(self.system.traces[0]['status'],'error')
        self.assertEqual(self.system.logs[0]['error_code'],'CROSS_ORIGIN_BLOCKED');self.assertEqual(self.system.bookings,[])
    def test_attempts_not_double_counted(self):
        for i in range(7):self.client.post('/api/bookings',json={'event_id':'event-001','seat':f'A{i+1}'})
        self.assertNotIn('request_burst',[a['rule'] for a in self.system.alerts])
        self.client.post('/api/bookings',json={'seat':3})
        self.assertIn('request_burst',[a['rule'] for a in self.system.alerts])
    def test_malformed_window_and_dedup(self):
        ticks=[0];system=Ticketing(clock=lambda:ticks[0]);client=create_app(system).test_client()
        for tick in (0,61,122):
            ticks[0]=tick;client.post('/api/bookings',json={'seat':3})
        self.assertEqual(system.alerts,[])
        for _ in range(5):client.post('/api/bookings',json={'seat':3})
        self.assertEqual(len([a for a in system.alerts if a['rule']=='malformed_input']),1)
    def test_validation_jsonl_persistence(self):
        with tempfile.TemporaryDirectory() as path:
            system=Ticketing(path);client=create_app(system).test_client()
            for _ in range(3):client.post('/api/bookings',json={'seat':3})
            for filename in ('logs.jsonl','traces.jsonl','alerts.jsonl'):
                rows=[json.loads(line) for line in (Path(path)/filename).read_text().splitlines()]
                self.assertTrue(rows);self.assertTrue(all('trace_id' in r for r in rows))

if __name__=='__main__':unittest.main()
