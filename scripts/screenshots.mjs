// Programmatic doc screenshots of datasette-town → docs/screenshots/*.png.
//
// SELF-CONTAINED (modelled on datasette-sheets' `shots`): this boots its own
// throwaway datasette on a fixed port with a fresh internal + data DB, lets the
// shot-plugin seed a deterministic demo `sales` table + a set of town queries
// with acl grants (alice owns several; one is shared to alice by bob; the
// headline query is shared to bob/carol/public), drives Playwright, then tears
// the server down. One command, reproducible — so the committed PNGs only
// change when the UI actually changes (clean git diffs).
//
// Output is committed; the README embeds these, so re-run + commit when the
// list / detail / share dialog look changes:  `just shots`  (or a subset, e.g.
// `just shots town-list share-dialog`).
import { chromium } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { mkdir, rm } from "node:fs/promises";
import { spawn, execFileSync } from "node:child_process";

const PORT = Number(process.env.SHOTS_PORT || 8489);
const BASE = `http://localhost:${PORT}`;
const DB_NAME = "data";
const TOWN = `${BASE}/${DB_NAME}/-/town`;
// Fixed signing secret — lets us mint signed actor cookies so the seeded
// queries are owned/shared as expected. NOT a real secret.
const SECRET = "screenshots-secret-not-for-prod";
const INTERNAL_DB = "/tmp/datasette-town-shots-internal.db";
// The directory name makes the Datasette database name "data" (matches DB_NAME).
const DATA_DIR = "/tmp/datasette-town-shots-data";
const DATA_DB = `${DATA_DIR}/${DB_NAME}.db`;

const HERE = dirname(fileURLToPath(import.meta.url));
const PLUGINS_DIR = resolve(HERE, "shot-plugins");
const OUT = resolve(HERE, "../docs/screenshots");

const HEADLINE_TITLE = "Revenue by region";
const VIEWPORT = { width: 1000, height: 820 };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------------------
// Signed ds_actor cookie for an actor id. itsdangerous has no maintained Node
// port, so shell out to a one-liner. Cached per id.
const _signed = new Map();
function signActorCookie(actorId) {
  let v = _signed.get(actorId);
  if (!v) {
    const out = execFileSync(
      "uv",
      [
        "run",
        "python",
        "-c",
        "import sys, json; from itsdangerous import URLSafeSerializer; " +
          'print(URLSafeSerializer(sys.argv[1]).dumps(json.loads(sys.argv[2]), salt="actor"))',
        SECRET,
        JSON.stringify({ a: { id: actorId } }),
      ],
      { encoding: "utf-8" },
    );
    v = out.trim();
    _signed.set(actorId, v);
  }
  return v;
}

// ---------------------------------------------------------------------------
async function reachable() {
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 500);
    const r = await fetch(TOWN, { redirect: "manual", signal: ac.signal });
    clearTimeout(t);
    return r.status < 500;
  } catch {
    return false;
  }
}

// Create an empty (but valid) sqlite file so datasette opens it mutable and the
// shot-plugin's startup seed can write the demo table into it.
function setupDataDb() {
  const py = `
import os, sqlite3
os.makedirs(${JSON.stringify(DATA_DIR)}, exist_ok=True)
p = ${JSON.stringify(DATA_DB)}
if os.path.exists(p): os.remove(p)
sqlite3.connect(p).close()
`;
  execFileSync("uv", ["run", "python", "-c", py]);
}

