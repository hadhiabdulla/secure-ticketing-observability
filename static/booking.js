const $=id=>document.getElementById(id);
let EVENTS=[],current=null,selected=new Set(),category='All';
const CATS=['All','Music','Tech','Comedy','Sports','Film'];
const EVENT_IMAGES={
  'event-001':{file:'echo-valley.webp',alt:'Purple-lit concert stage and crowd'},
  'event-002':{file:'tech-summit.webp',alt:'Audience at a blue-lit technology conference'},
  'event-003':{file:'comedy-night.webp',alt:'Microphone on a warmly lit comedy stage'},
  'event-004':{file:'cricket-final.webp',alt:'Cricket players in a floodlit stadium'},
  'event-005':{file:'classical-fusion.webp',alt:'Sitar and violin performers on a red-lit stage'},
  'event-006':{file:'film-premiere.webp',alt:'Outdoor cinema screen and parked cars at night'}
};
function eventImage(event,cls){
  const info=EVENT_IMAGES[event.id];
  if(!info)return null;
  const img=node('img',undefined,cls);
  img.src='/static/events/'+info.file;img.alt=info.alt;
  img.width=536;img.height=357;img.loading='lazy';img.decoding='async';
  img.title='Illustrative generated image, not a photograph of the listed event';
  img.addEventListener('error',()=>img.hidden=true,{once:true});
  return img;
}
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
async function api(path,options){const r=await fetch(path,options);let body={};try{body=await r.json();}catch(e){}return {ok:r.ok,status:r.status,...body};}
function money(p){return '₹'+Number(p).toLocaleString('en-IN');}
function renderChips(){$('chips').replaceChildren();for(const c of CATS){const b=node('button',c,'chip'+(c===category?' active':''));b.type='button';b.onclick=()=>{category=c;renderChips();renderGrid();};$('chips').append(b);}}
function renderGrid(){
  const q=$('search').value.trim().toLowerCase();
  const grid=$('event-grid');grid.replaceChildren();
  const list=EVENTS.filter(e=>(category==='All'||e.category===category)&&(!q||`${e.title} ${e.venue}`.toLowerCase().includes(q)));
  if(!list.length){grid.append(node('p','No events match that search.','muted'));return;}
  for(const e of list){
    const card=node('article','','card');
    const banner=node('div','','card-banner');
    const image=eventImage(e,'event-photo');if(image)banner.append(image);
    banner.append(node('span',e.category,'tag'));
    card.append(banner);
    const body=node('div','','card-body');
    body.append(node('h3',e.title),node('p',e.venue,'muted'),node('p',e.date,'muted'));
    const row=node('div','','card-row');
    row.append(node('strong',money(e.price)+' onwards'));
    const b=node('button','Book now');b.type='button';b.onclick=()=>openEvent(e.id);
    row.append(b);body.append(row);card.append(body);grid.append(card);
  }
}
async function openEvent(id){
  current=EVENTS.find(e=>e.id===id);selected=new Set();
  $('home-view').hidden=true;$('event-view').hidden=false;
  $('ev-title').textContent=current.title;
  const hero=eventImage(current,'event-detail-photo');
  $('ev-image').replaceChildren(...(hero?[hero]:[]));
  $('ev-meta').textContent=`${current.venue} · ${current.date} · ${money(current.price)} per seat`;
  $('ord-event').textContent=current.title;
  $('ord-result').textContent='';$('confirm').disabled=true;
  await renderSeats();renderOrder();
  window.scrollTo({top:0});
}
async function renderSeats(){
  const d=await api(`/api/events/${encodeURIComponent(current.id)}/seats`);
  const map=$('seat-map');map.replaceChildren();
  const rows={};
  for(const s of d.seats||[]){const row=s.seat[0];(rows[row]=rows[row]||[]).push(s);}
  for(const row of Object.keys(rows).sort()){
    const line=node('div','','seat-row');
    line.append(node('span',row,'row-label'));
    for(const s of rows[row]){
      const b=node('button',s.seat.slice(1),'seat');
      b.type='button';b.title=s.seat;b.disabled=!s.available;
      if(!s.available)b.classList.add('sold');
      b.onclick=()=>{if(selected.has(s.seat)){selected.delete(s.seat);b.classList.remove('chosen');}else{selected.add(s.seat);b.classList.add('chosen');}renderOrder();};
      line.append(b);
    }
    map.append(line);
  }
}
function renderOrder(){
  const box=$('ord-seats');box.replaceChildren();
  const seats=[...selected].sort();
  if(!seats.length){box.append(node('p','No seats selected yet.','muted'));}
  else{const p=node('p',seats.join(', '));box.append(p);}
  $('ord-total').textContent=money(seats.length*(current?current.price:0));
  $('confirm').disabled=!seats.length;
}
$('confirm').onclick=async()=>{
  if(!selected.size)return;
  $('confirm').disabled=true;$('ord-result').className='';
  const seats=[...selected].sort();const done=[],failed=[];
  for(const seat of seats){
    const d=await api('/api/bookings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_id:current.id,seat})});
    if(d.ok)done.push(`${seat} · ${d.booking.booking_id.slice(0,8)}`);else failed.push(`${seat} · ${d.error}`);
  }
  selected=new Set();
  await renderSeats();renderOrder();
  const out=$('ord-result');
  out.replaceChildren();
  if(done.length){out.append(node('p',`Confirmed ${done.length} seat(s). References: ${done.join(', ')}`,'ok-text'));}
  if(failed.length){out.append(node('p',`Could not book: ${failed.join(', ')}`,'error-text'));}
  if(done.length){const link=node('a','See this activity in the observability dashboard');link.href='/dashboard';out.append(link);}
};
$('back').onclick=()=>{$('event-view').hidden=true;$('home-view').hidden=false;};
$('search').oninput=renderGrid;
(async()=>{
  const d=await api('/api/events');
  EVENTS=d.events||[];
  renderChips();renderGrid();
})().catch(()=>{$('event-grid').replaceChildren(node('p','Could not reach the local server. Restart app.py.','muted'));});
