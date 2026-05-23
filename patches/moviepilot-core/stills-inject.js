(function(){
console.log('[BM] v16 LOADED');

var _done={};
var _pending=null;

function getMediaId(){
  var m=location.hash.match(/mediaid=([^&]+)/);
  if(!m)return null;
  var raw=decodeURIComponent(m[1]);
  return raw.replace(/^[^:]+:/,'');
}

function checkAndInject(){
  var mid=getMediaId();
  if(!mid)return;
  if(_done[mid])return;
  var ov=document.querySelector('.media-overview');
  if(ov&&ov.dataset.bmStills==='1'){_done[mid]=1;return}
  if(!_pending||_pending!==mid){_pending=mid;fetchDetail(mid)}
}

function fetchDetail(mid){
  fetch('/api/v1/plugin/ByteMuseDiscover/bytemuse_detail/'+encodeURIComponent(mid),{credentials:'include'})
    .then(function(r){return r.ok?r.json():null})
    .then(function(data){
      _pending=null;
      if(!data)return;
      if(!data.stills||!data.stills.length)return;
      _done[mid]=1;
      doInject(data);
    })
    .catch(function(){_pending=null});
}

function doInject(data){
  var ov=document.querySelector('.media-overview');
  if(!ov)return;
  if(ov.dataset.bmStills==='1')return;

  var stills=data.stills||[];
  var similar=data.similar||[];
  var monthly=data.monthly||[];
  var description=data.description||'';
  var actors=data.actors||[];

  // 1. Fill overview-left: description + actor credits
  var overviewLeft=ov.querySelector('.media-overview-left');
  if(overviewLeft){
    // Fill description
    var pEl=overviewLeft.querySelector('p');
    if(pEl&&description){
      pEl.textContent=description;
      pEl.style.whiteSpace='pre-wrap';
    }
    // Fill actor credits
    var crewUl=overviewLeft.querySelector('.media-crew');
    if(crewUl&&actors.length){
      var crewHtml='';
      for(var a=0;a<actors.length;a++){
        var actor=actors[a];
        if(!actor.name)continue;
        crewHtml+='<li><span class="media-crew-name">'+actor.name+'</span></li>';
      }
      crewUl.innerHTML=crewHtml;
    }
  }

  // 2. 剧照 → insert AFTER media-overview (not inside)
  if(stills.length){
    ov.insertAdjacentHTML('afterend',makeSlider('\u5267\u7167',stills,true));
    ov.parentElement.querySelectorAll('.bm-still').forEach(function(el){
      el.addEventListener('click',function(){lbOpen(parseInt(el.dataset.i),stills)});
    });
    ov.dataset.bmStills='1';
    console.log('[BM] stills:',stills.length);
  }

  // 3. 推荐 → fill TMDB native "推荐" slider
  if(similar.length){
    fillNativeSlider('\u63a8\u8350',similar);
    console.log('[BM] recommend:',similar.length);
  }

  // 4. 类似 → fill TMDB native "类似" slider
  if(monthly.length){
    fillNativeSlider('\u7c7b\u4f3c',monthly);
    console.log('[BM] similar:',monthly.length);
  }
}

function fillNativeSlider(titleText,items){
  var attempts=0;
  function tryFill(){
    attempts++;
    var filled=false;
    document.querySelectorAll('.slider-container').forEach(function(s){
      if(filled)return;
      var h=s.querySelector('.title-text');
      if(!h||h.textContent.trim()!==titleText)return;
      var sc=s.querySelector('.slider-content');
      if(!sc)return;

      // If slider is empty (TMDB returned nothing), fill it
      if(sc.children.length===0){
        sc.innerHTML=buildCards(items);
        showSlider(s);
        filled=true;
      }
    });
    // If native slider not found yet, retry (Vue may not have rendered)
    if(!filled&&attempts<40){setTimeout(tryFill,300)}
  }
  tryFill();
}

function buildCards(items){
  var html='';
  for(var i=0;i<items.length;i++){
    var it=items[i];
    var t=(it.title||'').length>28?(it.title||'').substring(0,28)+'...':(it.title||'');
    var p=it.poster_path||it.poster||'';
    var mid=it.media_id||it.id||'';
    if(mid&&!/^metatube_search:/.test(mid))mid='metatube_search:'+mid;
    html+='<div style="width:9rem;flex-shrink:0"><a href="#/media?mediaid='+encodeURIComponent(mid)+'&type=\u7535\u5f71" style="text-decoration:none;color:inherit">';
    html+='<div class="v-card v-theme--dark v-card--density-default elevation-0 rounded-lg v-card--variant-elevated outline-none overflow-hidden" style="width:9rem;cursor:pointer">';
    if(p){
      html+='<div style="padding-bottom:150%;position:relative"><img src="'+p+'" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover" loading="lazy" onerror="this.style.display=\'none\'"></div>';
    }else{
      html+='<div style="padding-bottom:150%"></div>';
    }
    html+='<div style="padding:.3rem .4rem;font-size:.65rem;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+t+'</div>';
    html+='</div></a></div>';
  }
  return html;
}

function showSlider(s){
  // Walk up to find the wrapper with data-v-eac58b7f and un-hide
  var w=s.parentElement;
  while(w){
    if(w.hasAttribute('data-v-eac58b7f')){w.style.display='';break}
    w=w.parentElement;
  }
  s.style.display='';
  if(s.dataset.bmHidden)delete s.dataset.bmHidden;
}

function makeSlider(title,items,isStill){
  if(!items||!items.length)return'';
  var h='<div class="bytemuse-section" style="margin-top:1.5rem">';
  h+='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.6rem;padding:0 .25rem">';
  h+='<span style="font-size:.95rem;font-weight:600">'+title+'</span>';
  h+='<span style="font-size:.7rem;opacity:.5">'+items.length+'</span></div>';
  h+='<div style="display:flex;gap:.5rem;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:.5rem;scrollbar-width:thin">';
  for(var i=0;i<items.length;i++){
    if(isStill){
      h+='<div class="bm-still" data-i="'+i+'" style="flex-shrink:0;width:200px;scroll-snap-align:start;border-radius:.5rem;overflow:hidden;cursor:pointer">';
      h+='<img src="'+items[i]+'" style="width:100%;aspect-ratio:3/2;object-fit:cover;display:block" loading="lazy" onerror="this.parentElement.remove()"></div>';
    }else{
      var it=items[i];
      var t=(it.title||'').length>24?(it.title||'').substring(0,24)+'...':(it.title||'');
      var p=it.poster_path||it.poster||'';
      var mid=it.media_id||it.id||'';
      if(mid&&!/^metatube_search:/.test(mid))mid='metatube_search:'+mid;
      h+='<a href="#/media?mediaid='+encodeURIComponent(mid)+'&type=\u7535\u5f71" style="flex-shrink:0;width:110px;scroll-snap-align:start;text-decoration:none;color:inherit;display:block">';
      h+='<div style="border-radius:.5rem;overflow:hidden">';
      if(p)h+='<img src="'+p+'" style="width:100%;aspect-ratio:2/3;object-fit:cover;display:block" loading="lazy" onerror="this.style.display=\'none\'">';
      else h+='<div style="width:100%;aspect-ratio:2/3;background:rgba(100,100,100,.1)"></div>';
      h+='<div style="padding:.35rem .4rem;font-size:.65rem;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+t+'</div></div></a>';
    }
  }
  h+='</div></div>';
  return h;
}

/* ===== Lightbox ===== */
var _lb=null,_lbS=[],_lbI=0;
function lbOpen(idx,stills){
  _lbS=stills||[];if(!_lbS.length)return;_lbI=idx;if(_lb)_lb.remove();
  _lb=document.createElement('div');
  _lb.style.cssText='position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;user-select:none';
  _lb.addEventListener('click',function(e){if(e.target===_lb)lbClose()});
  var bar=document.createElement('div');
  bar.style.cssText='position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:.75rem 1rem';
  var ct=document.createElement('span');ct.style.cssText='color:#fff;font-size:.8rem;opacity:.7';ct.textContent=(idx+1)+' / '+_lbS.length;bar.appendChild(ct);
  var cls=document.createElement('button');cls.textContent='\u2715';cls.style.cssText='background:none;border:none;color:#fff;font-size:1.2rem;cursor:pointer;opacity:.6';cls.addEventListener('click',function(e){e.stopPropagation();lbClose()});bar.appendChild(cls);
  _lb.appendChild(bar);
  var area=document.createElement('div');area.style.cssText='display:flex;align-items:center;gap:1rem;max-width:95vw';
  function mkNav(d){var b=document.createElement('button');b.textContent=d<0?'\u25C0':'\u25B6';b.style.cssText='background:rgba(255,255,255,.1);border:none;color:#fff;width:40px;height:40px;border-radius:50%;font-size:1rem;cursor:pointer;flex-shrink:0';b.addEventListener('click',function(e){e.stopPropagation();lbNav(d)});return b}
  area.appendChild(mkNav(-1));
  var img=document.createElement('img');img.style.cssText='max-width:80vw;max-height:75vh;object-fit:contain;border-radius:.25rem';img.src=_lbS[idx];
  area.appendChild(img);area.appendChild(mkNav(1));_lb.appendChild(area);
  var strip=document.createElement('div');strip.style.cssText='display:flex;gap:4px;margin-top:.75rem;overflow-x:auto;max-width:88vw';
  for(var i=0;i<_lbS.length;i++){(function(idx){var th=document.createElement('img');th.src=_lbS[idx];th.style.cssText='height:36px;border-radius:3px;object-fit:cover;cursor:pointer;opacity:'+(idx===i?'1':'.45')+';border:2px solid '+(idx===i?'#fff':'transparent')+';flex-shrink:0';th.addEventListener('click',function(e){e.stopPropagation();lbGo(idx)});strip.appendChild(th)})(i)}
  _lb.appendChild(strip);document.body.appendChild(_lb);document.addEventListener('keydown',lbKey);
}
function lbNav(d){_lbI=(_lbI+d+_lbS.length)%_lbS.length;lbUpd()}
function lbGo(i){_lbI=i;lbUpd()}
function lbUpd(){
  var i=_lbI,all=_lb.querySelectorAll('img');
  for(var j=0;j<all.length;j++){var el=all[j];if(el.style.height==='36px'){el.style.opacity=(j===i)?'1':'.45';el.style.border=(j===i)?'2px solid #fff':'2px solid transparent'}}
  var mainImg=_lb.querySelector('div:nth-child(2) img');
  if(mainImg){mainImg.style.opacity='0';(function(m,idx){setTimeout(function(){m.src=_lbS[idx];m.style.opacity='1'},100)})(mainImg,i)}
  var counter=_lb.querySelector('span');if(counter)counter.textContent=(i+1)+' / '+_lbS.length;
}
function lbClose(){if(_lb){_lb.remove();_lb=null;document.removeEventListener('keydown',lbKey)}}
function lbKey(e){if(!_lb)return;if(e.key==='ArrowLeft')lbNav(-1);if(e.key==='ArrowRight')lbNav(1);if(e.key==='Escape')lbClose()}

setInterval(checkAndInject,500);
window.addEventListener('hashchange',function(){_done={};setTimeout(checkAndInject,300)});
})();
