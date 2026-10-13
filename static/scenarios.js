// Customer-side traffic only. Every displayed response comes from the local API.
(()=>{
const el=id=>document.getElementById(id),make=(tag,text,cls)=>{const e=document.createElement(tag);e.textContent=text;if(cls)e.className=cls;return e;};
let running=false,rows=[],completed=0;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function stage(state){el('request-flow').dataset.state=state;el('flow-status').textContent={sending:'Browser sends real HTTP requests',receiving:'Server responses received and correlated',done:'Finished. Dashboard can inspect the same trace IDs.'}[state]||'Ready to send local requests';}
async function send(label,path,options){
 const row=make('div',label+' - sending...', 'scenario-request pending');el('scenario-requests').append(row);stage('sending');
 const start=performance.now();let response,body={};
 try{response=await fetch(path,options);body=await response.json();}catch(error){row.className='scenario-request failed';row.textContent=label+' - network error. Check the local server.';throw error;}
 const ms=Math.round(performance.now()-start);await pause(Math.max(0,450-ms));completed++;row.className='scenario-request '+(response.ok?'passed':'failed');row.replaceChildren(make('strong',`${label}: HTTP ${response.status} · ${body.error||'OK'} · ${ms} ms`));
 if(body.trace_id){const link=make('a','Inspect real trace '+body.trace_id);link.href='/dashboard?trace='+encodeURIComponent(body.trace_id);link.target='_blank';link.rel='noopener';row.append(link);}
 rows.push({label,status:response.status,trace_id:body.trace_id,error:body.error});el('flow-count').textContent=completed+' responses received';stage('receiving');return {ok:response.ok,status:response.status,...body};
}
const post=(label,event,seat)=>send(label,'/api/bookings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_id:event,seat})});
async function freeSeats(){const d=await send('Read available seats','/api/events/event-001/seats');return(d.seats||[]).filter(s=>s.available);}
const scenarios={
 browse:async()=>{await send('Discover six events','/api/events');await pause(350);await send('Compare concert seats','/api/events/event-001/seats');await pause(350);await send('Compare conference seats','/api/events/event-002/seats');return 'Customer browsing finished. Three read requests, no seats booked.';},
 checkout:async()=>{const seats=await freeSeats();if(!seats.length)return 'No free seats. Restart the server to reset inventory.';await pause(350);const r=await post('Confirm seat '+seats[0].seat,'event-001',seats[0].seat);return r.ok?'One real booking confirmed. The seat is now sold.':'Booking rejected: '+r.error;},
 rush:async()=>{const seats=await freeSeats();if(!seats.length)return 'No free seats. Restart the server to reset inventory.';await pause(350);const results=await Promise.all(Array.from({length:8},(_,i)=>post('Buyer '+(i+1)+' races for '+seats[0].seat,'event-001',seats[0].seat)));return `${results.filter(r=>r.ok).length} winner, ${results.filter(r=>!r.ok).length} conflicts. A legitimate rush can raise security signals too.`;},
 failures:async()=>{for(let i=0;i<3;i++){await post('Invalid event attempt '+(i+1),'invalid-demo-event','A1');await pause(250);}return 'Three EVENT_NOT_FOUND failures. The repeated-failure HIGH rule applies; deduplicated if already raised this minute.';},
 burst:async()=>{await Promise.all(Array.from({length:12},(_,i)=>post('Burst request '+(i+1),'event-001',`Z${i+1}`)));return 'Twelve real rapid requests. MEDIUM request_burst rule applies; invalid seats also contribute to repeated failures.';},
 malformed:async()=>{const payloads=[['Broken JSON','{"event_id":'],['Wrong field type',JSON.stringify({event_id:'event-001',seat:3})],['Missing seat',JSON.stringify({event_id:'event-001'})],['Overlong field',JSON.stringify({event_id:'x'.repeat(200),seat:'A1'})],['Not an object','"not-an-object"'],['Oversized body',JSON.stringify({event_id:'x'.repeat(9000),seat:'A1'})]];for(const [label,body] of payloads){await send(label,'/api/bookings',{method:'POST',headers:{'Content-Type':'application/json'},body});await pause(250);}return 'Six rejected requests, each with a WARN log and error trace. INVALID_INPUT (400) or PAYLOAD_TOO_LARGE (413). Three malformed inputs in 60s trigger MEDIUM malformed_input, plus the repeated-failure rule.';},
 duplicate:async()=>{const seats=await freeSeats();if(!seats.length)return 'No free seats. Restart the server to reset inventory.';const seat=seats[0].seat;await post('First checkout for '+seat,'event-001',seat);await pause(450);const r=await post('Repeat checkout for '+seat,'event-001',seat);return `Second checkout returned ${r.status} ${r.error||'OK'}. Inventory prevents double booking.`;},
 multiseat:async()=>{const seats=(await freeSeats()).slice(0,4);if(!seats.length)return 'No free seats. Restart the server to reset inventory.';const results=await Promise.all(seats.map(s=>post('Independent checkout '+s.seat,'event-001',s.seat)));return `${results.filter(r=>r.ok).length}/${seats.length} distinct seats confirmed. Real concurrent traffic without a same-seat race.`;},
 invalidseat:async()=>{for(const seat of ['Z1','Z2','Z3']){await post('Probe invalid seat '+seat,'event-001',seat);await pause(250);}return 'Three SEAT_NOT_FOUND responses. The repeated-failure rule applies, with inventory.reserve error spans.';}
};
document.querySelectorAll('[data-scenario]').forEach(button=>button.onclick=async()=>{
 if(running)return;running=true;rows=[];completed=0;document.querySelectorAll('[data-scenario]').forEach(b=>b.disabled=true);
 el('scenario-requests').replaceChildren();el('flow-count').textContent='0 responses received';el('walkthrough-title').textContent=button.closest('.scenario').querySelector('h3').textContent;el('scenario-result').textContent='Running real local traffic...';el('scenario-stage').scrollIntoView({behavior:'smooth',block:'center'});stage('sending');
 try{const before=await fetch('/api/observability').then(r=>r.json());const result=await scenarios[button.dataset.scenario]();const after=await fetch('/api/observability').then(r=>r.json());await pause(350);stage('done');el('scenario-result').textContent=result+`\nObserved change: +${after.requests-before.requests} requests, +${after.errors-before.errors} errors, +${after.bookings-before.bookings} bookings, +${after.alerts.length-before.alerts.length} new alerts.`;el('scenario-alerts').replaceChildren();for(const alert of after.alerts.slice(before.alerts.length)){el('scenario-alerts').append(make('p',`${alert.severity} · ${alert.rule}: ${alert.message}`,'alert'));}}
 catch(error){el('scenario-result').textContent='Run stopped: could not reach the local server. Completed responses remain below.';stage('done');}
 finally{running=false;document.querySelectorAll('[data-scenario]').forEach(b=>b.disabled=false);}
});
})();
