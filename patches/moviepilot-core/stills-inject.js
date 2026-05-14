(function(){
console.log('[BM] v8 LOADED');
var _done=new Set();

function checkAndInject(){
  var mid=location.hash.match(/mediaid=([^&]+)/);
  if(!mid)return;
  mid=decodeURIComponent(mid[1]).replace(/^[^:]+:/,'');
  if(_done.has(mid))return;
  
  var data=window.__bmData;
  if(!data){setTimeout(checkAndInject,300);return}
  if(!data.stills||!data.stills.length){setTimeout(checkAndInject,300);return}
  
  _done.add(mid);
  console.log('[BM] injecting stills:',data.stills.length,'similar:',(data.similar||[]).length);
  doInject(data);
}

function doInject(data){
  var tries=0;
  function wait(){
    var ov=document.querySelector('.media-overview');
    if(!ov){if(tries<50){tries++;setTimeout(wait,200)}return}
    if(ov.querySelector('.bytemuse-section'))return;
    var stills=data.stills||[];
    var similar=data.similar||[];
    hideEmpty('\u7c7b\u4f3c');
    if(stills.length){
      ov.insertAdjacentHTML('beforeend',makeSlider('\u5267\u7167',stills,true));
      ov.querySelectorAll('.bm-still').forEach(function(el){
        el.addEventListener('click',function(){lbOpen(parseInt(el.dataset.i),stills)});
      });
      console.log('[BM] stills DONE:',stills.length);
    }
    if(similar.length){
      var pg=document.querySelector('.media-page');
      if(pg){pg.insertAdjacentHTML('beforeend',makeSlider('\u7c7b\u4f3c\u4f5c\u54c1',similar,false));console.log('[BM] similar DONE:',similar.length)}
    }
  }
  wait();
}

function hideEmpty(title){
  document.querySelectorAll('.slider-container').forEach(function(s){
    var h=s.querySelector('.title-text');
    if(h&&h.textContent.trim()===title){
      var empty=true;
      s.querySelectorAll('.media-card').forEach(function(c){
        var img=c.querySelector('img');
        if(img&&img.src&&img.className.indexOf('v-img--booting')===-1)empty=false;
      });
      if(empty)s.style.display='none';
    }
  });
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

checkAndInject();
window.addEventListener('hashchange',function(){_done.clear();setTimeout(checkAndInject,500)});
})();
