(function(){
console.log('[BM] v20 LOADED (native sliders + subscribe fix)');

var _done={};
var _pending=null;
var _ak='';

// Get API token from global (set by inject_stills.py head hook)
if(window.__BM_API_TOKEN){_ak=window.__BM_API_TOKEN}

// ===== XHR Interception =====
var _origOpen=XMLHttpRequest.prototype.open;
var _origSend=XMLHttpRequest.prototype.send;

XMLHttpRequest.prototype.open=function(method,url,async,user,pass){
  this._bmMethod=method;
  this._bmUrl=url;
  if(url){
    // Intercept recommend: tmdb/recommend/BM_{code} -> bytemuse_similar (同演员作品 = 推荐)
    var recMatch=url.match(/tmdb\/recommend\/BM_([^\/]+)/);
    // Intercept similar: tmdb/similar/BM_{code} -> bytemuse_recommend (月榜 = 类似)
    var simMatch=url.match(/tmdb\/similar\/BM_([^\/]+)/);
    // Intercept credits: tmdb/credits/BM_{code} -> bytemuse_credits (演员阵容)
    var credMatch=url.match(/tmdb\/credits\/BM_([^\/]+)/);

    if(recMatch||simMatch||credMatch){
      var code=recMatch?recMatch[1]:(simMatch?simMatch[1]:credMatch[1]);
      var endpoint='';
      if(recMatch) endpoint='bytemuse_similar';      // 推荐 = 同演员作品
      else if(simMatch) endpoint='bytemuse_recommend'; // 类似 = 月榜
      else endpoint='bytemuse_credits';                // 演员阵容

      var newUrl='/api/v1/plugin/ByteMuseDiscover/'+endpoint+'/'+encodeURIComponent(code);
      var akMatch=url.match(/[?&]apikey=([^&]+)/);
      var apiKey=akMatch?akMatch[1]:_ak;
      if(apiKey) newUrl+='?apikey='+encodeURIComponent(apiKey);
      url=newUrl;
      console.log('[BM] XHR redirect ->',url);
    }
  }
  return _origOpen.call(this,method,url,async!==false,user,pass);
};

// Intercept subscribe POST: strip BM_ prefix from tmdbid in request body
XMLHttpRequest.prototype.send=function(body){
  if(this._bmMethod==='POST'&&this._bmUrl&&this._bmUrl.indexOf('subscribe')>=0&&typeof body==='string'){
    try{
      var modified=body.replace(/"tmdbid"\s*:\s*"BM_([^"]+)"/g, function(m,code){
        return '"tmdbid":"'+code+'"';
      });
      if(modified!==body){
        console.log('[BM] subscribe: stripped BM_ prefix from tmdbid');
        body=modified;
      }
    }catch(e){}
  }
  return _origSend.call(this,body);
};

// ===== fetch interception =====
var _origFetch=window.fetch;
window.fetch=function(input,init){
  var url=typeof input==='string'?input:(input&&input.url)||'';
  var recMatch=url.match(/tmdb\/recommend\/BM_([^\/]+)/);
  var simMatch=url.match(/tmdb\/similar\/BM_([^\/]+)/);
  var credMatch=url.match(/tmdb\/credits\/BM_([^\/]+)/);

  if(recMatch||simMatch||credMatch){
    var code=recMatch?recMatch[1]:(simMatch?simMatch[1]:credMatch[1]);
    var endpoint='';
    if(recMatch) endpoint='bytemuse_similar';
    else if(simMatch) endpoint='bytemuse_recommend';
    else endpoint='bytemuse_credits';

    var newUrl='/api/v1/plugin/ByteMuseDiscover/'+endpoint+'/'+encodeURIComponent(code);
    var akMatch=url.match(/[?&]apikey=([^&]+)/);
    var apiKey=akMatch?akMatch[1]:_ak;
    if(apiKey) newUrl+='?apikey='+encodeURIComponent(apiKey);
    console.log('[BM] fetch redirect ->',newUrl);
    return _origFetch.call(this,newUrl,init);
  }

  // Intercept subscribe POST: strip BM_ prefix from tmdbid
  if(init&&init.method==='POST'&&typeof url==='string'&&url.indexOf('subscribe')>=0&&init.body&&typeof init.body==='string'){
    try{
      var modified=init.body.replace(/"tmdbid"\s*:\s*"BM_([^"]+)"/g, function(m,code){
        return '"tmdbid":"'+code+'"';
      });
      if(modified!==init.body){
        console.log('[BM] subscribe fetch: stripped BM_ prefix');
        init=Object.assign({},init,{body:modified});
      }
    }catch(e){}
  }

  return _origFetch.call(this,input,init);
};

// ===== Stills / Description Injection =====
function getMediaId(){
  var m=location.hash.match(/mediaid=([^&]+)/);
  if(!m)return null;
  return decodeURIComponent(m[1]).replace(/^[^:]+:/,'');
}

function checkAndInject(){
  var mid=getMediaId();
  if(!mid)return;
  if(_done[mid])return;
  var ov=document.querySelector('.media-overview');
  if(ov&&ov.dataset.bmDone==='1'){_done[mid]=1;return}
  if(!_pending||_pending!==mid){_pending=mid;fetchDetail(mid)}
}

function fetchDetail(mid){
  fetch('/api/v1/plugin/ByteMuseDiscover/bytemuse_detail/'+encodeURIComponent(mid),{credentials:'include'})
    .then(function(r){return r.ok?r.json():null})
    .then(function(data){
      _pending=null;
      if(!data)return;
      var hasData=(data.stills&&data.stills.length)||(data.description);
      if(!hasData)return;
      _done[mid]=1;
      doInject(data);
    })
    .catch(function(){_pending=null});
}

function doInject(data){
  var ov=document.querySelector('.media-overview');
  if(!ov||ov.dataset.bmDone==='1')return;

  var stills=data.stills||[];
  var description=data.description||'';

  var overviewLeft=ov.querySelector('.media-overview-left');
  if(overviewLeft){
    var pEl=overviewLeft.querySelector('p');
    if(pEl&&description){
      pEl.textContent=description;
      pEl.style.whiteSpace='pre-wrap';
    }
  }

  if(stills.length){
    ov.insertAdjacentHTML('afterend',makeStillSlider(stills));
    ov.parentElement.querySelectorAll('.bm-still').forEach(function(el){
      el.addEventListener('click',function(){lbOpen(parseInt(el.dataset.i),stills)});
    });
    console.log('[BM] stills:',stills.length);
  }

  ov.dataset.bmDone='1';
}

function makeStillSlider(stills){
  var h='<div class="bytemuse-section" style="margin-top:1.5rem">';
  h+='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.6rem;padding:0 .25rem">';
  h+='<span style="font-size:.95rem;font-weight:600">剧照</span>';
  h+='<span style="font-size:.7rem;opacity:.5">'+stills.length+'</span></div>';
  h+='<div style="display:flex;gap:.5rem;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:.5rem;scrollbar-width:thin">';
  for(var i=0;i<stills.length;i++){
    h+='<div class="bm-still" data-i="'+i+'" style="flex-shrink:0;width:200px;scroll-snap-align:start;border-radius:.5rem;overflow:hidden;cursor:pointer">';
    h+='<img src="'+stills[i]+'" style="width:100%;aspect-ratio:3/2;object-fit:cover;display:block" loading="lazy" onerror="this.parentElement.remove()"></div>';
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
window.addEventListener('hashchange',function(){
  _done={};
  var ov=document.querySelector('.media-overview');
  if(ov)delete ov.dataset.bmDone;
  setTimeout(checkAndInject,300);
});
})();
