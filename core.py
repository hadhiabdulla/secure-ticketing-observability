"""Local demo ticket booking and observability. No production/payment integration."""
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import threading
import time
import uuid

class BookingError(Exception):
    def __init__(self, code, status=400): self.code, self.status = code, status

EVENTS = [
    {'id':'event-001','title':'Echo Valley Live','category':'Music','venue':'Grand Arena, Kochi','date':'Fri 21 Nov 2026, 7:00 PM','price':1499,'partner_id':'partner-demo'},
    {'id':'event-002','title':'National Tech Summit','category':'Tech','venue':'Convention Centre, Bengaluru','date':'Sat 06 Dec 2026, 9:30 AM','price':999,'partner_id':'partner-demo'},
    {'id':'event-003','title':'Stand-up Night: Full House','category':'Comedy','venue':'City Lights Theatre, Kozhikode','date':'Sun 16 Nov 2026, 6:30 PM','price':499,'partner_id':'partner-demo'},
    {'id':'event-004','title':'Champions T20 Final','category':'Sports','venue':'Greenfield Stadium, Thiruvananthapuram','date':'Wed 26 Nov 2026, 7:30 PM','price':1999,'partner_id':'partner-demo'},
    {'id':'event-005','title':'Classical Fusion Evening','category':'Music','venue':'Riverside Auditorium, Thrissur','date':'Sat 29 Nov 2026, 6:00 PM','price':799,'partner_id':'partner-demo'},
    {'id':'event-006','title':'Indie Film Premiere','category':'Film','venue':'Marina Drive-in, Mangaluru','date':'Fri 05 Dec 2026, 8:00 PM','price':349,'partner_id':'partner-demo'},
]
SEAT_ROWS = 'ABCDE'
SEATS_PER_ROW = 10

