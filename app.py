"""Loopback-only local demo. Not an internet-facing service."""
from pathlib import Path
import os
import mimetypes

# Older Python/Windows MIME tables may not know WebP.
mimetypes.add_type("image/webp", ".webp")
from flask import Flask, jsonify, request, render_template
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
        if request.headers.get('Origin') and request.headers['Origin'] != request.host_url.rstrip('/'):
            return jsonify(error='CROSS_ORIGIN_BLOCKED'),403
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or not all(isinstance(data.get(k),str) and 0<len(data[k])<80 for k in ('event_id','seat')):
            return jsonify(error='INVALID_INPUT'),400
        # A fixed demo actor. No real identity, proxy headers or arbitrary IDs are trusted.
        try:
            with system.request('booking.submit') as trace:
                booking=system.book(trace,data['event_id'],data['seat'],'demo-user',request.remote_addr or 'local')
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
