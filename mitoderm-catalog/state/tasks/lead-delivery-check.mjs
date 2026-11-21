#!/usr/bin/env node
// "The inquiry arrived": runs the built site locally on a throwaway test database,
// sends one test inquiry and checks that
//   1) it is stored,
//   2) the CRM webhook receives it with a valid signature,
//   3) the stored row is marked as delivered,
//   4) a repeated request is acknowledged but not announced a second time.
// It never touches the real database: the worker runs with `wrangler dev --local`
// on a temporary state folder that is removed at the end.
// usage: node lead-delivery-check.mjs      (after `pnpm build` in codex-site)
// Prints one JSON line; exit code 0 when every check passed.
import { spawn, spawnSync } from "node:child_process";
import { createHmac, randomBytes, randomUUID } from "node:crypto";
import { mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../codex-site");
const state = mkdtempSync(path.join(tmpdir(), "lead-check-"));
const secret = randomBytes(24).toString("hex");
const port = 8791;
const wrangler = ["--import", "./scripts/sites-env.mjs", "./node_modules/wrangler/bin/wrangler.js"];
const local = ["--config", "dist/server/wrangler.json", "--local", "--persist-to", state];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const checks = {};
let worker;
let hook;

function d1(args) {
  const run = spawnSync("node", [...wrangler, "d1", "execute", "DB", ...local, ...args], { cwd: app, encoding: "utf8" });
  if (run.status !== 0) throw new Error("d1 execute failed: " + (run.stderr || run.stdout).slice(-300));
  return run.stdout;
}

async function until(test, ms, what) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await test().catch(() => false)) return;
    await sleep(250);
  }
  throw new Error("timed out: " + what);
}

try {
  d1(["--file", "drizzle/0000_modern_talisman.sql"]);

  // The stand-in for the CRM: records what the site sends.
  const received = [];
  hook = createServer((request, response) => {
    let body = "";
    request.on("data", (chunk) => { body += chunk; });
    request.on("end", () => {
      received.push({ signature: request.headers["x-mitoderm-signature"], body });
      response.writeHead(200, { "content-type": "application/json" }).end("{}");
    });
  });
  await new Promise((resolve) => hook.listen(0, "127.0.0.1", resolve));
  const hookUrl = "http://127.0.0.1:" + hook.address().port + "/hook";

  worker = spawn("node", [
    ...wrangler, "dev", ...local, "--ip", "127.0.0.1", "--port", String(port), "--inspector-port", "0",
    "--var", "LEADS_WEBHOOK_URL:" + hookUrl, "--var", "LEADS_WEBHOOK_SECRET:" + secret,
  ], { cwd: app, stdio: "ignore", detached: true });
  const base = "http://127.0.0.1:" + port;
  await until(async () => (await fetch(base + "/privacy")).ok, 90000, "the local site did not start");

  const inquiry = {
    name: "בדיקת מערכת", phone: "050-123-4567", profession: "cosmetologist", productSlug: "exosignal-hair",
    comment: "בדיקה", privacyConsent: true, requestId: randomUUID(), locale: "he", sourceBlock: "delivery-check",
  };
  const send = () => fetch(base + "/api/leads", {
    method: "POST", headers: { "content-type": "application/json", origin: base }, body: JSON.stringify(inquiry),
  });

  const first = await send();
  const saved = await first.json();
  checks.stored = first.status === 201 && saved.ok === true && typeof saved.id === "string";

  await until(async () => received.length >= 1, 15000, "the webhook did not receive the inquiry");
  const { signature, body } = received[0];
  const payload = JSON.parse(body);
  checks.signed = signature === "sha256=" + createHmac("sha256", secret).update(body).digest("hex");
  checks.payload = payload.source === "mitoderm-site" && payload.lead.id === saved.id &&
    payload.lead.name === inquiry.name && payload.lead.phone === "+972501234567" &&
    payload.lead.professionLabel === "קוסמטיקאי/ת" && payload.lead.productName === "EXOSIGNAL HAIR" &&
    payload.lead.comment === inquiry.comment && payload.lead.sourceBlock === "delivery-check";

  const rows = () => JSON.parse(d1(["--json", "--command", "SELECT id, status FROM mitoderm_leads"]))[0].results;
  await until(async () => rows()[0]?.status === "delivered", 15000, "the row was not marked as delivered");
  checks.marked = rows().length === 1 && rows()[0].id === saved.id;

  const second = await send();
  const again = await second.json();
  await sleep(2000);
  checks.repeatAcknowledged = second.status === 200 && again.id === saved.id;
  checks.repeatNotAnnounced = received.length === 1 && rows().length === 1;

  const foreign = await fetch(base + "/api/leads", {
    method: "POST", headers: { "content-type": "application/json", origin: "https://example.com" },
    body: JSON.stringify({ ...inquiry, requestId: randomUUID() }),
  });
  await sleep(1000);
  checks.foreignOriginRefused = foreign.status === 403 && received.length === 1 && rows().length === 1;
} catch (error) {
  checks.error = String(error.message || error).slice(0, 300);
} finally {
  if (worker?.pid) {
    try { process.kill(-worker.pid, "SIGTERM"); } catch { /* already gone */ }
  }
  hook?.close();
  await sleep(1500);
  rmSync(state, { recursive: true, force: true });
}

const passed = !checks.error && Object.keys(checks).length === 7 && Object.values(checks).every((value) => value === true);
console.log(JSON.stringify({ passed, ...checks }));
process.exit(passed ? 0 : 1);