async function startServer() {
  await rm(INTERNAL_DB, { force: true });
  setupDataDb();
  if (await reachable()) {
    throw new Error(
      `something is already serving on ${BASE}. Stop it (or set SHOTS_PORT) and retry.`,
    );
  }
  // `detached: true` puts datasette in its own process group. datasette is a
  // grandchild of `uv run`, so we kill the whole group in stopServer.
  const child = spawn(
    "uv",
    [
      "run",
      "datasette",
      "--internal",
      INTERNAL_DB,
      DATA_DB,
      "--secret",
      SECRET,
      // Throwaway plugin: friendly actor names + seeds demo queries/grants.
      "--plugins-dir",
      PLUGINS_DIR,
      // Coarse instance gates open for everyone; per-query acl does the rest.
      "-s",
      "permissions.datasette-town-access",
      "true",
      "-s",
      "permissions.datasette-town-create",
      "true",
      "-p",
      String(PORT),
    ],
    { stdio: ["ignore", "pipe", "pipe"], detached: true },
  );
  let log = "";
  child.stdout.on("data", (d) => (log += d));
  child.stderr.on("data", (d) => (log += d));

  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`datasette exited early (code ${child.exitCode}):\n${log}`);
    }
    if (await reachable()) return child;
    await sleep(250);
  }
  stopServer(child);
  throw new Error(`datasette never came up on ${BASE}:\n${log}`);
}

// Kill the server's whole process group (datasette is uv's child). Idempotent.
function stopServer(child) {
  if (!child || child.exitCode !== null) return;
  try {
    process.kill(-child.pid, "SIGKILL");
  } catch {
    try {
      child.kill("SIGKILL");
    } catch {
      // already gone
    }
  }
}

// ---------------------------------------------------------------------------
// Per-page stabilization: kill carets / transitions and hide dev-only widgets
// so a re-run with no UI change produces no binary diff.
const STABILITY_CSS = `*, *::before, *::after {
  caret-color: transparent !important;
  transition: none !important;
  animation: none !important;
}
#datasette-debug-bar { display: none !important; }`;

async function freezeVolatile(page) {
  await page.evaluate(() => {
    // Relative "Updated …" timestamps move every run.
    document
      .querySelectorAll(".timestamp")
      .forEach((el) => (el.textContent = "Updated just now"));
    document.getElementById("datasette-debug-bar")?.remove();
  });
}

async function makeContext(browser, actorId) {
  const ctx = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 2 });
  await ctx.addInitScript((css) => {
    const inject = () => {
      if (document.getElementById("__shots_stability")) return;
      const s = document.createElement("style");
      s.id = "__shots_stability";
      s.textContent = css;
      (document.head || document.documentElement).appendChild(s);
    };
    inject();
    document.addEventListener("DOMContentLoaded", inject);
  }, STABILITY_CSS);
  await ctx.addCookies([
    { name: "ds_actor", value: signActorCookie(actorId), domain: "localhost", path: "/" },
  ]);
  return ctx;
}

// Resolve the headline query's id via the profile-queries JSON API (alice owns
// it).
async function findQueryId(ctx, title) {
  const r = await ctx.request.get(
    `${BASE}/-/town/api/profile_queries?actorId=alice`,
  );
  if (!r.ok()) throw new Error(`profile_queries failed: ${r.status()}`);
  const { data } = await r.json();
  const q = (data || []).find((row) => row.title === title);
  if (!q) {
    throw new Error(
      `seeded query "${title}" not found (have: ${(data || []).map((d) => d.title).join(", ")})`,
    );
  }
  return q.id;
}

async function gotoQuery(page, queryId) {
  await page.goto(`${TOWN}/q/${queryId}`);
  await page.locator(".query-detail").waitFor({ state: "visible", timeout: 20_000 });
  // Direct child only: the share dialog also renders an (h2) title nested deeper
  // inside .title-row > .title-actions.
  await page.locator(".title-row > h2").waitFor({ timeout: 15_000 });
}

