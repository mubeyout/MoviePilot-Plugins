import re
import time

html = open('/public/index.html', 'r').read()

# Remove old injections
html = re.sub(r'<script id="stills-inject[^"]*"[^>]*>.*?</script>\s*', '', html, flags=re.DOTALL)
html = re.sub(r'<script id="mediaverse-explore[^"]*"[^>]*>.*?</script>\s*', '', html, flags=re.DOTALL)

# Copy JS files
import shutil
shutil.copy('/config/stills-inject.js', '/public/stills-inject.js')
if __import__('os').path.exists('/config/mediaverse-explore.js'):
    shutil.copy('/config/mediaverse-explore.js', '/public/mediaverse-explore.js')
    print('MediaVerse explore script copied')
else:
    print('MediaVerse explore script not found, skipping')

# Inline hook in <head> - intercepts JSON.parse to catch API responses
head_hook = '''<script id="stills-inject-hook">
(function(){
var _origParse=JSON.parse;
JSON.parse=function(){
  var r=_origParse.apply(this,arguments);
  try{
    var d=r;
    if(d&&d.detail)d=d.detail;
    if(d&&d.source==="bytemuse"&&d.stills&&d.stills.length){
      window.__bmData=d;
      console.log("[BM-hook] JSON.parse caught bytemuse, stills:",d.stills.length);
    }
  }catch(e){}
  return r;
};
})();
</script>'''

html = html.replace('<head>', '<head>\n' + head_hook, 1)

# Scripts before </body>
ts = str(int(time.time()))
main_loader = '<script id="stills-inject" src="/stills-inject.js?v=' + ts + '"></script>'
mediaverse_loader = '<script id="mediaverse-explore" src="/mediaverse-explore.js?v=' + ts + '"></script>'
html = html.replace('</body>', mediaverse_loader + '\n' + main_loader + '\n</body>')

open('/public/index.html', 'w').write(html)
print('Done, JSON.parse hook + mediaverse-explore + main-loader injected')
