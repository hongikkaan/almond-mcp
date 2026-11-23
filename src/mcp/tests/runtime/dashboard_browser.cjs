// Run with PLAYWRIGHT_MODULE pointing to a development-only Playwright install.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const path = require("node:path");
const assert = require("node:assert/strict");

async function checkPlanOutline(page, url) {
  const entry = (id, root = page) => root.locator(`[data-plan-entry="${id}"]`);
  const outline = page.locator("#task-outline");
  const root = entry("outline_root", outline);
  const next = entry("outline_next", outline);
  const branch = entry("outline_branch", outline);
  await page.goto(url);
  await root.waitFor();
  const firstBox = await root.boundingBox();
  const nextBox = await next.boundingBox();
  assert(firstBox.x + firstBox.width <= nextBox.x, "A saved successor is right of its predecessor");
  assert.equal((await branch.boundingBox()).x, nextBox.x, "Branches share the successor column");
  assert.equal(await next.locator(".plan-sequence-arrow").textContent(), "→");
  assert.equal(await entry("outline_loose", outline).locator(".plan-previous").count(), 0);
  await entry("outline_cycle_a", outline).first().waitFor();
  await entry("outline_cycle_b", outline).first().waitFor();
  assert.equal(await outline.getByText("표시할 수 없는 상위 참조 있음").count() > 0, true);

  const children = root.locator(":scope > ul > li");
  assert.deepEqual(await children.evaluateAll((items) => items.map((item) => item.dataset.planEntry)),
    ["outline_child_a", "outline_child_b"]);
  assert.equal(await root.locator("[data-outline-plan='outline_leaf']").count(), 2,
    "A shared child is selectable from both parents");
  assert.equal(await entry("outline_child_b", root).locator(":scope > .plan-previous .plan-sibling-arrow").textContent(), "↑");

  await page.setViewportSize({ width: 360, height: 850 });
  await page.waitForFunction(() => {
    const element = document.querySelector("#task-outline .plan-sequence-arrow");
    return element && getComputedStyle(element).transform !== "none";
  });
  assert((await next.boundingBox()).y > (await root.boundingBox()).y,
    "A narrow screen stacks the same sequence without clipping");
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    "A narrow screen must not gain horizontal page overflow");

  const filters = page.locator("#task-filters");
  if (!(await filters.evaluate((detail) => detail.open))) await filters.locator("summary").click();
  const options = await page.locator("#filter-status option").evaluateAll((items) => items.map((item) => item.value));
  assert.deepEqual(new Set(options), new Set(["", "pending", "running", "paused", "completed", "failed", "blocked"]));
  await page.locator("#filter-file").selectOption("other.3dm");
  await page.locator("#filter-status").selectOption("pending");
  await page.locator("#filter-execution").selectOption("unstarted");
  await page.locator("#task-count").getByText("1개").waitFor();
  await root.getByText("상위 맥락 · example.3dm", { exact: true }).waitFor();
  assert.equal(await entry("outline_pending", outline).count(), 0);
  assert.equal(await entry("outline_legacy", outline).count(), 0);
  assert.equal(await entry("outline_next", outline).count(), 0);
  const leaf = outline.locator("[data-outline-plan='outline_leaf']").first();
  await leaf.press("Enter");
  await page.locator("[data-task-group='outline_leaf']").waitFor();
  assert.equal(await leaf.getAttribute("aria-current"), "true");

  await page.locator('[data-view="files"]').click();
  const file = page.locator("tr").filter({ has: page.getByRole("button", { name: "other.3dm", exact: true }) });
  await file.getByText("7개 Task", { exact: true }).waitFor();
  await entry("outline_root", file).getByText("상위 맥락 · example.3dm", { exact: true }).waitFor();
  assert.equal(await entry("outline_next", file).count(), 0);
  assert.equal(await entry("outline_leaf", file).count(), 2);
  await file.locator("[data-outline-plan='outline_child_b']").press("Enter");
  await page.locator("[data-task-group='outline_child_b']").waitFor();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  console.log("Plan outline browser passed: branching, depth, shared child, file context, status and keyboard selection.");
}

