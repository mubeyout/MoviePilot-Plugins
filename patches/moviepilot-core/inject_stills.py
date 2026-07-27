import re
import time

html = open('/public/index.html', 'r').read()

# Remove old injections
html = re.sub(r'<script id="stills-inject[^"]*"[^>]*>.*?</script>\s*', '', html, flags=re.DOTALL)

# Copy JS file
import shutil
shutil.copy('/config/stills-inject.js', '/public/stills-inject.js')

# Read API_TOKEN from app.env
api_token = ''
try:
    with open('/config/app.env', 'r') as f:
        for line in f:
            if line.strip().startswith('API_TOKEN='):
                api_token = line.strip().split('=', 1)[1].strip("'\"")
                break
except:
    pass

# Inline hook in <head>:
# 1. JSON.parse hook: for ByteMuse media, replace tmdb_id with BM_{code} so XHR interceptor can redirect
# 2. For subscribe list responses, add BM_ prefix to tmdbid so status matches
# 3. Expose API_TOKEN for XHR redirect (adds apikey query param)
head_hook = '''<script id="stills-inject-hook">
(function(){
window.__BM_API_TOKEN=''' + repr(api_token) + ''';

var _origParse=JSON.parse;

// Check if a string looks like an adult video code (not a numeric TMDB ID)
function isAvCode(s){
  if(!s||typeof s!=='string')return false;
  // Numeric IDs (TMDB/Douban) should not be prefixed
  if(/^-?\\d+$/.test(s))return false;
  // Already prefixed
  if(s.indexOf('BM_')===0)return false;
  // AV code pattern: letters + numbers (e.g. SSIS-001, JKSR-743)
  return /^[A-Za-z]{2,}-?\\d/.test(s);
}

JSON.parse=function(){
  var r=_origParse.apply(this,arguments);
  try{
    if(r&&typeof r==='object'&&!Array.isArray(r)){
      // Case 1: Single ByteMuse media in API response
      if(r.source==='bytemuse'&&r.media_id&&r.tmdb_id){
        var code=r.media_id.toString().replace(/^[^:]+:/,'');
        if(r.tmdb_id!=='BM_'+code){
          r.tmdb_id='BM_'+code;
          console.log('[BM-hook] Rewrote tmdb_id -> BM_'+code);
        }
      }
      // Case 2: Wrapped response {data: {...}}
      if(r.data&&typeof r.data==='object'&&!Array.isArray(r.data)&&r.data.source==='bytemuse'&&r.data.media_id){
        var code2=r.data.media_id.toString().replace(/^[^:]+:/,'');
        if(r.data.tmdb_id!=='BM_'+code2){
          r.data.tmdb_id='BM_'+code2;
          console.log('[BM-hook] Rewrote data.tmdb_id -> BM_'+code2);
        }
      }
      // Case 3: Subscribe list item with AV code tmdbid (non-numeric)
      if(r.tmdbid&&isAvCode(r.tmdbid)){
        r.tmdbid='BM_'+r.tmdbid;
      }
    }
    // Case 4: Array of subscribe items
    if(Array.isArray(r)){
      for(var i=0;i<r.length;i++){
        if(r[i]&&typeof r[i]==='object'&&r[i].tmdbid&&isAvCode(r[i].tmdbid)){
          r[i].tmdbid='BM_'+r[i].tmdbid;
        }
      }
    }
  }catch(e){}
  return r;
};
})();
</script>'''

html = html.replace('<head>', '<head>\n' + head_hook, 1)

# Main script before </body>
ts = str(int(time.time()))
main_loader = '<script id="stills-inject" src="/stills-inject.js?v=' + ts + '"></script>'
html = html.replace('</body>', main_loader + '\n</body>')

open('/public/index.html', 'w').write(html)
print('Done, JSON.parse hook v2 (tmdb_id rewrite + subscribe list BM_ prefix + API_TOKEN) + main-loader injected')