class Ticketing:
    def __init__(self, directory=None, clock=time.monotonic, events=None):
        self.lock = threading.RLock(); self.clock = clock
        self.key = secrets.token_bytes(32); self.directory = Path(directory) if directory else None
        if self.directory: self.directory.mkdir(parents=True, exist_ok=True)
        self.events = list(events) if events is not None else [dict(event) for event in EVENTS]
        self.seats = {event['id']: {f'{row}{n}': None for row in SEAT_ROWS for n in range(1,SEATS_PER_ROW+1)} for event in self.events}
        self.logs, self.traces, self.alerts, self.bookings = [], [], [], []
        self.failures = defaultdict(deque); self.attempts = defaultdict(deque)
        self.last_alert = {}; self.last_burst = {}

    def _write(self, filename, record):
        if self.directory:
            with (self.directory / filename).open('a', encoding='utf-8') as file:
                file.write(json.dumps(record)+'\n')

    def source_key(self, user, ip):
        # Process-local pseudonym; raw source addresses never enter logs or alerts.
        return hmac.new(self.key, f'{user}|{ip}'.encode(), hashlib.sha256).hexdigest()[:24]

    @contextmanager
    def request(self, operation, partner='partner-demo'):
        trace = {'trace_id': secrets.token_hex(16), 'operation': operation, 'partner_id': partner,
                 'region': 'local', 'timestamp': datetime.now(timezone.utc).isoformat(), 'spans': [], 'status': 'ok'}
        try:
            with self.span(trace, operation): yield trace
        except Exception:
            trace['status'] = 'error'; raise
        finally:
            with self.lock:
                self.traces.append(trace); self._write('traces.jsonl', trace)

    @contextmanager
    def span(self, trace, name):
        parent = trace.get('_active'); span = {'span_id': secrets.token_hex(8), 'parent_span_id': parent,
             'name': name, 'status': 'ok'}
        trace['_active'] = span['span_id']; start = time.perf_counter()
        try: yield span
        except BookingError as error: span['status'] = 'error'; span['error_code'] = error.code; raise
        except Exception: span['status'] = 'error'; span['error_code'] = 'INTERNAL_ERROR'; raise
        finally:
            span['duration_ms'] = round((time.perf_counter()-start)*1000, 3)
            trace['spans'].append(span)
            if parent: trace['_active'] = parent
            else: trace.pop('_active', None)

    def log(self, trace, level, message, **fields):
        allowed = {'event_id','seat','booking_id','error_code','source_key','duration_ms'}
        record = {'timestamp': datetime.now(timezone.utc).isoformat(), 'level':level, 'service':'booking-demo',
                  'region':'local', 'partner_id':trace['partner_id'], 'trace_id':trace['trace_id'],
                  'span_id':trace['_active'], 'message':message,
                  **{k:v for k,v in fields.items() if k in allowed}}
        with self.lock: self.logs.append(record); self._write('logs.jsonl', record)

    def list_events(self, trace):
        self.log(trace, 'INFO','Events listed'); return list(self.events)

    def list_seats(self, trace, event_id):
        with self.lock, self.span(trace, 'inventory.lookup'):
            if event_id not in self.seats:
                self.log(trace,'WARN','Event not found',error_code='EVENT_NOT_FOUND'); raise BookingError('EVENT_NOT_FOUND',404)
            self.log(trace,'INFO','Seat map loaded',event_id=event_id)
            return [{'seat':seat,'available':booking is None} for seat,booking in self.seats[event_id].items()]

    def book(self, trace, event_id, seat, user='demo-user', ip='local'):
        key = self.source_key(user, ip)
        with self.lock:
            self._burst(trace, key)
            try:
                with self.span(trace, 'inventory.reserve'):
                    if event_id not in self.seats: raise BookingError('EVENT_NOT_FOUND',404)
                    if seat not in self.seats[event_id]: raise BookingError('SEAT_NOT_FOUND',404)
                    if self.seats[event_id][seat]: raise BookingError('SEAT_UNAVAILABLE',409)
                    # Single lock makes reservation atomic for concurrent requests.
                    price = next(event['price'] for event in self.events if event['id']==event_id)
                    booking = {'booking_id':str(uuid.uuid4()),'event_id':event_id,'seat':seat,'price':price,'partner_id':trace['partner_id']}
                    self.seats[event_id][seat] = booking['booking_id']
                    self.log(trace,'INFO','Seat reserved',event_id=event_id,seat=seat)
                with self.span(trace, 'booking.persist'):
                    self.bookings.append(booking); self.log(trace,'INFO','Booking confirmed',**{k:v for k,v in booking.items() if k not in ('partner_id','price')})
                return {k:v for k,v in booking.items() if k!='partner_id'}
            except BookingError as error:
                self.log(trace,'WARN','Booking failed',error_code=error.code,source_key=key)
                self._detect(trace,key)
                raise

    def _burst(self, trace, key):
        now = self.clock(); window = self.attempts[key]
        while window and now-window[0] > 10: window.popleft()
        window.append(now)
        if len(window) >= 8 and now-self.last_burst.get(key,float('-inf')) >= 60:
            alert = {'alert_id':str(uuid.uuid4()), 'severity':'MEDIUM','rule':'request_burst',
                     'source_key':key,'failure_count':0,'window_seconds':10,
                     'trace_id':trace['trace_id'],'timestamp':datetime.now(timezone.utc).isoformat(),
                     'message':'Eight or more booking attempts in 10s from one source. Bot-like burst; investigate before blocking.'}
            self.alerts.append(alert); self._write('alerts.jsonl',alert); self.last_burst[key]=now

    def _detect(self, trace, key):
        now = self.clock(); window = self.failures[key]
        while window and now-window[0] > 60: window.popleft()
        window.append(now)
        if len(window) >= 3 and now-self.last_alert.get(key,float('-inf')) >= 60:
            alert = {'alert_id':str(uuid.uuid4()), 'severity':'HIGH','rule':'repeated_booking_failures',
                     'source_key':key,'failure_count':len(window),'window_seconds':60,
                     'trace_id':trace['trace_id'],'timestamp':datetime.now(timezone.utc).isoformat(),
                     'message':'Three or more booking failures in 60s. Investigate; this is not proof of an attack.'}
            self.alerts.append(alert); self._write('alerts.jsonl',alert); self.last_alert[key]=now

    def snapshot(self):
        with self.lock:
            traces = json.loads(json.dumps(self.traces))
            durations = sorted(sum(s['duration_ms'] for s in t['spans'] if s['parent_span_id'] is None) for t in traces)
            p95 = durations[max(0,__import__('math').ceil(.95*len(durations))-1)] if durations else 0
            return {'requests':len(traces),'errors':sum(t['status']=='error' for t in traces),
                    'bookings':len(self.bookings),'p95_ms':p95,'alerts':list(self.alerts),'traces':traces,'logs':list(self.logs)}
