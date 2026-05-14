import re

html = open('/public/index.html', 'r').read()
# Remove ALL stills-inject script blocks
html = re.sub(r'<script id="stills-inject"[^>]*>.*?</script>\s*', '', html, flags=re.DOTALL)
print('After cleanup:', html.count('stills-inject'))

# Add fresh
script = open('/config/stills-inject.js', 'r').read()
html = html.replace('</body>', script + '\n</body>')
open('/public/index.html', 'w').write(html)
print('Done, stills-inject count:', html.count('stills-inject'))
