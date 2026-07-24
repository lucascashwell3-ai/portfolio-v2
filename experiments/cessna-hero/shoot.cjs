/* Screenshot harness for cessna-hero prototype */
const { chromium } = require('/tmp/claude-0/-home-user/01be7249-bf6f-59b4-b059-00b33f8e7846/scratchpad/node_modules/playwright');
const path = require('path');
const fs = require('fs');

const WT = '/tmp/claude-0/-home-user/01be7249-bf6f-59b4-b059-00b33f8e7846/scratchpad/cessna-wt';
const OUT = '/tmp/claude-0/-home-user/01be7249-bf6f-59b4-b059-00b33f8e7846/scratchpad/cessna-shots';
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium',
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
           '--disable-gpu-sandbox', '--no-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  const url = 'file://' + path.join(WT, 'experiments/cessna-hero/index.html');
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForTimeout(1200);

  const glInfo = await page.evaluate(() => {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2') || c.getContext('webgl');
    if (!gl) return 'NO WEBGL';
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    return dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'webgl ok (no dbg info)';
  });
  console.log('GL:', glInfo);
  console.log('state after load:', await page.evaluate(() => window.__cessna && window.__cessna.state));

  // helper: render one frame after driving sim
  const settle = async (ms = 400) => page.waitForTimeout(ms);

  // 1. cockpit intro — ~5.3s in (head settled, prop disc spun up, "Clear prop!")
  await page.evaluate(() => { window.__cessna.ff(5.3); });
  await settle(200);
  await page.screenshot({ path: OUT + '/1-intro.png' });
  console.log('intro state:', await page.evaluate(() => window.__cessna.state));

  // 2. cruise over the world — skip intro, fast-forward into cruise, look slightly left toward islands
  await page.evaluate(() => {
    const c = window.__cessna;
    c.skipIntro();
    // stage: south of the archipelago, heading west into the sun, Skillproof ahead-below
    c.S.theta = Math.PI * 0.55;
    c.S.heading = Math.PI - c.S.theta;
    c.ff(4);
    c.setLook(-0.10, -0.07);  // sun just off the center post, golden path on the water
    c.ff(1.6);
  });
  await settle(300);
  await page.screenshot({ path: OUT + '/2-cruise.png' });
  console.log('cruise state:', await page.evaluate(() => window.__cessna.state));

  // 3. mid-flight to a project — fly to DATproof, capture mid-transit (banking)
  await page.evaluate(() => {
    const c = window.__cessna;
    c.setLook(0, -0.04);      // eyes forward over the nose for the banking shot
    c.flyTo('datproof');
    c.ff(3.4);
  });
  await settle(400);
  await page.screenshot({ path: OUT + '/3-transit.png' });
  console.log('transit state:', await page.evaluate(() => window.__cessna.state),
              'roll:', await page.evaluate(() => window.__cessna.S.roll.toFixed(2)));

  // 4. project card open — finish the transit, orbiting the island
  const after9 = await page.evaluate(() => {
    window.__cessna.ff(9);
    return { mode: window.__cessna.state, tween: !!window.__cessna.S.tween,
             card: document.getElementById('card').className,
             cap: document.getElementById('caption').className };
  });
  console.log('immediately after ff(9):', JSON.stringify(after9));
  await page.waitForFunction(() =>
    window.__cessna.state === 'orbit' &&
    getComputedStyle(document.getElementById('card')).opacity === '1', { timeout: 20000 });
  await settle(400);
  await page.screenshot({ path: OUT + '/4-card.png' });
  console.log('orbit state:', await page.evaluate(() => window.__cessna.state),
              'card on:', await page.evaluate(() => document.getElementById('card').classList.contains('on')),
              'card opacity:', await page.evaluate(() => getComputedStyle(document.getElementById('card')).opacity));

  await page.close();   // free the GPU thread before the fallback checks

  // 5. prefers-reduced-motion: static aerial view + clickable pills
  const rm = await browser.newPage({ viewport: { width: 1440, height: 900 },
    reducedMotion: 'reduce' });
  rm.setDefaultTimeout(60000); rm.setDefaultNavigationTimeout(60000);
  rm.on('console', m => { if (m.type() === 'error') errors.push('RM: ' + m.text()); });
  rm.on('pageerror', e => errors.push('RM PAGEERROR: ' + e.message));
  await rm.goto(url, { waitUntil: 'load' });
  await rm.waitForTimeout(1500);
  console.log('reduced-motion state:', await rm.evaluate(() => window.__cessna.state));
  await rm.screenshot({ path: OUT + '/5-reduced-motion.png' });
  await rm.click('#pills button[data-id="warden"]');
  await rm.waitForTimeout(900);
  console.log('reduced-motion card after pill click:',
    await rm.evaluate(() => document.getElementById('card').classList.contains('on') &&
                            document.getElementById('cName').textContent));
  await rm.screenshot({ path: OUT + '/6-reduced-motion-card.png' });
  await rm.close();

  // 6. WebGL unavailable → fallback message
  const ng = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await ng.addInitScript(() => {
    const orig = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type, ...rest) {
      if (String(type).startsWith('webgl')) return null;
      return orig.call(this, type, ...rest);
    };
  });
  await ng.goto(url, { waitUntil: 'load' });
  await ng.waitForTimeout(600);
  console.log('nogl visible:', await ng.evaluate(() =>
    getComputedStyle(document.getElementById('nogl')).display));
  await ng.screenshot({ path: OUT + '/7-nogl.png' });
  await ng.close();

  console.log('CONSOLE ERRORS:', errors.length ? errors : 'none');
  await browser.close();
})().catch(e => { console.error('HARNESS FAIL:', e); process.exit(1); });
