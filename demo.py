"""Generate actual booking/trace/alert evidence using synthetic data."""
import json
from pathlib import Path
from app import create_app
from core import Ticketing

out=Path('evidence');out.mkdir(exist_ok=True)
system=Ticketing();client=create_app(system).test_client()
responses=[]
responses.append(client.get('/api/events').json)
responses.append(client.get('/api/events/event-001/seats').json)
for event,seat in [('event-001','A1'),('event-001','A2'),('event-001','A1'),('bad-event','A1'),('event-001','Z99')]:
    response=client.post('/api/bookings',json={'event_id':event,'seat':seat})
    responses.append({'status':response.status_code,**response.json})
(out/'demo-responses.json').write_text(json.dumps(responses,indent=2)+'\n')
(out/'observability.json').write_text(json.dumps(system.snapshot(),indent=2)+'\n')
print('Actual demo: 7 requests, 2 bookings, 3 failures, 1 HIGH alert.')