async function checkLoopHistory(page, url) {
  await page.setViewportSize({ width: 360, height: 760 });
  await page.goto(url);
  await page.locator('#task-select option[value="plan_a"]').waitFor({ state: "attached" });
  await page.locator("#task-select").selectOption("plan_a");
  const card = page.locator('[data-task-group="plan_a"] > .task-card');
  const picker = card.getByLabel("조회할 회차");
  await picker.waitFor();
  assert.deepEqual(await picker.locator("option").evaluateAll(items => items.map(i => i.value)), ["0", "1", "3", "4"]);
  assert.equal(await picker.inputValue(), "4");
  assert(await card.getByRole("button", { name: "다음 회차" }).isDisabled());
  await card.getByRole("button", { name: "이전 회차" }).click();
  await card.getByText("feedback only", { exact: true }).waitFor();
  assert((await card.innerText()).includes("일부 기록"));
  assert(!(await card.innerText()).includes("current decision"));
  await card.getByRole("button", { name: "이전 회차" }).click();
  await card.getByRole("button", { name: "Old title" }).click();
  await page.locator("#detail").getByText("Original goal", { exact: true }).waitFor();
  await page.keyboard.press("Escape");
  const step = card.locator('[data-step-id="archived_step"]');
  await step.locator("summary").click();
  await step.getByRole("button", { name: /Step 전체 기록/ }).click();
  await page.locator("#detail").getByText("previous/deleted.png", { exact: true }).waitFor();
  assert((await page.locator("#detail").innerText()).includes("decision 2"));
  await page.keyboard.press("Escape");
  const longStep = card.locator('[data-step-id="z_first"]');
  await longStep.locator("summary").click();
  await longStep.getByText("old/first.png", { exact: true }).waitFor();
  assert((await longStep.innerText()).includes("일부 표시"));
  assert(!(await card.innerText()).includes("current/new.png"));
  assert(!(await card.innerText()).includes("일부 기록"));
  await longStep.getByRole("button", { name: /Step 전체 기록/ }).click();
  await page.locator("#detail").getByText("old/first.png", { exact: true }).waitFor();
  assert(!(await page.locator("#detail").innerText()).includes("current/new.png"));
  await page.keyboard.press("Escape");
  await picker.selectOption("0");
  await card.locator('[data-step-id="z_first"]').waitFor();
  assert(await card.getByRole("button", { name: "이전 회차" }).isDisabled());
  assert.equal(await picker.locator("option:checked").textContent(), "실행 전 기록 (0)");
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));

  // Hold an old Loop response until the newer selection has rendered.
  for (const switchPlan of [false, true]) {
    let resume, started;
    const gate = new Promise(resolve => { resume = resolve; });
    const pending = new Promise(resolve => { started = resolve; });
    const match = u => u.pathname === "/api/domain" && u.searchParams.get("loop_no") === "1";
    await page.route(match, async route => {
      const response = await route.fetch();
      started();
      await gate;
      await route.fulfill({ response });
    });
    await picker.selectOption("1");
    await pending;
    if (switchPlan) {
      await page.locator("#task-select").selectOption("plan_b");
      await page.locator('[data-task-group="plan_b"]').waitFor();
    } else {
      await picker.selectOption("4");
      await card.getByText("current feedback", { exact: true }).waitFor({ state: "visible" });
      await page.waitForFunction(() => !document.querySelector('[data-task-id="plan_a"]').hasAttribute("aria-busy"));
    }
    const received = page.waitForResponse(response => match(new URL(response.url())));
    resume();
    await received;
    await page.unroute(match);
    await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
    assert.equal(await page.locator('[data-task-id="plan_a"][data-loop="1"]').count(), 0);
  }
  await page.locator("#task-select").selectOption("plan_a");
  await picker.waitFor();
  assert.equal(await picker.inputValue(), "4");
  await longStep.locator("summary").click();
  await longStep.getByText("current/new.png", { exact: true }).waitFor();
  await longStep.getByRole("button", { name: /Step 전체 기록/ }).click();
  await page.locator("#detail").getByText("current/new.png", { exact: true }).waitFor();
  assert(!(await page.locator("#detail").innerText()).includes("old/first.png"));
  console.log("Loop history browser passed: revisions, partial rows, Loop 0, popups, gaps, boundaries and delayed responses.");
}

