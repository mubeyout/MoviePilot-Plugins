<script id="stills-inject" data-v="3">(function(){
/* v3 - slider style, no dup sections */
function matchMediaUrl(url){
  var u=typeof url==='string'?url:'';
  return (u.indexOf('/api/v1/media/')!==-1||u.indexOf('api/v1/media/')!==-1)&&u.indexOf(':')!==-1;
}
function makeSlider(title,items,isStill){
  if(!items||!items.length)return '';
  var h='<div class="bytemuse-section" style="margin-top:1.5rem">';
  h+='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.6rem;padding:0 .25rem">';
  h+='<span style="font-size:.95rem;font-weight:600">'+title+'</span>';
  h+='<span style="font-size:.7rem;opacity:.5">'+items.length+'</span>';
  h+='</div>';
  h+='<div style="position:relative">';
  h+='<div style="display:flex;gap:.5rem;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:.5rem;-webkit-overflow-scrolling:touch;scrollbar-width:thin">';
  for(var i=0;i<items.length;i++){
    if(isStill){
      var s=items[i];
      h+='<div class="bm-still" data-i="'+i+'" style="flex-shrink:0;width:200px;scroll-snap-align:start;border-radius:.5rem;overflow:hidden;cursor:pointer;position:relative">';
      h+='<img src="'+s+'" style="width:100%;aspect-ratio:3/2;object-fit:cover;display:block" loading="lazy" onerror="this.parentElement.remove()">';
      h+='</div>';
    } else {
      var it=items[i];
      var t=(it.title||'').length>24?(it.title||'').substring(0,24)+'...':(it.title||'');
      var p=it.poster_path||it.poster||'';
      var mid=it.media_id||it.id||'';
      var link='/media?mediaid=metatube_search:'+encodeURIComponent(mid)+'&type=\u7535\u5f71&title='+encodeURIComponent(it.title||'');
      h+='<a href="'+link+'" style="flex-shrink:0;width:110px;scroll-snap-align:start;text-decoration:none;color:inherit;display:block">';
      h+='<div style="border-radius:.5rem;overflow:hidden;background:rgba(var(--v-theme-surface-variant),.3)">';
      if(p){h+='<img src="'+p+'" style="width:100%;aspect-ratio:2/3;object-fit:cover;display:block" loading="lazy" onerror="this.style.display=\'none\'">'}
      else{h+='<div style="width:100%;aspect-ratio:2/3;background:rgba(var(--v-theme-on-surface),.05)"></div>'}
      h+='<div style="padding:.35rem .4rem;font-size:.65rem;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+t+'</div>';
      h+='</div></a>';
    }
  }
  h+='</div></div></div>';
  return h;
}
function doInject(data){
  var ov=document.querySelector('.media-overview');
  if(!ov||!data||data.source!=='bytemuse')return false;
  if(ov.querySelector('.bytemuse-section'))return true;
  // Remove any old injected content
  var old=document.querySelectorAll('.bytemuse-injected');
  for(var i=0;i<old.length;i++)old[i].remove();
  window._bmStills=data.stills||[];
  // Hide native empty "类似" slider
  hideEmptyNative('类似');
  // Stills
  if(window._bmStills.length){
    ov.insertAdjacentHTML('beforeend',makeSlider('\u5267\u7167',window._bmStills,true));
    ov.querySelectorAll('.bm-still').forEach(function(el){
      el.addEventListener('click',function(){lbOpen(parseInt(this.dataset.i))});
    });
  }
  // Similar from ByteMuse discover
  loadSimilar(ov,data);
  return true;
}
function hideEmptyNative(title){
  var sliders=document.querySelectorAll('.slider-container');
  for(var i=0;i<sliders.length;i++){
    var h3=sliders[i].querySelector('.title-text');
    if(h3&&h3.textContent.trim()===title){
      var cards=sliders[i].querySelectorAll('.media-card');
      var empty=true;
      for(var j=0;j<cards.length;j++){
        var img=cards[j].querySelector('img');
        if(img&&img.src&&!img.src.endsWith('undefined')&&img.className.indexOf('v-img--booting')===-1){empty=false;break}
      }
      if(empty)sliders[i].style.display='none';
    }
  }
}
function loadSimilar(ov,data){
  var curId=data.media_id||data.id||'';
  var recIds=new Set((data.recommendations||[]).map(function(x){return(x.id||x.media_id||'')}));
  fetch('/api/v1/plugin/ByteMuseDiscover/bytemuse_discover?discover_type=new_releases&page=1&count=20')
    .then(function(r){return r.json()})
    .then(function(list){
      if(!Array.isArray(list))return;
      var sim=[];
      for(var i=0;i<list.length&&sim.length<15;i++){
        var it=list[i];
        var mid=(it.media_id||it.imdb_id||'').replace('metatube_search:','').replace('bytemuse:','');
        if(mid&&mid!==curId&&!recIds.has(mid)){
          sim.push({id:mid,media_id:mid,title:it.title||mid,poster_path:it.poster_path||''});
        }
      }
      if(sim.length){
        // Find a good insertion point: after the last slider-container or before page end
        var page=document.querySelector('.media-page');
        if(page){
          var lastSlider=page.querySelector('.slider-container');
          var ref=lastSlider?lastSlider.parentNode:page;
          ref.insertAdjacentHTML('beforeend',makeSlider('\u7c7b\u4f3c\u4f5c\u54c1',sim,false));
        }
      }
    }).catch(function(){});
}
/* Lightbox */
var _lb=null;
function lbOpen(idx){
  if(!window._bmStills.length)return;
  window._lbIdx=idx;
  if(_lb)_lb.remove();
  _lb=document.createElement('div');
  _lb.style.cssText='position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;user-select:none';
  _lb.addEventListener('click',function(e){if(e.target===_lb){lbClose()}});
  // top bar: counter + close
  var bar=document.createElement('div');
  bar.style.cssText='position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:.75rem 1rem';
  var ct=document.createElement('span');
  ct.style.cssText='color:#fff;font-size:.8rem;opacity:.7';
  ct.textContent=(idx+1)+' / '+window._bmStills.length;
  bar.appendChild(ct);
  var cls=document.createElement('button');
  cls.textContent='\u2715';
  cls.style.cssText='background:none;border:none;color:#fff;font-size:1.2rem;cursor:pointer;opacity:.6;padding:.25rem .5rem';
  cls.addEventListener('click',function(e){e.stopPropagation();lbClose()});
  bar.appendChild(cls);
  _lb.appendChild(bar);
  // main image area with nav
  var area=document.createElement('div');
  area.style.cssText='display:flex;align-items:center;gap:1rem;max-width:95vw';
  var mkNav=function(dir){
    var b=document.createElement('button');
    b.textContent=dir<0?'\u25C0':'\u25B6';
    b.style.cssText='background:rgba(255,255,255,.1);border:none;color:#fff;width:40px;height:40px;border-radius:50%;font-size:1rem;cursor:pointer;flex-shrink:0;transition:background .15s;display:flex;align-items:center;justify-content:center';
    b.addEventListener('mouseenter',function(){this.style.background='rgba(255,255,255,.25)'});
    b.addEventListener('mouseleave',function(){this.style.background='rgba(255,255,255,.1)'});
    b.addEventListener('click',function(e){e.stopPropagation();lbNav(dir)});
    return b;
  };
  area.appendChild(mkNav(-1));
  var img=document.createElement('img');
  img.style.cssText='max-width:80vw;max-height:75vh;object-fit:contain;border-radius:.25rem;transition:opacity .12s';
  img.src=window._bmStills[idx];
  area.appendChild(img);
  area.appendChild(mkNav(1));
  _lb.appendChild(area);
  // thumbnail strip
  var strip=document.createElement('div');
  strip.style.cssText='display:flex;gap:4px;margin-top:.75rem;overflow-x:auto;max-width:88vw;padding:4px 0;scroll-snap-type:x mandatory;scrollbar-width:none';
  strip.className='bm-lb-strip';
  for(var i=0;i<window._bmStills.length;i++){
    (function(idx){
      var th=document.createElement('img');
      th.src=window._bmStills[idx];
      th.style.cssText='height:36px;border-radius:3px;object-fit:cover;cursor:pointer;opacity:'+(idx===i?'1':'.45')+';transition:all .15s;border:2px solid '+(idx===i?'#fff':'transparent')+';scroll-snap-align:center;flex-shrink:0';
      th.addEventListener('click',function(e){e.stopPropagation();lbGo(idx)});
      strip.appendChild(th);
    })(i);
  }
  _lb.appendChild(strip);
  document.body.appendChild(_lb);
  document.addEventListener('keydown',_lbKey);
  // scroll thumb into view
  setTimeout(function(){var ac=strip.querySelector('img[style*="opacity: 1"]');if(ac)ac.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})},50);
}
function lbNav(d){
  window._lbIdx=(window._lbIdx+d+window._bmStills.length)%window._bmStills.length;
  lbUpdate();
}
function lbGo(i){window._lbIdx=i;lbUpdate()}
function lbUpdate(){
  var idx=window._lbIdx;
  var img=_lb.querySelector('area img')||_lb.querySelector('img');
  var ct=_lb.querySelector('span');
  if(img){img.style.opacity='0';setTimeout(function(){img.src=window._bmStills[idx];img.style.opacity='1'},100)}
  if(ct)ct.textContent=(idx+1)+' / '+window._bmStills.length;
  var thumbs=_lb.querySelectorAll('.bm-lb-strip img');
  for(var i=0;i<thumbs.length;i++){
    thumbs[i].style.opacity=i===idx?'1':'.45';
    thumbs[i].style.border=i===idx?'2px solid #fff':'2px solid transparent';
  }
  setTimeout(function(){if(thumbs[idx])thumbs[idx].scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})},50);
}
function lbClose(){if(_lb){_lb.remove();_lb=null;document.removeEventListener('keydown',_lbKey)}}
function _lbKey(e){
  if(!_lb)return;
  if(e.key==='ArrowLeft')lbNav(-1);
  else if(e.key==='ArrowRight')lbNav(1);
  else if(e.key==='Escape')lbClose();
}
// Touch swipe
(function(){
  var sx=0,sy=0;
  document.addEventListener('touchstart',function(e){if(!_lb)return;sx=e.touches[0].clientX;sy=e.touches[0].clientY},{passive:true});
  document.addEventListener('touchend',function(e){
    if(!_lb)return;
    var dx=e.changedTouches[0].clientX-sx,dy=e.changedTouches[0].clientY-sy;
    if(Math.abs(dx)>Math.abs(dy)&&Math.abs(dx)>50)lbNav(dx<0?1:-1);
  },{passive:true});
})();
/* Interceptors */
function tryInject(data){
  var n=0;var t=setInterval(function(){if(doInject(data)||n>30){clearInterval(t)}n++},300);
}
var _xo=XMLHttpRequest.prototype.open;
var _xs=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(){this._bmU=arguments[1]||'';return _xo.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(){
  var s=this;
  if(this._bmU&&matchMediaUrl(this._bmU)){
    this.addEventListener('load',function(){try{var d=JSON.parse(s.responseText);if(d&&d.stills)tryInject(d)}catch(e){}});
  }
  return _xs.apply(this,arguments);
};
var _wf=window.fetch;
window.fetch=function(){
  var u=typeof arguments[0]==='string'?arguments[0]:(arguments[0]&&arguments[0].url)||'';
  var p=_wf.apply(this,arguments);
  if(matchMediaUrl(u)){p.then(function(r){return r.clone().json()}).then(function(d){if(d&&d.stills)tryInject(d)}).catch(function(){})}
  return p;
};
})();
</script>
