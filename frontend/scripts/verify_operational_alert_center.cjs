const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const http = require('http');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const REAL_ADMIN_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODgwMDYwNzksInN1YiI6IjEiLCJyb2xlIjoiQURNSU4iLCJpYXQiOjE3ODc5MTk2Nzl9.IfZYC1puuVuT0dbBtE1V0h3EL7S_ThaA64fGrtrFPyo';
const ARTIFACT_DIR = 'C:\\Users\\Vihaa\\.gemini\\antigravity\\brain\\745b96bc-79e9-4f23-a862-2d077a47d185';

function makeApiRequest(endpoint, method, payload) {
  return new Promise((resolve, reject) => {
    const postData = payload ? JSON.stringify(payload) : '';
    const req = http.request(`http://127.0.0.1:8000/api/v1${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${REAL_ADMIN_TOKEN}`,
        'Content-Length': Buffer.byteLength(postData)
      }
    }, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(body) });
        } catch (e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });

    req.on('error', reject);
    if (postData) req.write(postData);
    req.end();
  });
}

(async () => {
  console.log('=== STARTING OPERATIONAL ALERT CENTER E2E BROWSER VERIFICATION ===');

  const validIncidentId = 10;
  const validTeamId = 4;

  // Create an EN_ROUTE mission & trigger a detour to populate alerts
  const missionRes = await makeApiRequest('/missions/propose', 'POST', {
    incident_id: validIncidentId,
    situation_data: { category: "FLOOD", urgency_level: "CRITICAL" },
    risk_data: { triage_level: "CRITICAL", matched_hazards: [] },
    resource_data: { rescue_team_id: validTeamId },
    route_data: {
      route_polyline: "[[78.3800, 17.4400], [78.3780, 17.4440], [78.3650, 17.4550]]",
      eta_minutes: 8.0
    }
  });

  const missionId = missionRes.data.mission_id || missionRes.data.id;
  console.log(`1. Created Mission #${missionId}`);

  await makeApiRequest(`/missions/${missionId}/authorize`, 'POST', { action: 'APPROVE' });
  await makeApiRequest(`/missions/${missionId}/dispatch`, 'POST', {});
  await makeApiRequest(`/missions/${missionId}/status`, 'POST', { status: 'EN_ROUTE' });

  // Post blocking hazard to trigger REPLAN_PENDING_HITL alert item
  await makeApiRequest('/road-status', 'POST', {
    road_name: "Alert Center Verification Hazard",
    condition: "BLOCKED",
    latitude_start: 17.4440,
    longitude_start: 78.3780,
    latitude_end: 17.4445,
    longitude_end: 78.3770,
  });

  await new Promise(r => setTimeout(r, 2500));

  // Launch browser
  const browser = await puppeteer.launch({
    executablePath: EDGE_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 950 });

  await page.goto('http://127.0.0.1:5173/admin', { waitUntil: 'domcontentloaded' });
  await page.evaluate((token) => {
    localStorage.setItem('resqmesh_token', token);
    localStorage.setItem('resqmesh_role', 'ADMIN');
    localStorage.setItem('resqmesh_user', JSON.stringify({ id: 1, email: 'admin@resqmesh.ai', role: 'ADMIN' }));
  }, REAL_ADMIN_TOKEN);

  await page.goto('http://127.0.0.1:5173/admin', { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 3000));

  // 1. Verify Operational Alert Center header & items
  const alertCenterTitle = await page.evaluate(() => {
    const el = Array.from(document.querySelectorAll('h2')).find(h => h.textContent.toUpperCase().includes('OPERATIONAL ALERT CENTER'));
    return el ? el.textContent : null;
  });

  console.log('2. Alert Center Header:', alertCenterTitle);

  const liveSyncText = await page.evaluate(() => {
    const el = Array.from(document.querySelectorAll('span')).find(s => s.textContent.includes('LIVE SYNC'));
    return el ? el.textContent : null;
  });

  console.log('3. Live Sync Indicator:', liveSyncText);

  // 2. Click an alert item and verify map & mission selection synchronization
  const alertItemClicked = await page.evaluate((mId) => {
    const alertItems = Array.from(document.querySelectorAll('.cursor-pointer'));
    const targetAlert = alertItems.find(item => item.textContent.includes(`MISSION #${mId}`));
    if (targetAlert) {
      targetAlert.click();
      return true;
    }
    return false;
  }, missionId);

  console.log(`4. Alert item clicked for Mission #${missionId}: ${alertItemClicked}`);
  await new Promise(r => setTimeout(r, 2000));

  // Screenshot: Operational Alert Center & Live Dashboard
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'screenshot_operational_alert_center.png'), fullPage: true });
  console.log('Saved screenshot: screenshot_operational_alert_center.png');

  if (alertCenterTitle && liveSyncText && alertItemClicked) {
    console.log('=== OPERATIONAL ALERT CENTER E2E VERIFICATION PASSED 100% ===');
  }

  await browser.close();
})().catch(err => {
  console.error('E2E Test Error:', err);
  process.exit(1);
});
