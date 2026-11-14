// Captures the DS-07 API responses used by component and page tests (TRD 04 §4.14; TRD 14 TDV-016).
// Run against the local stack after `python -m backend.cli seed test_v0_1` and the DS-10 loader:
//   API=http://localhost:8000 ADMIN_PASSWORD=... RESEARCHER_PASSWORD=... node tests/fixtures/capture.mjs
// Synthetic test data only. Volatile values (ids of users, request ids) are kept as returned.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const API = `${process.env.API ?? "http://localhost:8000"}/api/v1`;
const OUT = join(dirname(fileURLToPath(import.meta.url)), "ds07");
const RESIDENTS = ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10"];

async function login(email, password) {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`login ${email}: ${res.status}`);
  return (await res.json()).access_token;
}

async function get(token, path) {
  const res = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`GET ${path}: ${res.status} ${await res.text()}`);
  return res.json();
}

function save(name, body) {
  const file = join(OUT, `${name}.json`);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, `${JSON.stringify(body, null, 2)}\n`);
}

const admin = await login("admin@example.com", process.env.ADMIN_PASSWORD);
const researcher = await login("researcher@example.com", process.env.RESEARCHER_PASSWORD);

save("me-admin", await get(admin, "/auth/me"));
save("me-researcher", await get(researcher, "/auth/me"));
save("config-ui", await get(admin, "/config/ui"));
save(
  "residents",
  await get(admin, "/residents?sort=alarm&cohort=longitudinal&include_withdrawn=false&limit=500"),
);
save("alerts-open", await get(admin, "/alerts?status=open"));
save("devices", await get(admin, "/devices?limit=500&offset=0"));
save("data-alerts-open", await get(admin, "/data-alerts?status=open"));
save("analytics", await get(researcher, "/analytics"));
save("admissions", await get(admin, "/admissions?limit=500&offset=0"));
save("pipeline-runs", await get(admin, "/pipeline/runs"));
save("users", await get(admin, "/users"));
for (const code of RESIDENTS) {
  save(`resident/${code}`, await get(admin, `/residents/${code}`));
  save(`resident/${code}-checkins`, await get(admin, `/residents/${code}/checkins`));
  save(`resident/${code}-features`, await get(admin, `/residents/${code}/features`));
  save(`resident/${code}-scores`, await get(admin, `/scores?resident_code=${code}`));
  save(`resident/${code}-notes`, await get(admin, `/residents/${code}/notes`));
  const alerts = await get(admin, `/alerts?resident_code=${code}`);
  save(`resident/${code}-alerts`, alerts);
  for (const alert of alerts.items) {
    save(`resident/${code}-reviews`, await get(admin, `/alerts/${alert.id}/reviews`));
  }
}
console.log(`Fixtures written to ${OUT}`);
