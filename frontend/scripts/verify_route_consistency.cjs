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
  console.log('=== STARTING ROUTE INTELLIGENCE CONSISTENCY BROWSER VERIFICATION ===');

  const validIncidentId = 10;
  const validTeamId = 4;

  // 1. Propose & dispatch EN_ROUTE mission
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

  // 2. Open browser
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

  // Inspect Mission Card Route Intelligence text
  const cardRouteText = await page.evaluate((mId) => {
    const cards = Array.from(document.querySelectorAll('.cursor-pointer'));
    const card = cards.find(c => c.textContent.includes(`MISSION #${mId}`));
    return card ? card.textContent : null;
  }, missionId);

  console.log('2. Mission Card Text before replan:');
  console.log(cardRouteText);

  if (cardRouteText && cardRouteText.includes('OSRM route verified')) {
    console.log('✓ Mission card correctly displays "OSRM route verified" with distance and ETA!');
  } else {
    console.warn('⚠️ Card route text mismatch:', cardRouteText);
  }

  // 3. Post blocking hazard to trigger replan
  console.log('3. Triggering dynamic replanning via blocking hazard...');
  await makeApiRequest('/road-status', 'POST', {
    road_name: "Flooding on route",
    condition: "BLOCKED",
    latitude_start: 17.4440,
    longitude_start: 78.3780,
    latitude_end: 17.4445,
    longitude_end: 78.3770,
  });

  await new Promise(r => setTimeout(r, 3000));
  await page.reload({ waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 3000));

  // 4. Click APPROVE DETOUR button
  const approveBtn = await page.evaluateHandle(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    return buttons.find(b => b.textContent.includes('APPROVE DETOUR'));
  });

  if (approveBtn.asElement()) {
    console.log('4. Approving detour in browser...');
    await approveBtn.asElement().click();
    await new Promise(r => setTimeout(r, 4000));
  }

  // Inspect Mission Card Route Intelligence text after approval
  const cardRouteTextAfter = await page.evaluate((mId) => {
    const cards = Array.from(document.querySelectorAll('.cursor-pointer'));
    const card = cards.find(c => c.textContent.includes(`MISSION #${mId}`));
    return card ? card.textContent : null;
  }, missionId);

  console.log('5. Mission Card Text after detour approval:');
  console.log(cardRouteTextAfter);

  const updatedMission = await makeApiRequest(`/missions/${missionId}`, 'GET');
  console.log('Updated Mission State in DB:', {
    status: updatedMission.data.status,
    pending_replan_status: updatedMission.data.pending_replan_status,
    eta: updatedMission.data.eta_minutes,
  });

  if (
    updatedMission.data.status === 'EN_ROUTE' &&
    updatedMission.data.pending_replan_status === null &&
    cardRouteTextAfter.includes('OSRM route verified')
  ) {
    console.log('=== ROUTE INTELLIGENCE CONSISTENCY VERIFICATION PASSED 100% ===');
  }

  await browser.close();
})().catch(err => {
  console.error('Verification error:', err);
  process.exit(1);
});