(async () => {
  const root = path.resolve(__dirname, "../../../..");
  const outlineOnly = process.argv.includes("--plan-outline");
  const loopOnly = process.argv.includes("--loop-history");
  const child = spawn(
    path.join(root, "data/development/.venv/Scripts/python.exe"),
    ["-B", "-X", "utf8", path.join(__dirname, "dashboard_ui_host.py"),
      ...process.argv.slice(2)],
    { cwd: root, windowsHide: true },
  );
  let browser;
  try {
    const url = await new Promise((resolve, reject) => {
      let output = "";
      child.stdout.on("data", (chunk) => {
        output += chunk;
        if (output.includes("\n")) resolve(output.split("\n")[0].trim());
      });
      child.stderr.on("data", (chunk) => process.stderr.write(chunk));
      child.once("exit", (code) => reject(new Error(`Fixture exited ${code}`)));
    });
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1050 },
    });
    const errors = [];
    if (outlineOnly || loopOnly) {
      page.on("pageerror", (error) => errors.push(error.message));
      if (loopOnly) await checkLoopHistory(page, url);
      else await checkPlanOutline(page, url);
      assert.deepEqual(errors, []);
      return;
    }
    const chooseTask = async (id) => {
      await page
        .locator(`#task-select option[value="${id}"]`)
        .waitFor({ state: "attached" });
      await page.locator("#task-select").selectOption(id);
      await page.locator(`[data-task-group="${id}"] > .task-card`).waitFor();
      assert.equal(
        await page.locator("#domain-results > .task-group").count(),
        1,
        "Task dropdown should render one selected Task",
      );
    };
    const assertTaskOrder = async (card, width) => {
      const header = card.locator(".task-heading");
      assert.equal(
        await header.locator(".task-phase").count(),
        1,
        "Phase belongs in the Task header",
      );
      const phase = await header.locator(".task-phase").boundingBox();
      const file = await header.locator(".task-files").boundingBox();
      const title = await header.locator("h2").boundingBox();
      const identity = await header.locator(".task-identity").boundingBox();
      const meta = await header.locator(".task-meta").boundingBox();
      assert(
        phase &&
          file &&
          title &&
          phase.y + phase.height <= file.y + 1 &&
          file.y + file.height <= title.y + 1,
        `Task header must read Phase, file, title at ${width}px`,
      );
      assert(
        identity.x + identity.width <= meta.x + 1 &&
          meta.x + meta.width <= width + 1,
        `Task identity overlaps right metadata at ${width}px`,
      );
    };
    page.on("pageerror", (error) => errors.push(error.message));
    let releaseOptions;
    const optionsGate = new Promise((resolve) => {
      releaseOptions = resolve;
    });
    await page.route("**/api/domain-options?*", async (route) => {
      await optionsGate;
      const response = await route.fetch();
      const options = await response.json();
      options.notes = ["필터 목록은 처음 2000개만 표시합니다."];
      await route.fulfill({ response, json: options });
    });
    await page.goto(url);
    await page.locator('[data-view="files"]').waitFor();
    await page.locator('[data-view="scenes"]:enabled').click();
    releaseOptions();
    await page
      .locator('#filter-phase option[value="phase_a"]')
      .waitFor({ state: "attached" });
    await page
      .getByText("필터 목록은 처음 2000개만 표시합니다.", { exact: false })
      .waitFor();
    assert.equal(await page.locator("[data-view]").count(), 6);
    assert.equal(
      await page.locator(".brand").count(),
      0,
      "Remove the redundant Dashboard logo row",
    );
    assert.equal(
      await page.locator(".topbar #domain-title").count(),
      1,
      "Move the view title into the compact top bar",
    );
    assert.equal(
      await page
        .locator('#tables,#folded-tables,#show-internal,[data-view="tables"]')
        .count(),
      0,
    );
    await page.locator('[data-view="tasks"]').click();
    assert.equal(
      await page.locator("#task-select").count(),
      1,
      "Task needs its own selection dropdown",
    );
    await chooseTask("plan_a");
    await page.locator('[data-task-id="plan_a"]').waitFor();
    const selectedPlan = page.locator('[data-task-group="plan_a"]');
    assert.deepEqual((await selectedPlan.locator(":scope > .task-card .relation-type").allTextContents()).sort(),
      ["관련 Plan", "직전 Plan"]);
    assert.deepEqual((await selectedPlan.locator(":scope > .adjacent-tasks > label select option").allTextContents())
      .map((label) => label.split(" · ")[0]).sort(), ["관련 Plan", "직전 Plan"]);
    const step = page.locator(
      '[data-task-group="plan_a"] > .task-card details[data-step-id="z_first"]',
    );
    await step.locator("summary").click();
    await step.locator("pre").getByText("판단 기록", { exact: true }).waitFor();
    await step.locator("pre").getByText("설계 근거", { exact: true }).waitFor();
    assert.deepEqual(
      await step.locator(".step-body section h3").allTextContents(),
      ["takeaways", "design_rationale", "input_refs_json", "output_refs_json"],
      "Step fields should keep their stored names",
    );
    const outputs = step
      .locator(".step-body section")
      .filter({ has: page.getByText("output_refs_json", { exact: true }) });
    assert.equal(
      await outputs.locator(".stored-value > ul").count(),
      1,
      "Step references should be a readable list",
    );
    assert((await outputs.innerText()).includes("검토 자료"));
    assert.equal(
      await outputs
        .getByRole("link", {
          name: "https://example.com/record?id=3",
          exact: true,
        })
        .getAttribute("href"),
      "https://example.com/record?id=3",
    );
    assert(
      (
        await outputs
          .locator("a")
          .evaluateAll((links) =>
            links.map((link) => link.getAttribute("href")),
          )
      ).includes("https://example.com/report?range=[1,2]"),
      "Reference URL brackets must be preserved",
    );
    assert.equal(
      await step.locator(".step-meta").count(),
      1,
      "Step loop/kind metadata should be separate from its fields",
    );
    await step
      .locator(".step-kind")
      .getByText("kind · reason", { exact: true })
      .waitFor();
    const fieldAppearance = await step
      .locator(".step-body section")
      .first()
      .evaluate((field) => ({
        size: parseFloat(getComputedStyle(field.querySelector("h3")).fontSize),
        weight: parseInt(
          getComputedStyle(field.querySelector("h3")).fontWeight,
        ),
        background: getComputedStyle(field.querySelector(".stored-value"))
          .backgroundColor,
      }));
    assert(
      fieldAppearance.size >= 14 &&
        fieldAppearance.weight >= 700 &&
        fieldAppearance.background === "rgb(255, 255, 255)",
      "Fields need large bold names and white value boxes",
    );
    const stepKind = await step.locator(".step-kind").boundingBox(),
      stepId = await step.locator(".identity").boundingBox();
    assert(
      stepKind.x < stepId.x,
      "Step kind and step_id should exchange sides",
    );
    const taskHeader = page.locator(
      '[data-task-group="plan_a"] > .task-card .task-heading',
    );
    assert(
      await taskHeader
        .locator(".task-loop")
        .evaluate((node) => parseFloat(getComputedStyle(node).fontSize) >= 20),
      "Task LOOP must be prominent",
    );
    const taskStatus = await taskHeader.locator(".status-label").boundingBox(),
      taskLoop = await taskHeader.locator(".task-loop").boundingBox();
    const taskRev = await taskHeader.locator(".task-revision").boundingBox();
    assert(
      taskStatus.y < taskLoop.y && taskRev.y < taskLoop.y,
      "Task should use accepted layout B",
    );
    await assertTaskOrder(
      page.locator('[data-task-group="plan_a"] > .task-card'),
      1440,
    );
    await page.locator('[data-view="scenes"]').click();
    await page.locator('[data-view="tasks"]').click();
    assert.equal(await step.getAttribute("open"), "");
    await page.locator("#filter-phase").selectOption("phase_b");
    await page.locator('[data-task-id="plan_c"]').waitFor();
    assert.equal(await page.locator('[data-task-id="plan_a"]').count(), 0);
    await page.reload();
    await page.locator('[data-task-id="plan_c"]').waitFor();
    assert.equal(await page.locator("#filter-phase").inputValue(), "phase_b");
    await page.locator('[data-view="scenes"]').click();
    await page
      .locator("tbody tr")
      .filter({ hasText: "진입 장면" })
      .getByRole("button", { name: "공간 설계", exact: true })
      .first()
      .click();
    await page.locator('[data-task-id="plan_a"]').first().waitFor();
    assert.equal(
      await page.locator("#task-count").textContent(),
      "직접 선택",
      "A linked Task outside stored filters should not show a misleading dropdown count",
    );
    assert.equal(await page.locator("#filter-phase").inputValue(), "phase_b");
    await page.locator("#domain-show-all").click();
    await page.locator('[data-task-id="plan_c"]').first().waitFor();
    await page.locator("#filter-phase").selectOption("");
    await chooseTask("plan_a");
    await page
      .locator(
        '[data-task-group="plan_a"] .adjacent-tasks [data-task-id="plan_b"]',
      )
      .waitFor();
    const mainStep = page.locator(
      '[data-task-group="plan_b"] > .task-card details[data-step-id="b_first"]',
    );
    const adjacentStep = page.locator(
      '[data-task-group="plan_a"] .adjacent-tasks details[data-step-id="b_first"]',
    );
    await chooseTask("plan_b");
    await mainStep.locator("summary").click();
    await chooseTask("plan_a");
    await adjacentStep.locator("summary").click();
    await adjacentStep.locator("summary").click();
    await page.locator('[data-view="scenes"]').click();
    await page.locator('[data-view="tasks"]').click();
    assert.equal(await adjacentStep.getAttribute("open"), null);
    await chooseTask("plan_b");
    assert.equal(await mainStep.getAttribute("open"), "");
    await chooseTask("plan_a");
    await page
      .locator('[data-task-group="plan_a"] .adjacent-tasks')
      .getByText("Task 소속 Step: 처음 200개만 표시합니다.", { exact: false })
      .waitFor();
    await page.locator('[data-task-id="plan_a"] [data-detail]').first().click();
    await page.locator("#detail[open]").waitFor();
    await page.locator("#detail h2").click();
    assert.equal(await page.locator("#detail[open]").count(), 1);
    await page.mouse.click(5, 5);
    await page.locator("#detail[open]").waitFor({ state: "hidden" });
    for (const view of ["files", "scenes", "holons", "phases", "steps"]) {
      await page.locator(`[data-view="${view}"]`).click();
      await page.locator("#domain-results > *").first().waitFor();
    }
    await page.setViewportSize({ width: 650, height: 720 });
    await page.locator('[data-view="files"]').click();
    await page.locator("#domain-results tbody tr").first().waitFor();
    assert.equal(
      await page
        .locator(".table-scroll")
        .evaluate((table) => table.scrollWidth <= table.clientWidth + 1),
      true,
      "Docked File context requires horizontal scrolling to read its fields",
    );
    await page.locator('[data-view="tasks"]').click();
    assert.equal(
      await page.locator("#filter-phase").isVisible(),
      false,
      "Dock filters should initially leave room for Task content",
    );
    const comparison = page.locator(
      '[data-task-group="plan_a"] > .adjacent-tasks',
    );
    await comparison.waitFor();
    assert.equal(
      await comparison.evaluate((panel) =>
        panel.matches("details:not([open])"),
      ),
      true,
      "A new dock comparison should leave room to read the selected Task",
    );
    await comparison.locator(":scope > summary").click();
    await comparison.locator('[data-task-id="plan_b"]').waitFor();
    await page.locator('[data-view="scenes"]').click();
    await page.locator('[data-view="tasks"]').click();
    assert.equal(
      await comparison.getAttribute("open"),
      "",
      "Dock comparison expansion was lost during navigation",
    );
    for (const width of [650, 480, 320]) {
      await page.setViewportSize({ width, height: 720 });
      for (const view of [
        "files",
        "scenes",
        "holons",
        "phases",
        "steps",
        "tasks",
      ]) {
        await page.locator(`[data-view="${view}"]`).click();
        await page.locator("#domain-results > *").first().waitFor();
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
          true,
          `${view} overflows the ${width}px dock`,
        );
        for (const selector of [
          "#view-tabs",
          "#domain-search",
          "#domain-search-form button",
          ...(view === "tasks"
            ? ["#task-select"]
            : ["#domain-previous", "#domain-next"]),
        ]) {
          const box = await page.locator(selector).boundingBox();
          assert(
            box && box.x >= 0 && box.x + box.width <= width + 1,
            `${selector} is clipped at ${width}px`,
          );
        }
      }
      if (!(await page.locator("#filter-phase").isVisible()))
        await page.locator("#task-filters > summary").click();
      await page.locator("#filter-phase").selectOption("phase_b");
      const clearBox = await page.locator("#clear-context").boundingBox();
      const filterHeader = await page
        .locator("#task-filters > summary")
        .boundingBox();
      assert(
        clearBox &&
          filterHeader &&
          clearBox.y >= filterHeader.y &&
          clearBox.y + clearBox.height <=
            filterHeader.y + filterHeader.height + 1,
        "Clear filters should stay in the filter header",
      );
      await page.locator('[data-task-id="plan_c"]').waitFor();
      await page.locator("#filter-phase").selectOption("");
      await chooseTask("plan_a");
      await page.locator('[data-task-id="plan_a"]').first().waitFor();
      const currentStep = page.locator(
        '[data-task-group="plan_a"] > .task-card details[data-step-id="z_first"]',
      );
      if ((await currentStep.getAttribute("open")) === null)
        await currentStep.locator("summary").click();
      const longReference = currentStep
        .locator("pre")
        .filter({ hasText: "reference/" });
      await longReference.waitFor();
      assert.equal(
        await longReference.evaluate(
          (pre) => pre.scrollWidth <= pre.clientWidth + 1,
        ),
        true,
        `Long Step reference needs horizontal scrolling at ${width}px`,
      );
      await currentStep.locator("[data-detail]").click();
      await page.locator("#detail[open]").waitFor();
      const dialog = await page.locator("#detail").boundingBox();
      assert(
        dialog &&
          dialog.x >= 0 &&
          dialog.x + dialog.width <= width + 1 &&
          dialog.height <= 720,
        `Detail dialog exceeds ${width}px dock`,
      );
      await page.keyboard.press("Escape");
      await page.locator("#detail[open]").waitFor({ state: "hidden" });
      await page.locator("footer").scrollIntoViewIfNeeded();
      const nav = await page.locator("#view-tabs").boundingBox();
      assert(
        nav && nav.y >= 0 && nav.y + nav.height <= 720,
        "Domain navigation disappeared while scrolling dock",
      );
    }
    await page.locator('[data-view="phases"]').click();
    if (!(await page.locator("#filter-file").isVisible()))
      await page.locator("#task-filters > summary").click();
    assert.equal(await page.locator("#filter-scene").isVisible(), false);
    await page.locator("#filter-file").selectOption("other.3dm");
    await page.locator("tbody tr").filter({ hasText: "다른 Phase" }).waitFor();
    assert.equal(
      await page.locator("tbody tr").count(),
      1,
      "Phase file filter ignored its stored file relation",
    );
    await page.locator('[data-view="scenes"]').click();
    await page.locator("tbody tr").filter({ hasText: "휴식 장면" }).waitFor();
    assert.equal(await page.locator("tbody tr").count(), 1);
    await page.locator('[data-view="holons"]').click();
    await page.locator("#filter-scene").selectOption("scene_a");
    await page.locator(".no-records").waitFor();
    await page.locator("#filter-scene").selectOption("scene_b");
    await page.locator("tbody tr").filter({ hasText: "쉼터" }).waitFor();
    assert.equal(
      await page.locator("tbody tr").count(),
      1,
      "Holon filters should compose file AND Scene",
    );
    await page.locator("#clear-context").click();
    await page.locator('[data-view="tasks"]').click();
    await chooseTask("plan_a");
    await page.reload();
    await page.locator('[data-task-group="plan_a"]').waitFor();
    assert.equal(
      await page.locator("#task-select").inputValue(),
      "plan_a",
      "Selected Task lost after reload",
    );
    await page.waitForLoadState("networkidle");
    let releaseTask, taskRequested;
    const taskGate = new Promise((resolve) => {
      releaseTask = resolve;
    });
    const taskStarted = new Promise((resolve) => {
      taskRequested = resolve;
    });
    await page.route("**/api/domain?*", async (route) => {
      if (
        new URL(route.request().url()).searchParams.get("focus") === "plan_b"
      ) {
        taskRequested();
        await taskGate;
      }
      await route.continue();
    });
    await page.locator("#task-select").selectOption("plan_b");
    await taskStarted;
    await chooseTask("plan_c");
    releaseTask();
    await page.waitForLoadState("networkidle");
    assert.equal(
      await page
        .locator('#domain-results > [data-task-group="plan_c"]')
        .count(),
      1,
      "A late Task response replaced the newer dropdown selection",
    );
    await page.unroute("**/api/domain?*");
    for (const width of [1440, 650, 320]) {
      await page.setViewportSize({
        width,
        height: width === 1440 ? 1050 : 720,
      });
      for (const view of [
        "files",
        "scenes",
        "holons",
        "phases",
        "tasks",
        "steps",
      ]) {
        await page.locator(`[data-view="${view}"]`).click();
        await page
          .locator('#domain-results[aria-busy="false"] > *')
          .first()
          .waitFor();
        if (view === "tasks") {
          await chooseTask("plan_a");
          await assertTaskOrder(
            page.locator('[data-task-group="plan_a"] > .task-card'),
            width,
          );
          const comparison = page.locator(
            '[data-task-group="plan_a"] > .adjacent-tasks',
          );
          if ((await comparison.getAttribute("open")) === null)
            await comparison.locator(":scope > summary").click();
          await comparison.locator(".task-card").waitFor();
          await assertTaskOrder(comparison.locator(".task-card"), width);
          const header = page.locator(
            '[data-task-group="plan_a"] > .task-card .task-heading',
          );
          const loop = await header.locator(".task-loop").boundingBox();
          const status = await header.locator(".status-label").boundingBox(),
            rev = await header.locator(".task-revision").boundingBox();
          assert(
            status.y < loop.y && rev.y < loop.y,
            `Task B layout is not preserved at ${width}px`,
          );
        }
        if (view === "steps") {
          const first = page.locator("#domain-results > details").first();
          if ((await first.getAttribute("open")) === null)
            await first.locator("summary").click();
        }
        await page
          .locator("#domain-results [data-detail]:visible")
          .first()
          .click();
        await page.locator("#detail[open] .detail-field").first().waitFor();
        const fields = await page
          .locator("#detail .detail-field")
          .evaluateAll((fields) =>
            fields.map((field) => ({
              size: parseFloat(
                getComputedStyle(field.querySelector("h3")).fontSize,
              ),
              weight: parseInt(
                getComputedStyle(field.querySelector("h3")).fontWeight,
              ),
              background: getComputedStyle(field.querySelector(".stored-value"))
                .backgroundColor,
            })),
          );
        assert(
          fields.every(
            (field) =>
              field.size >= 14 &&
              field.weight >= 700 &&
              field.background === "rgb(255, 255, 255)",
          ),
          `${view} detail fields do not share the requested style at ${width}px`,
        );
        assert(
          await page
            .locator("#detail")
            .evaluate((dialog) => dialog.scrollWidth <= dialog.clientWidth + 1),
          `${view} detail overflows ${width}px`,
        );
        await page.keyboard.press("Escape");
      }
    }
    await page.waitForLoadState("networkidle");
    assert.deepEqual(errors, []);
    console.log(
      "Dashboard browser contracts passed: six domains, no raw UI, Step records, filters, state, dialog.",
    );
  } finally {
    await browser?.close();
    child.kill();
    if (child.exitCode === null) await once(child, "exit");
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