// ---------------------------------------------------------------------------
function buildShots(browser, headlineId) {
  const out = (n) => resolve(OUT, `${n}.png`);

  return {
    // The query list: My Queries + Shared with Me, populated via acl grants.
    "town-list": async () => {
      const ctx = await makeContext(browser, "alice");
      const page = await ctx.newPage();
      await page.goto(TOWN);
      await page.locator(".query-card").first().waitFor({ timeout: 15_000 });
      // Both sections present (alice owns queries; bob shared one to her).
      await page.getByText("My Queries").waitFor({ timeout: 15_000 });
      await page.getByText("Shared with Me").waitFor({ timeout: 15_000 });
      await freezeVolatile(page);
      await page.screenshot({ path: out("town-list") });
      await ctx.close();
    },

    // The new-query form with the SQL editor.
    "new-query": async () => {
      const ctx = await makeContext(browser, "alice");
      const page = await ctx.newPage();
      await page.goto(`${TOWN}/new`);
      await page.locator(".new-query").waitFor({ state: "visible", timeout: 15_000 });
      await page.locator(".cm-editor").waitFor({ timeout: 15_000 });
      await freezeVolatile(page);
      await page.screenshot({ path: out("new-query") });
      await ctx.close();
    },

    // A single query: title, author, SQL, and the owner-only Share button.
    "query-detail": async () => {
      const ctx = await makeContext(browser, "alice");
      const page = await ctx.newPage();
      await gotoQuery(page, headlineId);
      await page.locator(".cm-editor").first().waitFor({ timeout: 15_000 });
      // Share trigger (from <datasette-acl-share-dialog>) confirms owner view.
      await page
        .getByRole("button", { name: new RegExp(`^Share\\b`) })
        .waitFor({ timeout: 15_000 });
      await freezeVolatile(page);
      await page.screenshot({ path: out("query-detail") });
      await ctx.close();
    },

    // Same query after pressing Execute: the results table.
    "query-results": async () => {
      const ctx = await makeContext(browser, "alice");
      const page = await ctx.newPage();
      await gotoQuery(page, headlineId);
      await page.getByRole("button", { name: "Execute" }).click();
      await page.locator(".results-wrapper table tbody tr").first().waitFor({
        timeout: 15_000,
      });
      await freezeVolatile(page);
      await page.screenshot({ path: out("query-results") });
      await ctx.close();
    },

    // The datasette-acl-share dialog, open, with the people-with-access list
    // (alice owner, bob Editor, carol Viewer) + the public toggle.
    "share-dialog": async () => {
      const ctx = await makeContext(browser, "alice");
      const page = await ctx.newPage();
      await gotoQuery(page, headlineId);
      await page.getByRole("button", { name: new RegExp(`^Share\\b`) }).click();
      const dialog = page.locator("dialog[open]");
      await dialog.waitFor({ state: "visible", timeout: 15_000 });
      await page.getByText("People with access").waitFor({ timeout: 15_000 });
      // Let the grant list finish loading its rows.
      await sleep(500);
      await freezeVolatile(page);
      const box = await dialog.boundingBox();
      if (box) {
        const pad = 16;
        await page.screenshot({
          path: out("share-dialog"),
          clip: {
            x: Math.max(0, box.x - pad),
            y: Math.max(0, box.y - pad),
            width: Math.min(VIEWPORT.width, box.width + pad * 2),
            height: Math.min(VIEWPORT.height, box.height + pad * 2),
          },
        });
      } else {
        await page.screenshot({ path: out("share-dialog") });
      }
      await ctx.close();
    },
  };
}

// ---------------------------------------------------------------------------
async function main() {
  const requested = new Set(process.argv.slice(2));

  await mkdir(OUT, { recursive: true });
  console.log(`booting datasette on ${BASE} …`);
  const server = await startServer();
  const onSignal = () => {
    stopServer(server);
    process.exit(130);
  };
  process.once("SIGINT", onSignal);
  process.once("SIGTERM", onSignal);

  const browser = await chromium.launch();
  try {
    const discoverCtx = await makeContext(browser, "alice");
    const headlineId = await findQueryId(discoverCtx, HEADLINE_TITLE);
    await discoverCtx.close();

    const shotsByName = buildShots(browser, headlineId);
    const names = Object.keys(shotsByName);
    const unknown = [...requested].filter((n) => !names.includes(n));
    if (unknown.length) {
      throw new Error(`unknown shot(s): ${unknown.join(", ")} (have: ${names.join(", ")})`);
    }
    const todo = requested.size ? names.filter((n) => requested.has(n)) : names;

    for (const name of todo) {
      await shotsByName[name]();
      console.log(`✓ ${name} → ${resolve(OUT, name + ".png")}`);
    }
  } finally {
    await browser.close();
    stopServer(server);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
