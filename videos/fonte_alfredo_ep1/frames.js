const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [,, html, outdir, fps, only] = process.argv;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type()==='error') errs.push(m.text()); });
  await p.goto('file://' + html, { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  const total = await p.evaluate(() => TL.total);
  fs.mkdirSync(outdir, { recursive: true });
  const times = only ? only.split(',').map(Number) : Array.from({ length: Math.ceil(total * fps) }, (_, i) => i / fps);
  let n = 0;
  for (const t of times) {
    await p.evaluate(t => render(t), t);
    await p.screenshot({ path: `${outdir}/f${String(n).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 90 });
    n++;
  }
  console.log('frames', n, 'errors', JSON.stringify(errs));
  await b.close();
})();
