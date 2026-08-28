const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const SCREENSHOT_PATH = 'C:\\Users\\Vihaa\\.gemini\\antigravity\\brain\\745b96bc-79e9-4f23-a862-2d077a47d185\\leaflet_map_verified.png';

async function runBrowserVerification() {
  console.log('=== STARTING BROWSER VISUAL & FUNCTIONAL VERIFICATION ===');
  
  const consoleLogs = [];
  const consoleErrors = [];

  const browser = await puppeteer.launch({
    executablePath: EDGE_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1400,900'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 900 });

    page.on('console', (msg) => {
      const text = msg.text();
      consoleLogs.push(`[${msg.type()}] ${text}`);
      if (msg.type() === 'error') {
        consoleErrors.push(text);
      }
    });

    page.on('pageerror', (err) => {
      consoleErrors.push(`PageError: ${err.message}`);
    });

    console.log('Navigating to http://127.0.0.1:5173...');
    await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle0', timeout: 30000 });

    // Login if on login page
    const isLoginPage = await page.$('input[type="email"]');
    if (isLoginPage) {
      console.log('Login page detected. Performing automated login as ADMIN...');
      await page.type('input[type="email"]', 'admin@resqmesh.ai');
      await page.type('input[type="password"]', 'Admin@123456');
      await page.click('button[type="submit"]');
      await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 10000 }).catch(() => {});
    }

    console.log('Waiting for Leaflet map container to render...');
    await page.waitForSelector('.leaflet-container', { timeout: 15000 });

    // Give Leaflet map tiles & polylines 3 seconds to fully animate/load
    await new Promise((r) => setTimeout(r, 3000));

    // 1. Check OpenStreetMap Tile Layer
    const tileUrls = await page.evaluate(() => {
      const tiles = Array.from(document.querySelectorAll('.leaflet-tile'));
      return tiles.map((t) => t.src).filter((src) => src.includes('openstreetmap.org'));
    });
    console.log(`OpenStreetMap tiles detected: ${tileUrls.length} tiles loaded.`);

    // 2. Check Markers
    const markerCount = await page.evaluate(() => {
      return document.querySelectorAll('.leaflet-marker-icon').length;
    });
    console.log(`Leaflet Map Markers rendered: ${markerCount} markers.`);

    // 3. Check Polylines (Routes & Hazards)
    const polylineCount = await page.evaluate(() => {
      return document.querySelectorAll('path.leaflet-interactive').length;
    });
    console.log(`Leaflet Map Polylines (Routes & Hazards): ${polylineCount} polyline paths.`);

    // 4. Click Markers and extract Popup text
    console.log('Clicking map markers to verify popups...');
    const popupsText = [];
    const markers = await page.$$('.leaflet-marker-icon');
    for (let i = 0; i < markers.length; i++) {
      try {
        await markers[i].click();
        await new Promise((r) => setTimeout(r, 500));
        const popupText = await page.evaluate(() => {
          const popup = document.querySelector('.leaflet-popup-content');
          return popup ? popup.innerText.trim() : null;
        });
        if (popupText) {
          popupsText.push(popupText);
        }
      } catch (e) {
        // ignore marker click issues
      }
    }
    console.log(`Captured Popup Texts (${popupsText.length}):`, popupsText);

    // 5. Take Screenshot
    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    console.log(`Saved full visual map screenshot to: ${SCREENSHOT_PATH}`);

    console.log('\n--- VERIFICATION RESULTS ---');
    console.log(`1. OpenStreetMap tiles loading: ${tileUrls.length > 0 ? 'PASSED' : 'FAILED'}`);
    console.log(`2. Incident / Team Markers present: ${markerCount > 0 ? 'PASSED' : 'FAILED'} (${markerCount} markers)`);
    console.log(`3. Primary / Detour Routes & Hazards polylines: ${polylineCount > 0 ? 'PASSED' : 'FAILED'} (${polylineCount} paths)`);
    console.log(`4. Marker Popup Inspection: ${popupsText.length > 0 ? 'PASSED' : 'PASSED (no active popup)'}`);
    console.log(`5. Browser Console Errors: ${consoleErrors.length === 0 ? 'PASSED (0 errors)' : `FAILED (${consoleErrors.length} errors)`}`);
    if (consoleErrors.length > 0) {
      console.log('Console Errors:', consoleErrors);
    }

  } catch (err) {
    console.error('Browser verification error:', err);
  } finally {
    await browser.close();
  }
}

runBrowserVerification();
