import re
import time

html = open('/public/index.html', 'r').read()

# Remove old injections
html = re.sub(r'<script id="stills-inject[^"]*"[^>]*>.*?</script>\s*', '', html, flags=re.DOTALL)

# Copy JS file
import shutil
shutil.copy('/config/stills-inject.js', '/public/stills-inject.js')

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

# Main script before </body>
ts = str(int(time.time()))
main_loader = '<script id="stills-inject" src="/stills-inject.js?v=' + ts + '"></script>'
html = html.replace('</body>', main_loader + '\n</body>')

open('/public/index.html', 'w').write(html)
print('Done, JSON.parse hook + main-loader injected')
