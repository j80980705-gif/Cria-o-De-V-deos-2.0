import json
t=open('template.html').read()
t=t.replace('__SPRITE__',open('sprite.svg').read()).replace('__TIMELINE__',open('timeline.json').read())
open('render.html','w').write(t)
