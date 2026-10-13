"""Loopback-only local demo. Not an internet-facing service."""
from pathlib import Path
import os
import mimetypes

# Older Python/Windows MIME tables may not know WebP.
mimetypes.add_type("image/webp", ".webp")
from flask import Flask, jsonify, request, render_template
from werkzeug.exceptions import RequestEntityTooLarge
from core import Ticketing, BookingError

def create_app(system=None):
    app = Flask(__name__); app.config['MAX_CONTENT_LENGTH'] = 8192
    system = system or Ticketing(Path('artifacts')); app.config['SYSTEM'] = system
    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; object-src 'none'"
        response.headers['Cache-Control']='no-store'; return response
    @app.get('/')
    def booking_site(): return render_template('booking.html')
    @app.get('/favicon.ico')
    def favicon(): return ('',204)
    @app.get('/dashboard')
    def dashboard(): return render_template('index.html')
    @app.get('/api/events')
    def events():
        with system.request('events.list') as trace: result=system.list_events(trace)
        return jsonify(events=result,trace_id=trace['trace_id'])
    @app.get('/api/events/<event_id>/seats')
    def seats(event_id):
        try:
            with system.request('seats.list') as trace: result=system.list_seats(trace,event_id)
            return jsonify(seats=result,trace_id=trace['trace_id'])
        except BookingError as error: return jsonify(error=error.code,trace_id=trace['trace_id']),error.status
    @app.post('/api/bookings')
    def book():
        # Observe validation too: no rejected booking request disappears.
        try:
            with system.request('booking.submit') as trace:
                key=system.source_key('demo-user',request.remote_addr or 'local')
                system.record_attempt(trace,key)
                with system.span(trace,'request.validate'):
                    if request.headers.get('Origin') and request.headers['Origin'] != request.host_url.rstrip('/'):
                        system.reject(trace,key,'CROSS_ORIGIN_BLOCKED',403)
                    try:
                        data=request.get_json(silent=True)
                    except RequestEntityTooLarge:
                        system.reject(trace,key,'PAYLOAD_TOO_LARGE',413)
                    if not isinstance(data,dict) or not all(isinstance(data.get(k),str) and 0<len(data[k])<80 for k in ('event_id','seat')):
                        system.reject(trace,key,'INVALID_INPUT',400)
                booking=system.book(trace,data['event_id'],data['seat'],'demo-user',request.remote_addr or 'local',record_attempt=False)
            return jsonify(booking=booking,trace_id=trace['trace_id']),201
        except BookingError as error: return jsonify(error=error.code,trace_id=trace['trace_id']),error.status
    @app.get('/api/observability')
    def observability(): return jsonify(system.snapshot())
    @app.get('/api/traces/<trace_id>')
    def details(trace_id):
        snapshot=system.snapshot(); trace=next((t for t in snapshot['traces'] if t['trace_id']==trace_id),None)
        if trace is None: return jsonify(error='TRACE_NOT_FOUND'),404
        return jsonify(trace=trace,logs=[l for l in snapshot['logs'] if l['trace_id']==trace_id])
    return app

if __name__=='__main__': create_app().run(host='127.0.0.1',port=int(os.environ.get('PORT','5000')),debug=False)
