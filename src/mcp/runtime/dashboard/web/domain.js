"use strict";
const planStatusLabels = new Map(Object.entries({
  pending: "대기",
  running: "진행 중",
  completed: "완료",
  failed: "실패",
  blocked: "막힘",
  paused: "일시정지",
}));
const filterLabels = { file: "파일", phase: "Phase", scene: "Scene", status: "상태", execution: "실행 이력" };

function planSequences(ids, records) {
  const siblings = new Set(ids);
  const children = new Map(ids.map((id) => [id, []]));
  const roots = [];
  for (const id of ids) {
    const previous = records.get(id).previous?.id;
    if (previous !== id && siblings.has(previous)) children.get(previous).push(id);
    else roots.push(id);
  }
  const seen = new Set();
  const sequences = [];
  for (const root of roots) {
    const levels = [];
    for (let level = [root]; level.length; level = level.flatMap((id) => children.get(id))) {
      levels.push(level);
      for (const id of level) seen.add(id);
    }
    sequences.push(levels);
  }
  // Following cyclic references has no starting point. Keep each item and show its saved reference.
  for (const id of ids)
    if (!seen.has(id)) sequences.push([[id]]);
  return sequences;
}

window.DomainExplorer = class {
  constructor({ api, node, notify }) {
    Object.assign(this, { api, node, notify });
    this.schema = null;
    this.schemaVersion = 0;
    this.optionNotes = [];
    this.version = 0;
    this.request = 0;
    this.detailRequest = 0;
    this.labels = {
      files: "File 목록",
      scenes: "Scene 조회",
      holons: "Holon 조회",
      phases: "Phase",
      tasks: "Task",
      steps: "Step",
    };
    this.descriptions = {
      files: "파일에서 장면과 작업으로 이어지는 프로젝트의 연결을 살펴봅니다.",
      scenes: "장면에 연결된 Holon과 작업의 맥락을 읽습니다.",
      holons: "건축 요소의 의미와 저장된 장면·부모 관계를 살펴봅니다.",
      phases: "Phase별 작업과 진행 맥락을 함께 읽습니다.",
      tasks: "관계가 있는 작업을 곁에 두고 회차별 Step과 피드백을 읽습니다.",
      steps: "Task별 현재 회차의 Step과 판단·입출력 기록을 찾아봅니다.",
    };
    this.reset();
    document
      .querySelectorAll("[data-view]")
      .forEach((b) =>
        b.addEventListener("click", () => this.select(b.dataset.view)),
      );
    this.$("domain-search-form").addEventListener("submit", (e) => {
      e.preventDefault();
      this.current.search = this.$("domain-search").value;
      this.current.offset = 0;
      this.save();
      this.load();
    });
    for (const [id, n] of [
      ["domain-previous", -20],
      ["domain-next", 20],
    ])
      this.$(id).addEventListener("click", () => {
        this.current.offset = Math.max(0, this.current.offset + n);
        this.save();
        this.load();
      });
    this.$("domain-show-all").addEventListener("click", () => {
      Object.assign(this.current, { focus: "", parent: "", offset: 0 });
      this.save();
      this.chrome();
      this.load();
    });
    for (const key of Object.keys(filterLabels))
      this.$("filter-" + key).addEventListener("change", () => {
        this.state.filters[key] = this.$("filter-" + key).value;
        Object.assign(this.current, { offset: 0, focus: "" });
        this.save();
        this.chrome();
        this.load();
      });
    this.$("clear-context").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.state.filters = {};
      Object.assign(this.current, { offset: 0, focus: "", parent: "" });
      this.save();
      this.chrome();
      this.load();
    });
    this.$("task-filters")
      .querySelector("summary")
      .addEventListener("click", () => {
        this.state.filterPanelOpen = !this.$("task-filters").open;
        this.save();
      });
    this.wideFilters = window.matchMedia("(min-width: 901px)");
    this.wideFilters.addEventListener("change", () => this.updateFilterPanel());
    this.$("task-select").addEventListener("change", () => {
      Object.assign(this.current, {
        task: this.$("task-select").value,
        focus: "",
        parent: "",
        offset: 0,
      });
      this.save();
      this.chrome();
      this.load();
    });
  }
  $(id) {
    return document.getElementById(id);
  }
  reset() {
    this.state = {
      view: "tasks",
      views: {},
      filters: {},
      expanded: [],
      comparisons: {},
    };
  }
  get view() {
    return this.state.view;
  }
  get current() {
    return (this.state.views[this.view] ||= {
      offset: 0,
      search: "",
      focus: "",
      parent: "",
    });
  }
  plain(value) {
    if (value === null || value === undefined || value === "") return "미기록";
    if (typeof value === "object" && Object.hasOwn(value, "value"))
      return String(value.value) + (value.truncated ? "… [일부 표시]" : "");
    return typeof value === "object"
      ? JSON.stringify(value, null, 2)
      : String(value);
  }
  storedValue(original, json = false) {
    const box = this.node("div", undefined, "stored-value");
    let value = original;
    const wrapped =
      value &&
      typeof value === "object" &&
      Object.hasOwn(value, "value") &&
      ["text", "integer", "number"].includes(value.kind);
    if (wrapped) value = value.value;
    if (json && typeof value === "string") {
      try {
        value = JSON.parse(value);
      } catch {
        /* Keep malformed stored text visible. */
      }
    }
    const pending = [[box, value]];
    while (pending.length) {
      const [parent, entry] = pending.pop();
      if (entry === null || entry === undefined || entry === "") {
        parent.append(this.node("span", "미기록", "missing-value"));
      } else if (Array.isArray(entry)) {
        if (!entry.length)
          parent.append(this.node("span", "없음", "missing-value"));
        else {
          const list = this.node("ul");
          parent.append(list);
          for (const item of entry) {
            const li = this.node("li");
            list.append(li);
            pending.push([li, item]);
          }
        }
      } else if (typeof entry === "object") {
        const fields = Object.entries(entry),
          list = this.node("dl");
        if (!fields.length)
          parent.append(this.node("span", "없음", "missing-value"));
        else {
          parent.append(list);
          for (const [key, item] of fields) {
            const detail = this.node("dd");
            list.append(this.node("dt", key), detail);
            pending.push([detail, item]);
          }
        }
      } else {
        const text = String(entry),
          pre = this.node("pre");
        let end = 0;
        const links = /^https?:\/\/\S+$/.test(text)
          ? [{ 0: text, index: 0 }]
          : text.matchAll(/https?:\/\/[^\s<>"]+/g);
        for (const match of links) {
          pre.append(document.createTextNode(text.slice(end, match.index)));
          try {
            new URL(match[0]);
            const link = this.node("a", match[0]);
            link.href = match[0];
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            pre.append(link);
          } catch {
            pre.append(document.createTextNode(match[0]));
          }
          end = match.index + match[0].length;
        }
        pre.append(document.createTextNode(text.slice(end)));
        parent.append(pre);
      }
    }
    if (wrapped && original.truncated)
      box.append(
        this.node(
          "p",
          "일부 표시 · 저장값이 표시 한도를 초과했습니다.",
          "hint",
        ),
      );
    return box;
  }
  field(name, value, className = "record-field") {
    const field = this.node("section", undefined, className);
    field.append(
      this.node("h3", name),
      this.storedValue(value, name.endsWith("_json")),
    );
    return field;
  }
  save() {
    if (this.schema?.path) {
      try {
        sessionStorage.setItem(
          "dashboard-context:" + this.schema.path,
          JSON.stringify(this.state),
        );
      } catch {}
    }
  }
  async setSchema(schema) {
    this.version++;
    const schemaVersion = ++this.schemaVersion;
    this.optionNotes = [];
    this.hasExecutionHistory = false;
    this.$("task-outline").replaceChildren();
    for (const key of ["file", "phase", "scene"])
      this.$("filter-" + key).replaceChildren(new Option("불러오는 중…", ""));
    this.schema = schema;
    this.$("detail").close();
    this.reset();
    try {
      const stored = JSON.parse(
        sessionStorage.getItem("dashboard-context:" + schema.path) || "null",
      );
      if (
        stored &&
        this.labels[stored.view] &&
        stored.views &&
        stored.filters &&
        Array.isArray(stored.expanded)
      )
        this.state = stored;
    } catch {}
    if (!schema.domain_views?.[this.view])
      this.state.view =
        Object.keys(this.labels).find((key) => schema.domain_views?.[key]) ||
        "tasks";
    this.chrome();
    if (!schema.name) return;
    try {
      const options = await this.api(
        "/api/domain-options?" + new URLSearchParams({ database: schema.path }),
      );
      if (schemaVersion !== this.schemaVersion) return;
      this.optionNotes = options.notes || [];
      const statusSelect = this.$("filter-status");
      statusSelect.replaceChildren(new Option("전체 상태", ""));
      for (const status of options.statuses || [])
        statusSelect.add(new Option(planStatusLabels.get(status) || status, status));
      this.hasExecutionHistory = options.has_execution_history;
      if (!this.hasExecutionHistory) delete this.state.filters.execution;
      for (const [key, plural, label] of [
        ["file", "files", "파일"],
        ["phase", "phases", "Phase"],
        ["scene", "scenes", "Scene"],
      ]) {
        const select = this.$("filter-" + key);
        select.replaceChildren(new Option("전체 " + label, ""));
        for (const option of options[plural] || [])
          select.add(new Option(option.name, option.id));
        const selected = this.state.filters[key];
        if (selected && ![...select.options].some((o) => o.value === selected))
          select.add(new Option("현재 DB에 없는 선택: " + selected, selected));
      }
    } catch (error) {
      if (schemaVersion === this.schemaVersion)
        this.notify(error.message, true);
    }
    if (schemaVersion === this.schemaVersion) {
      this.chrome();
      await this.load();
    }
  }
  chrome() {
    const present = !!this.schema?.name;
    this.$("empty").hidden = present;
    this.$("domain-explorer").hidden = !present;
    document.querySelectorAll("[data-view]").forEach((b) => {
      b.disabled = !this.schema?.domain_views?.[b.dataset.view];
      b.setAttribute("aria-pressed", String(b.dataset.view === this.view));
    });
    this.$("domain-title").textContent = this.labels[this.view];
    this.$("domain-description").textContent = this.descriptions[this.view];
    this.$("domain-search").value = this.current.search;
    const keys = this.filterKeys();
    this.$("task-filters").hidden = !keys.length;
    this.$("filter-title").textContent =
      keys
        .map((key) => filterLabels[key])
        .join("·") + " 필터";
    this.$("task-chooser").hidden = this.view !== "tasks";
    this.$("task-outline").hidden = this.view !== "tasks";
    document.querySelector(".pagination").hidden = this.view === "tasks";
    this.updateFilterPanel();
    const activeFilters = keys.filter((key) => this.state.filters[key]).length;
    this.$("filter-summary").textContent = activeFilters
      ? `${activeFilters}개 적용`
      : "전체";
    for (const key of Object.keys(filterLabels)) {
      this.$("filter-" + key).closest("label").hidden = !keys.includes(key);
      this.$("filter-" + key).value = this.state.filters[key] || "";
      this.$("filter-" + key).disabled =
        !!this.current.focus || !!this.current.parent;
    }
    this.$("focus-bar").hidden = !this.current.focus && !this.current.parent;
    this.$("focus-label").textContent = this.current.parent
      ? "선택한 Task의 Step · 전체 목록에서 저장된 필터로 돌아갑니다."
      : "선택한 항목 · 전체 목록에서 저장된 검색·필터로 돌아갑니다.";
  }
  updateFilterPanel() {
    this.$("task-filters").open = this.state.filterPanelOpen ?? this.wideFilters.matches;
  }
  filterKeys() {
    return (
      {
        tasks: ["file", "phase", "scene", "status", ...(this.hasExecutionHistory ? ["execution"] : [])],
        steps: ["file", "phase", "scene"],
        phases: ["file"],
        scenes: ["file"],
        holons: ["file", "scene"],
      }[this.view] || []
    );
  }
  select(view, focus = "", parent = "") {
    if (!this.schema?.domain_views?.[view]) return;
    this.version++;
    this.$("detail").close();
    this.state.view = view;
    if (focus || parent)
      Object.assign(this.current, { focus, parent, offset: 0 });
    this.save();
    this.chrome();
    this.load();
  }
  path(route, extra = {}) {
    return (
      "/api/" +
      route +
      "?" +
      new URLSearchParams({
        database: this.schema.path,
        view: this.view,
        ...extra,
      })
    );
  }
  async load() {
    const version = this.version,
      request = ++this.request,
      result = this.$("domain-results");
    const outlineHost = this.$("task-outline");
    result.replaceChildren();
    result.setAttribute("aria-busy", "true");
    this.$("domain-note").textContent = "자료를 읽고 있습니다…";
    this.$("domain-previous").disabled = this.$("domain-next").disabled = true;
    this.$("domain-page-info").textContent = "";
    try {
      const filters = Object.fromEntries(
        this.filterKeys().map((key) => [key, this.state.filters[key] || ""]),
      );
      const selected = this.current.focus || this.current.parent;
      let task = "",
        outline = null,
        taskNotes = [];
      if (this.view === "tasks") {
        const select = this.$("task-select");
        select.disabled = true;
        const options = await this.api(
          this.path("domain-options", {
            ...filters,
            search: this.current.search,
          }),
        );
        if (version !== this.version || request !== this.request) return;
        const candidates = options.tasks || [];
        outline = options.plan_outline;
        taskNotes = options.notes || [];
        task =
          this.current.focus ||
          (candidates.some((item) => item.id === this.current.task)
            ? this.current.task
            : candidates[0]?.id || "");
        const names = new Map();
        for (const item of candidates)
          names.set(item.name, (names.get(item.name) || 0) + 1);
        select.replaceChildren(
          ...candidates.map((item) => {
            const option = new Option(
              item.name + (names.get(item.name) > 1 ? ` · ${item.id}` : ""),
              item.id,
            );
            option.title = item.id;
            return option;
          }),
        );
        if (task && !candidates.some((item) => item.id === task))
          select.add(new Option("선택한 Task", task));
        if (!task) select.add(new Option("조건에 맞는 Task 없음", ""));
        select.value = task;
        select.disabled = !task;
        this.$("task-count").textContent = this.current.focus
          ? "직접 선택"
          : `${candidates.length}개`;
        if (!this.current.focus) {
          this.current.task = task;
          this.save();
        }
      }
      const data =
        this.view === "tasks" && !task
          ? { groups: [], offset: 0, has_more: false }
          : await this.api(
              this.path("domain", {
                ...this.current,
                ...filters,
                ...(selected
                  ? { search: "", file: "", phase: "", scene: "", status: "", execution: "" }
                  : {}),
                ...(this.view === "tasks"
                  ? { focus: task, search: "", offset: 0 }
                  : {}),
                limit: this.view === "tasks" ? 1 : 20,
              }),
            );
      if (version !== this.version || request !== this.request) return;
      if (this.view === "tasks" && this.current.focus && data.groups[0])
        this.$("task-select").selectedOptions[0].textContent =
          data.groups[0].name;
      if (this.view === "tasks") {
        const active = outlineHost.contains(document.activeElement)
          ? document.activeElement.dataset.outlinePlan
          : "";
        outlineHost.replaceChildren(this.planOutline(outline, { selected: task }));
        if (active)
          [...outlineHost.querySelectorAll("[data-outline-plan]")]
            .find((button) => button.dataset.outlinePlan === active)
            ?.focus({ preventScroll: true });
      }
      this.render(data);
      this.$("domain-note").textContent = [
        ...new Set([...this.optionNotes, ...taskNotes, ...(data.notes || [])]),
      ]
        .filter(
          (note) =>
            !note.startsWith("현재 DB에는 Step별 목표가 저장되지 않습니다."),
        )
        .join("\n");
      this.$("domain-page-info").textContent = data.groups.length
        ? `${data.offset + 1}번부터 ${data.groups.length}개 항목 · ${data.has_more ? "다음 자료 있음" : "마지막 페이지"}`
        : "조건에 맞는 항목이 없습니다.";
      this.$("domain-previous").disabled = data.offset === 0;
      this.$("domain-next").disabled = !data.has_more;
    } catch (error) {
      if (version === this.version && request === this.request)
        this.$("domain-note").textContent = error.message;
    } finally {
      if (version === this.version && request === this.request)
        result.setAttribute("aria-busy", "false");
    }
  }
  button(title, action, className = "record-link") {
    const b = this.node("button", title, className);
    b.type = "button";
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      action();
    });
    return b;
  }
  detailButton(title, kind, id, parent = "", loop = null) {
    const b = this.button(title, () => this.detail(kind, id, parent, loop));
    b.dataset.detail = kind;
    return b;
  }
  refs(values, view) {
    const box = this.node("div", undefined, "record-links");
    if (!values?.length) box.append(this.node("span", "—", "missing-value"));
    for (const v of values || [])
      box.append(this.button(v.name, () => this.select(view, v.id)));
    return box;
  }
  status(value) {
    const b = this.node(
      "span",
      planStatusLabels.get(value) || this.plain(value),
      "status-label",
    );
    b.dataset.status = value || "";
    return b;
  }
  planOutline(outline, { selected = "", showCount = false } = {}) {
    const box = this.node("div", undefined, "plan-outline");
    const records = new Map((outline?.items || []).map((item) => [item.id, item]));
    if (!records.size) {
      box.append(this.node("span", "표시할 Task 없음", "missing-value"));
      return box;
    }
    if (showCount) {
      const matches = [...records.values()].filter((item) => item.matches).length;
      box.append(this.node("p", `${matches}개 Task`, "plan-context"));
    }

    const parentOf = new Map(), children = new Map();
    for (const item of records.values()) {
      for (const parent of item.parents) {
        if (!records.has(parent)) continue;
        let ancestor = parent;
        while (ancestor && ancestor !== item.id) ancestor = parentOf.get(ancestor);
        if (!ancestor) {
          parentOf.set(item.id, parent);
          break;
        }
      }
      for (const parent of item.parents) {
        if (!records.has(parent) || parent === item.id) continue;
        if (!children.has(parent)) children.set(parent, []);
        children.get(parent).push(item.id);
      }
    }
    const rootIds = [...records.keys()].filter((id) => !parentOf.has(id));
    const pendingChildren = [];
    const appendPlan = (container, id, { nested = false, linked = false, ordered = false } = {}) => {
      const item = records.get(id);
      const entry = this.node(nested ? "li" : "div", undefined, "plan-outline-entry");
      entry.dataset.planEntry = id;
      const line = this.node("div", undefined, "plan-outline-line");
      const button = this.button(item.name, () => {
        if (this.view !== "tasks" || !item.matches) {
          this.select("tasks", id);
        } else {
          Object.assign(this.current, { task: id, focus: "", parent: "", offset: 0 });
          this.save();
          this.chrome();
          this.load();
        }
      });
      button.dataset.outlinePlan = id;
      if (selected === id) button.setAttribute("aria-current", "true");
      line.append(button, this.status(item.status));
      if (!item.matches) {
        const files = item.file_names?.join(" · ");
        line.append(this.node("span", files ? "상위 맥락 · " + files : "상위 맥락", "plan-context"));
      }
      if (linked) line.append(this.node("span", "연결된 하위 Task", "plan-context"));
      if (item.parents.some((parent) => parent === id || !records.has(parent)))
        line.append(this.node("span", "표시할 수 없는 상위 참조 있음", "plan-context"));
      entry.append(line);
      if (item.previous) {
        const previous = this.node("div", undefined, "plan-previous");
        if (ordered) {
          const arrow = this.node("span", nested ? "↑" : "→",
            nested ? "plan-sibling-arrow" : "plan-sequence-arrow");
          arrow.setAttribute("aria-hidden", "true");
          previous.append(arrow);
        }
        previous.append(this.node("span", "선행 · " + (item.previous.name || item.previous.id)));
        entry.append(previous);
      }
      container.append(entry);
      if (!linked && children.has(id)) pendingChildren.push([entry, id]);
    };
    for (const sequence of planSequences(rootIds, records)) {
      const strip = this.node("div", undefined, "plan-sequence");
      for (const [depth, ids] of sequence.entries()) {
        const level = this.node("div", undefined, "plan-sequence-level");
        for (const id of ids) appendPlan(level, id, { ordered: depth > 0 });
        strip.append(level);
      }
      box.append(strip);
    }
    for (const [entry, parent] of pendingChildren) {
      const list = this.node("ul", undefined, "plan-children");
      for (const sequence of planSequences(children.get(parent), records))
        for (const [depth, ids] of sequence.entries())
          for (const id of ids)
            appendPlan(list, id, { nested: true, linked: parentOf.get(id) !== parent, ordered: depth > 0 });
      entry.append(list);
    }
    if (outline.truncated)
      box.append(this.node("p", "조회 한도로 일부 상위 관계가 표시되지 않을 수 있습니다.", "plan-context"));
    return box;
  }
  render(data) {
    if (!data.groups.length) {
      this.$("domain-results").append(
        this.node("p", "조건에 맞는 기록이 없습니다.", "no-records"),
      );
      return;
    }
    if (this.view === "tasks")
      for (const g of data.groups)
        this.$("domain-results").append(this.taskGroup(g));
    else if (this.view === "steps")
      for (const g of data.groups)
        this.$("domain-results").append(
          this.step(g, g.parent, g.task?.name, true),
        );
    else this.table(data.groups);
  }
  taskGroup(group) {
    const frame = this.node("section", undefined, "task-group");
    frame.dataset.taskGroup = group.id;
    frame.append(this.task(group));
    const relations = (group.relations || []).filter(
      (item) => !item.missing && item.id !== group.id,
    );
    if (!relations.length) return frame;
    const side = this.node("details", undefined, "adjacent-tasks");
    const toggle = this.node("summary", "관련 Task 비교");
    side.open =
      this.state.comparisonOpen?.[group.id] ??
      window.matchMedia("(min-width: 901px)").matches;
    toggle.addEventListener("click", () => {
      (this.state.comparisonOpen ||= {})[group.id] = !side.open;
      this.save();
    });
    side.append(toggle);
    const label = this.node("label", "연결된 Task 나란히 읽기");
    const select = this.node("select");
    const labels = {
      previous: "이전",
      next: "후속",
      depends_on: "선행 의존",
      dependent: "후속 의존",
      parent: "부모",
      child: "자식",
    };
    for (const [index, relation] of relations.entries())
      select.add(
        new Option(
          `${labels[relation.type] || relation.type} · ${relation.name}`,
          String(index),
        ),
      );
    const comparisons = (this.state.comparisons ||= {});
    const remembered = relations.findIndex(
      (relation) => `${relation.type}:${relation.id}` === comparisons[group.id],
    );
    if (remembered >= 0) select.value = String(remembered);
    label.append(select);
    const content = this.node("div");
    side.append(
      label,
      this.node(
        "p",
        "목록의 검색·필터와 독립적으로 연결된 작업을 읽습니다.",
        "hint",
      ),
      content,
    );
    frame.append(side);
    const version = this.version,
      request = this.request;
    let selection = 0;
    const show = async () => {
      const own = ++selection;
      const relation = relations[Number(select.value)];
      content.replaceChildren(
        this.node("p", "연결된 작업을 읽고 있습니다…", "hint"),
      );
      try {
        const data = await this.api(
          this.path("domain", { view: "tasks", focus: relation.id, limit: 1 }),
        );
        if (
          version !== this.version ||
          request !== this.request ||
          own !== selection ||
          !frame.isConnected
        )
          return;
        content.replaceChildren(
          data.groups.length
            ? this.task(data.groups[0], true, "adjacent:" + group.id)
            : this.node("p", "연결된 작업이 현재 DB에 없습니다.", "hint"),
        );
        if (data.notes?.length)
          content.append(this.node("p", data.notes.join("\n"), "hint"));
      } catch (error) {
        if (
          version === this.version &&
          request === this.request &&
          own === selection &&
          frame.isConnected
        )
          content.replaceChildren(this.node("p", error.message, "hint"));
      }
    };
    select.addEventListener("change", () => {
      const relation = relations[Number(select.value)];
      comparisons[group.id] = `${relation.type}:${relation.id}`;
      this.save();
      show();
    });
    // One bounded neighbour per visible Task; never recursively expand the graph.
    queueMicrotask(show);
    return frame;
  }
  loopPicker(group, card, adjacent, location) {
    const numbers = group.loop_numbers || [];
    if (!numbers.length)
      return this.node("span", group.loop_no === 0 ? "실행 전" : "회차 미기록", "task-loop");
    const controls = this.node("div", undefined, "task-loop");
    const select = this.node("select");
    select.setAttribute("aria-label", "조회할 회차");
    for (const n of numbers) {
      const title = n === 0 ? "실행 전 기록 (0)" : `Loop ${n}`;
      select.add(new Option(title + (n === group.current_loop && n > 0 ? " · 현재" : ""), String(n)));
    }
    select.value = String(group.loop_no);
    let serial = 0;
    const previous = this.button("←", () => change(select.selectedIndex - 1, "previous"), "loop-arrow");
    const next = this.button("→", () => change(select.selectedIndex + 1, "next"), "loop-arrow");
    previous.setAttribute("aria-label", "이전 회차");
    next.setAttribute("aria-label", "다음 회차");
    const sync = () => {
      previous.disabled = select.selectedIndex <= 0;
      next.disabled = select.selectedIndex >= numbers.length - 1;
    };
    const change = async (index, trigger) => {
      if (index < 0 || index >= numbers.length) return;
      const own = ++serial;
      this.$("detail").close();
      const version = this.version, request = this.request;
      select.selectedIndex = index;
      sync();
      const active = () => card.isConnected && own === serial && version === this.version && request === this.request;
      card.setAttribute("aria-busy", "true");
      try {
        const data = await this.api(this.path("domain", { view: "tasks", focus: group.id, loop_no: numbers[index], limit: 1 }));
        if (!active()) return;
        const selected = data.groups[0];
        if (!selected || selected.id !== group.id || selected.loop_no !== numbers[index])
          throw new Error("선택한 Task 또는 회차 기록이 없습니다.");
        const replacement = this.task(selected, adjacent, location);
        if (data.notes?.length) replacement.append(this.node("p", data.notes.join("\n"), "hint"));
        const hadFocus = controls.contains(document.activeElement);
        card.replaceWith(replacement);
        if (hadFocus) {
          const arrows = replacement.querySelectorAll(".loop-arrow");
          const button = trigger === "previous" ? arrows[0] : trigger === "next" ? arrows[1] : null;
          (button && !button.disabled ? button : replacement.querySelector(".task-loop select"))?.focus();
        }
      } catch (error) {
        if (!active()) return;
        select.value = String(group.loop_no);
        sync();
        card.removeAttribute("aria-busy");
        this.notify(error.message, true);
      }
    };
    select.addEventListener("change", () => change(select.selectedIndex, "select"));
    sync();
    controls.append(previous, select, next);
    return controls;
  }
  task(group, adjacent = false, location = "") {
    const card = this.node("article", undefined, "task-card");
    card.dataset.taskId = group.id;
    const selectedLoop = group.loop_numbers?.includes(group.loop_no) ? group.loop_no : null;
    card.dataset.loop = group.loop_no ?? "";
    const header = this.node("div", undefined, "task-heading"),
      identity = this.node("div", undefined, "task-identity"),
      meta = this.node("div", undefined, "task-meta"),
      h = this.node("h2");
    h.append(this.detailButton(group.name, "tasks", group.id, "", selectedLoop));
    const top = this.node("div", undefined, "task-meta-top");
    top.append(
      this.loopPicker(group, card, adjacent, location),
      this.status(group.status),
    );
    meta.append(
      top,
      this.node("span", `REV ${group.revision ?? "미기록"}`, "task-revision"),
    );
    if (group.history) identity.append(this.node("span", "현재 연결된 Phase · 파일", "hint"));
    identity.append(
      this.node("span", group.phase?.name || "Phase 미지정", "task-phase"),
      this.node(
        "span",
        (group.file_names || []).join(" · ") || "파일 미지정",
        "task-files",
      ),
      h,
    );
    header.append(identity, meta);
    card.append(header);
    const context = this.node("div", undefined, "task-context");
    if (group.history) {
      card.append(this.node("p", group.history === "partial"
        ? "일부 기록 · 이 회차에 남아 있는 자료만 표시합니다."
        : "과거 회차 · 마지막으로 저장된 revision", "history-kind"));
      context.append(this.node("span", "현재 연결된 Scene", "hint"));
    }
    context.append(this.refs(group.scenes, "scenes"));
    if (group.scenes?.length) card.append(context);
    card.append(this.field("goal", group.goal));
    if (group.scope) card.append(this.field("scope", group.scope));
    if (group.loop_no > 0 || group.feedback) card.append(this.field("feedback", group.feedback));
    for (const key of ["loop_created_at", "artifact_dir", "loop_artifact_dir"])
      if (group[key]) card.append(this.field(key, group[key]));
    if (group.artifact_refs && group.artifact_refs !== "[]")
      card.append(this.field("artifact_refs_json", group.artifact_refs));
    if (!adjacent && group.relations?.length) {
      const related = this.node("div", undefined, "task-relations"),
        labels = {
          previous: "이전 Task",
          next: "후속 Task",
          depends_on: "선행 의존",
          dependent: "후속 의존",
          parent: "부모 Task",
          child: "자식 Task",
        };
      if (group.history) related.append(this.node("span", "현재 연결된 Task", "hint"));
      for (const r of group.relations) {
        const item = this.node("div", undefined, "relation-item");
        item.append(
          this.node("span", labels[r.type] || r.type, "relation-type"),
          r.missing
            ? this.node("span", `미등록 · ${r.id}`, "missing-value")
            : this.detailButton(r.name, "tasks", r.id),
        );
        related.append(item);
      }
      card.append(related);
    }
    const steps = this.node("div", undefined, "steps-list");
    for (const s of group.steps || [])
      steps.append(
        this.step(
          { ...s, loop_no: group.loop_no },
          group.id,
          "",
          false,
          location || "task:" + group.id,
          selectedLoop,
        ),
      );
    if (!group.steps?.length)
      steps.append(this.node("p", "기록된 Step 없음", "missing-value"));
    card.append(steps);
    return card;
  }
  step(step, parent, taskName = "", standalone = false, location = "steps", selectedLoop = null) {
    const panel = this.node(
      "details",
      undefined,
      "step-record" + (standalone ? " standalone-step" : ""),
    );
    panel.dataset.stepId = step.id;
    const identity = [location, parent, step.loop_no, step.id].join(":"),
      summary = this.node("summary");
    summary.append(
      this.node("span", step.step_type || "유형 미기록", "step-type"),
      this.node("span", step.name, "step-name"),
      this.status(step.status),
    );
    if (taskName) summary.append(this.node("span", taskName, "step-task"));
    panel.append(summary);
    const body = this.node("div", undefined, "step-body");
    const header = this.node("div", undefined, "step-heading"),
      meta = this.node("div", undefined, "step-meta");
    meta.append(
      this.node("span", `loop_no · ${step.loop_no ?? "미기록"}`, "step-loop"),
      this.node("p", `step_id · ${step.id}`, "identity"),
    );
    header.append(
      this.node("span", `kind · ${this.plain(step.kind)}`, "step-kind"),
      meta,
    );
    body.append(header);
    for (const [label, value] of [
      ["takeaways", step.takeaways],
      ["design_rationale", step.design_rationale],
      ["input_refs_json", step.input_refs_json],
      ["output_refs_json", step.output_refs_json],
    ]) {
      body.append(this.field(label, value));
    }
    const footer = this.node("div", undefined, "step-footer");
    footer.append(
      this.detailButton("Step 전체 기록 ↗", "steps", step.id, parent, selectedLoop),
    );
    body.append(footer);
    panel.append(body);
    panel.open = this.state.expanded.includes(identity);
    panel.addEventListener("toggle", () => {
      const expanded = new Set(this.state.expanded);
      if (panel.open) expanded.add(identity);
      else expanded.delete(identity);
      this.state.expanded = [...expanded].slice(-2000);
      this.save();
    });
    return panel;
  }
  table(groups) {
    const columns = {
      files: ["파일명", "설명", "Scene", "Holon", "Phase", "Task"],
      scenes: ["Scene 이름", "Holon", "객체 이름", "Task"],
      holons: [
        "Holon 이름",
        "Scene",
        "부모 Holon",
        "객체 수 · 저장 요약",
        "등록 상태",
      ],
      phases: ["Phase 이름", "Task"],
    }[this.view];
    const wrap = this.node("div", undefined, "table-scroll"),
      table = this.node("table"),
      head = this.node("thead"),
      tr = this.node("tr"),
      body = this.node("tbody");
    columns.forEach((c) => {
      const header = this.node("th", c);
      header.scope = "col";
      tr.append(header);
    });
    head.append(tr);
    table.append(head, body);
    const cell = (value) => {
      const td = this.node("td");
      td.append(
        typeof value === "object" && value?.nodeType
          ? value
          : this.node("span", this.plain(value)),
      );
      return td;
    };
    for (const g of groups) {
      const row = this.node("tr"),
        first = this.node("td");
      first.append(
        g.id
          ? this.detailButton(g.name, this.view, g.id)
          : this.node("span", g.name),
      );
      row.append(first);
      if (this.view === "files")
        row.append(
          cell(g.description),
          cell(this.refs(g.scenes, "scenes")),
          cell(this.refs(g.holons, "holons")),
          cell(this.refs(g.phases, "phases")),
          cell(g.plan_outline ? this.planOutline(g.plan_outline, { showCount: true }) : this.refs(g.tasks, "tasks")),
        );
      if (this.view === "scenes")
        row.append(
          cell(this.refs(g.holons, "holons")),
          cell(g.objects?.length ? g.objects.join(" · ") : "미기록"),
          cell(this.refs(g.tasks, "tasks")),
        );
      if (this.view === "holons")
        row.append(
          cell(this.refs(g.scenes, "scenes")),
          cell(this.refs(g.parent ? [g.parent] : [], "holons")),
          cell(g.object_count),
          cell(g.availability),
        );
      if (this.view === "phases")
        row.append(
          cell(
            this.refs(
              (g.tasks || []).map((t) => ({
                id: t.plan_id,
                name: t.title || t.name || "이름 미기록",
              })),
              "tasks",
            ),
          ),
        );
      [...row.cells].forEach((cell, index) => {
        cell.dataset.label = columns[index];
      });
      body.append(row);
    }
    wrap.append(table);
    this.$("domain-results").append(wrap);
  }
  async detail(kind, id, parent = "", loop = null) {
    const version = this.version,
      request = ++this.detailRequest,
      dialog = this.$("detail");
    this.$("detail-title").textContent = "상세 조회";
    this.$("detail-fields").replaceChildren(
      this.node("p", "자료를 읽고 있습니다…"),
    );
    if (!dialog.open) dialog.showModal();
    try {
      const data = await this.api(
        this.path("domain-detail", { view: kind, id, parent, ...(loop == null ? {} : { loop_no: loop }) }),
      );
      if (
        version !== this.version ||
        request !== this.detailRequest ||
        !dialog.open
      )
        return;
      this.$("detail-title").textContent = data.title;
      this.$("detail-fields").replaceChildren();
      if (loop != null)
        this.$("detail-fields").append(this.node("p",
          (loop === 0 ? "실행 전 기록 (0)" : `Loop ${loop}`) + (data.history === "partial" ? " · 일부 기록" : ""), "hint"));
      if (data.notes?.length) this.$("detail-fields").append(this.node("p", data.notes.join("\n"), "hint"));
      if (data.task) {
        this.$("detail-fields").append(
          this.node(
            "p",
            `Task · ${data.task.name} | revision · ${data.task.revision ?? "미기록"}`,
            "hint",
          ),
        );
        const context = this.node("details", undefined, "detail-context");
        context.append(
          this.node("summary", "Task context"),
          this.storedValue(data.context),
        );
        this.$("detail-fields").append(context);
      }
      for (const [key, original] of Object.entries(data.fields)) {
        this.$("detail-fields").append(
          this.field(key, original, "detail-field record-field"),
        );
      }
    } catch (error) {
      if (
        version === this.version &&
        request === this.detailRequest &&
        dialog.open
      )
        this.$("detail-fields").replaceChildren(this.node("p", error.message));
    }
  }
};
