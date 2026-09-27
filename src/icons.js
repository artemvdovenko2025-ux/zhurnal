const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const p = await b.newPage();
  await p.goto('file://' + __dirname + '/icons.html');
  const jobs = [['#a192 .ic','icon-192.png',true],['#a512 .ic','icon-512.png',true],
                ['#m512 .ic','icon-maskable-512.png',false],['#t180 .ic','apple-touch-icon.png',false]];
  for (const [sel, name, transparent] of jobs)
    await p.locator(sel).screenshot({ path: 'out/site/' + name, omitBackground: transparent });
  await b.close();
  console.log('значки готовы');
})();
