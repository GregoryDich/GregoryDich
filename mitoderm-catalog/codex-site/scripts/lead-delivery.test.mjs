// Checks that a saved inquiry reaches the team: the e-mail and the CRM webhook.
// Run: pnpm test   (node --experimental-strip-types --test scripts/lead-delivery.test.mjs)
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { test } from "node:test";
import { deliverLead, leadEmail } from "../lib/leads-delivery.server.ts";

const labels = {
  received: "הפנייה התקבלה", name: "שם מלא", phone: "טלפון לחזרה",
  profession: "תחום העיסוק", product: "המוצר שנבחר", comment: "מה תרצו לדעת?",
};
const lead = {
  id: "0b6f2c1e-8a44-4c55-9d0e-1f2a3b4c5d6e",
  createdAt: "2026-11-21T12:00:00.000Z",
  name: "דנה לוי",
  phone: "+972501234567",
  profession: "cosmetologist",
  professionLabel: "קוסמטיקאי/ת",
  productSlug: "exosignal-hair",
  productName: "EXOSIGNAL HAIR",
  comment: "מתי אפשר לקבל הדרכה?",
  locale: "he",
  sourceBlock: "contact",
};

/** A fetch stand-in that records every call and answers as told. */
function recorder(answer = () => new Response("{}", { status: 200 })) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init });
    return answer(String(url));
  };
  return { calls, fetchImpl };
}

/** Collects console.warn lines for the duration of a callback. */
async function warnings(run) {
  const original = console.warn;
  const lines = [];
  console.warn = (...parts) => lines.push(parts.join(" "));
  try {
    await run();
  } finally {
    console.warn = original;
  }
  return lines;
}

test("nothing is sent when nothing is configured", async () => {
  const { calls, fetchImpl } = recorder();
  const outcome = await deliverLead(lead, {}, labels, fetchImpl);
  assert.deepEqual(outcome, { email: "skipped", webhook: "skipped" });
  assert.equal(calls.length, 0);
});

