/**
 * screenshot.js
 * Opens the hosted bulletin in a headless browser,
 * waits for the Google Sheets data to load, and saves a screenshot.
 *
 * Run by GitHub Actions — do not edit the OUTPUT_FILE path.
 */

const puppeteer = require('puppeteer');

// URL of the bulletin hosted on GitHub Pages
// Replace with your actual GitHub Pages URL once the repo is published
const BULLETIN_URL = process.env.BULLETIN_URL || 'https://YOUR-USERNAME.github.io/racing-forecast/bulletin.html';
const OUTPUT_FILE  = 'bulletin_screenshot.png';

(async () => {
  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  // Match the bulletin's design width
  await page.setViewport({ width: 1340, height: 900, deviceScaleFactor: 2 });

  console.log(`Opening ${BULLETIN_URL} …`);
  await page.goto(BULLETIN_URL, { waitUntil: 'networkidle0', timeout: 30000 });

  // Wait until the grid is populated (data loaded from Google Sheets)
  await page.waitForFunction(
    () => {
      const grid = document.getElementById('grid');
      return grid && !grid.querySelector('.status');
    },
    { timeout: 20000 }
  );

  // Extra wait for images (logos) to finish loading
  await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 2000)));

  // Clip to the .page element only (no body background overflow)
  const pageEl = await page.$('.page');
  const box    = await pageEl.boundingBox();

  await page.screenshot({
    path: OUTPUT_FILE,
    clip: {
      x:      Math.floor(box.x),
      y:      Math.floor(box.y),
      width:  Math.ceil(box.width),
      height: Math.ceil(box.height),
    }
  });

  console.log(`Screenshot saved → ${OUTPUT_FILE}`);
  await browser.close();
})();
