(function(){
  var root=document.documentElement;
  var saved=null;
  try{saved=localStorage.getItem('ticmint-theme');}catch(e){}
  root.dataset.theme=saved||(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
  function paint(btn){var dark=root.dataset.theme==='dark';btn.textContent=dark?'Light mode':'Dark mode';btn.setAttribute('aria-pressed',String(dark));}
  window.addEventListener('DOMContentLoaded',function(){
    var btn=document.getElementById('theme-toggle');
    if(!btn)return;
    paint(btn);
    btn.onclick=function(){
      root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';
      try{localStorage.setItem('ticmint-theme',root.dataset.theme);}catch(e){}
      paint(btn);
    };
  });
})();