test("the e-mail goes to the team with the inquiry in it", async () => {
  const { calls, fetchImpl } = recorder();
  const env = {
    RESEND_API_KEY: "test-key", LEADS_FROM_EMAIL: "site@example.com",
    LEADS_TO_EMAIL: "sales@example.com, owner@example.com",
  };
  const outcome = await deliverLead(lead, env, labels, fetchImpl);
  assert.deepEqual(outcome, { email: "sent", webhook: "skipped" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://api.resend.com/emails");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, "Bearer test-key");
  const mail = JSON.parse(calls[0].init.body);
  assert.equal(mail.from, "site@example.com");
  assert.deepEqual(mail.to, ["sales@example.com", "owner@example.com"]);
  assert.equal(mail.subject, "הפנייה התקבלה · דנה לוי · EXOSIGNAL HAIR");
  assert.ok(mail.text.includes("שם מלא: דנה לוי"));
  assert.ok(mail.text.includes("טלפון לחזרה: ⁦+972501234567⁩"));
  assert.ok(mail.text.includes("WhatsApp: https://wa.me/972501234567"));
  assert.ok(mail.text.includes("תחום העיסוק: קוסמטיקאי/ת"));
  assert.ok(mail.text.includes("המוצר שנבחר: ⁦EXOSIGNAL HAIR⁩"));
  assert.ok(mail.text.includes("מה תרצו לדעת?\nמתי אפשר לקבל הדרכה?"));
  assert.ok(mail.text.includes("0B6F2C1E · 2026-11-21T12:00:00.000Z · contact"));
});

test("an e-mail without a sender or a recipient is not attempted", async () => {
  const { calls, fetchImpl } = recorder();
  const outcome = await deliverLead(lead, { RESEND_API_KEY: "test-key", LEADS_TO_EMAIL: " , " }, labels, fetchImpl);
  assert.equal(outcome.email, "skipped");
  assert.equal(calls.length, 0);
});

test("the webhook carries the inquiry and a valid signature", async () => {
  const { calls, fetchImpl } = recorder();
  const env = { LEADS_WEBHOOK_URL: "https://crm.example.com/hook", LEADS_WEBHOOK_SECRET: "shared-secret" };
  const outcome = await deliverLead(lead, env, labels, fetchImpl);
  assert.deepEqual(outcome, { email: "skipped", webhook: "sent" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://crm.example.com/hook");
  const body = calls[0].init.body;
  const expected = "sha256=" + createHmac("sha256", "shared-secret").update(body).digest("hex");
  assert.equal(calls[0].init.headers["x-mitoderm-signature"], expected);
  const payload = JSON.parse(body);
  assert.equal(payload.source, "mitoderm-site");
  assert.deepEqual(payload.lead, lead);
});

test("a webhook without a secret is sent unsigned", async () => {
  const { calls, fetchImpl } = recorder();
  await deliverLead(lead, { LEADS_WEBHOOK_URL: "https://crm.example.com/hook" }, labels, fetchImpl);
  assert.equal(calls[0].init.headers["x-mitoderm-signature"], undefined);
});

test("contact details never leave over plain HTTP, except to a local test", async () => {
  const remote = recorder();
  const lines = await warnings(async () => {
    const outcome = await deliverLead(lead, { LEADS_WEBHOOK_URL: "http://crm.example.com/hook" }, labels, remote.fetchImpl);
    assert.equal(outcome.webhook, "failed");
  });
  assert.equal(remote.calls.length, 0);
  assert.equal(lines.length, 1);
  const local = recorder();
  const outcome = await deliverLead(lead, { LEADS_WEBHOOK_URL: "http://127.0.0.1:8792/hook" }, labels, local.fetchImpl);
  assert.equal(outcome.webhook, "sent");
  const bad = recorder();
  await warnings(async () => {
    assert.equal((await deliverLead(lead, { LEADS_WEBHOOK_URL: "not an address" }, labels, bad.fetchImpl)).webhook, "failed");
  });
  assert.equal(bad.calls.length, 0);
});

test("a failing service never throws and never logs the inquiry", async () => {
  const env = {
    RESEND_API_KEY: "test-key", LEADS_FROM_EMAIL: "site@example.com", LEADS_TO_EMAIL: "sales@example.com",
    LEADS_WEBHOOK_URL: "https://crm.example.com/hook",
  };
  const refusing = recorder((url) => new Response("no", { status: url.includes("resend") ? 500 : 403 }));
  let lines = await warnings(async () => {
    assert.deepEqual(await deliverLead(lead, env, labels, refusing.fetchImpl), { email: "failed", webhook: "failed" });
  });
  const broken = async () => { throw new Error("network down: " + lead.phone); };
  lines = lines.concat(await warnings(async () => {
    assert.deepEqual(await deliverLead(lead, env, labels, broken), { email: "failed", webhook: "failed" });
  }));
  assert.equal(lines.length, 4);
  for (const line of lines) {
    assert.ok(!line.includes(lead.phone) && !line.includes(lead.name) && !line.includes("test-key"), line);
  }
});

test("one channel failing does not stop the other", async () => {
  const env = {
    RESEND_API_KEY: "test-key", LEADS_FROM_EMAIL: "site@example.com", LEADS_TO_EMAIL: "sales@example.com",
    LEADS_WEBHOOK_URL: "https://crm.example.com/hook",
  };
  const mixed = recorder((url) => new Response("{}", { status: url.includes("resend") ? 500 : 200 }));
  await warnings(async () => {
    assert.deepEqual(await deliverLead(lead, env, labels, mixed.fetchImpl), { email: "failed", webhook: "sent" });
  });
});

test("direction-override characters in a comment cannot reorder the e-mail", () => {
  const { text } = leadEmail({ ...lead, comment: "abc‮def⁦ghi⁩" }, labels);
  assert.ok(text.includes("\nabcdefghi\n"));
});

test("an inquiry without a comment has no empty comment block", () => {
  const { text } = leadEmail({ ...lead, comment: "" }, labels);
  assert.ok(!text.includes("מה תרצו לדעת?"));
});
