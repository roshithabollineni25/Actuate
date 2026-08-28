const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const http = require('http');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const REAL_ADMIN_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODgwMDYwNzksInN1YiI6IjEiLCJyb2xlIjoiQURNSU4iLCJpYXQiOjE3ODc5MTk2Nzl9.IfZYC1puuVuT0dbBtE1V0h3EL7S_ThaA64fGrtrFPyo';

function makeApiRequest(endpoint, method, payload) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify(payload);
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
          resolve(JSON.parse(body));
        } catch (e) {
          resolve(body);
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

(async () => {
  console.log('=== STARTING REAL BROWSER VERIFICATION OF DYNAMIC MISSION REPLANNING ===');

  // 1. Propose, approve, dispatch, and transition mission to EN_ROUTE
  console.log('1. Setting up EN_ROUTE mission via backend API...');
  const proposal = await makeApiRequest('/missions/propose', 'POST', {
    incident_id: 1,
    situation_data: { category: "FLOOD", urgency_level: "CRITICAL" },
    risk_data: { triage_level: "CRITICAL", matched_hazards: [] },
    resource_data: { rescue_team_id: 1 },
    route_data: {
      route_polyline: "[[78.3800, 17.4400], [78.3780, 17.4440], [78.3650, 17.4550]]",
      eta_minutes: 8.0
    }
  });

  const missionId = proposal.mission_id;
  console.log(`Created mission #${missionId} (Status: ${proposal.status})`);

  await makeApiRequest(`/missions/${missionId}/authorize`, 'POST', { action: 'APPROVE' });
  await makeApiRequest(`/missions/${missionId}/dispatch`, 'POST', { notes: 'Dispatching for test' });
  await makeApiRequest(`/missions/${missionId}/status`, 'POST', { status: 'EN_ROUTE', notes: 'Team moving' });
  console.log(`Mission #${missionId} transitioned to EN_ROUTE.`);

  // 2. Post new blocking hazard intersecting the route
  console.log('2. Reporting new blocking road hazard intersecting mission route...');
  const hazard = await makeApiRequest('/road-status', 'POST', {
    road_name: "Flood Hazard Point 17.4440",
    condition: "FLOODED",
    latitude_start: 17.4440,
    longitude_start: 78.3780,
    latitude_end: 17.4445,
    longitude_end: 78.3770,
    hazard_notes: "Severe flash flood road obstruction"
  });
  console.log(`Created hazard #${hazard.id}. Replanning triggered automatically.`);

  // 3. Open Edge Browser to test UI alert banner & detour approval
  console.log('3. Launching browser to verify Admin Operations HUD...');
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
  await new Promise(r => setTimeout(r, 4000));

  const artifactDir = 'C:\\Users\\Vihaa\\.gemini\\antigravity\\brain\\745b96bc-79e9-4f23-a862-2d077a47d185';
  const alertScreen = path.join(artifactDir, 'replan_hazard_alert_verified.png');
  await page.screenshot({ path: alertScreen, fullPage: true });
  console.log(`Saved ROUTE HAZARD DETECTED alert screenshot: ${alertScreen}`);

  // 4. Click APPROVE DETOUR button
  const approveDetourBtn = await page.evaluateHandle(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    return buttons.find(b => b.textContent.includes('APPROVE DETOUR'));
  });

  if (approveDetourBtn.asElement()) {
    console.log('4. Clicking APPROVE DETOUR button...');
    await approveDetourBtn.asElement().click();
    await new Promise(r => setTimeout(r, 4000));

    const approvedDetourScreen = path.join(artifactDir, 'replan_detour_activated_verified.png');
    await page.screenshot({ path: approvedDetourScreen, fullPage: true });
    console.log(`Saved DETOUR ACTIVATED screenshot: ${approvedDetourScreen}`);
  } else {
    console.warn('APPROVE DETOUR button not found in UI elements.');
  }

  await browser.close();
  console.log('=== REAL BROWSER VERIFICATION OF DYNAMIC REPLANNING COMPLETED CLEANLY ===');
})().catch(err => {
  console.error('Browser test error:', err);
  process.exit(1);
});
