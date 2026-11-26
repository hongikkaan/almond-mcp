const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const { mkdirSync, mkdtempSync, rmSync } = require("node:fs");
const path = require("node:path");
const { createInterface } = require("node:readline");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const repo = path.resolve(__dirname, "../../../..");

async function checkJourney(page, { url, plan, step, phase }) {
  page.setDefaultTimeout(8_000);
  await page.goto(url);
  const tabs = page.getByRole("navigation", { name: "조회 대상" });
  const taskTab = tabs.getByRole("button", { name: /Task$/ });
  await taskTab.click();

  const phasePicker = page.getByRole("combobox", { name: "Phase", exact: true });
  await page.locator("#task-filters > summary").click();
  await phasePicker.selectOption(phase);
  const taskPicker = page.getByRole("combobox", { name: "Task 선택" });
  await taskPicker.selectOption(plan);
  const card = page.locator(`[data-task-group="${plan}"] > .task-card`);
  await card.getByText("새 입구 검토", { exact: true }).waitFor();

  await tabs.getByRole("button", { name: /Scene 조회$/ }).click();
  await taskTab.click();
  await page.reload();
  await card.getByText("새 입구 검토", { exact: true }).waitFor();
  assert.equal(await phasePicker.inputValue(), phase);
  assert.equal(await taskPicker.inputValue(), plan);

  await card.getByRole("button", { name: "이전 회차" }).click();
  await card.getByText("기존 입구 검토", { exact: true }).waitFor();
  const panel = card.locator(`[data-step-id="${step}"]`);
  await panel.locator("summary").click();
  await panel.getByRole("button", { name: /Step 전체 기록/ }).click();
  const detail = page.getByRole("dialog");
  await detail.getByText("drawings/old.pdf", { exact: true }).waitFor();
  await page.keyboard.press("Escape");
  await detail.waitFor({ state: "hidden" });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
}

async function main() {
  const data = path.join(repo, "data");
  mkdirSync(data, { recursive: true });
  const scratch = mkdtempSync(path.join(data, "dashboard-"));
  const python = process.env.DASHBOARD_TEST_PYTHON ||
    path.join(repo, "data", "development", ".venv", "Scripts", "python.exe");
  const fixture = spawn(python, [
    "-B", "-X", "utf8", path.join(__dirname, "dashboard_sample.py"), path.join(scratch, "design.sqlite3"),
  ], {
    stdio: ["pipe", "pipe", "inherit"],
    env: { ...process.env, PYTHONPATH: [path.resolve(__dirname, "../../runtime"), process.env.PYTHONPATH]
      .filter(Boolean).join(path.delimiter) },
  });
  const closed = once(fixture, "close");
  const lines = createInterface({ input: fixture.stdout });
  let browser;
  try {
    const [line] = await Promise.race([
      once(lines, "line", { signal: AbortSignal.timeout(15_000) }),
      closed.then(([code]) => { throw new Error(`Dashboard fixture exited with code ${code}`); }),
    ]);
    browser = await chromium.launchPersistentContext(path.join(scratch, "profile"), {
      channel: "chrome", viewport: { width: 360, height: 760 },
    });
    await checkJourney(browser.pages()[0], JSON.parse(line));
    console.log("Dashboard filter restoration and historical Step passed.");
  } finally {
    if (!fixture.stdin.destroyed) {
      fixture.stdin.end();
    }
    const results = await Promise.allSettled([browser?.close(), closed]);
    lines.close();
    rmSync(scratch, { recursive: true, force: true });
    for (const result of results) {
      if (result.status === "rejected") {
        throw result.reason;
      }
    }
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
