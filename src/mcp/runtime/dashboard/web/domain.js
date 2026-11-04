"use strict";

// Named read-only views share the existing file, authentication and detail dialog.
window.DomainExplorer = class {
  constructor({api, node, rawVisibility, busy}) {
    Object.assign(this, {api, node, rawVisibility, busy});
    this.view = "tables";
    this.schema = null;
    this.capabilities = {};
    this.version = 0;
    this.request = 0;
    this.detailRequest = 0;
    this.offset = 0;
    this.limit = 20;
    this.search = "";
    this.focus = "";
    this.labels = {tables: "전체 테이블", scenes: "Scene 조회", holons: "ontological_holon 조회", phases: "Phase", tasks: "Task"};
    document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => this.select(button.dataset.view)));
    this.$("domain-search-form").addEventListener("submit", event => {
      event.preventDefault(); this.search = this.$("domain-search").value; this.offset = 0; this.load();
    });
    this.$("domain-previous").addEventListener("click", () => { this.offset = Math.max(0, this.offset - this.limit); this.load(); });
    this.$("domain-next").addEventListener("click", () => { this.offset += this.limit; this.load(); });
    this.$("domain-show-all").addEventListener("click", () => this.select(this.view));
  }

  $(id) { return document.getElementById(id); }
  get isRaw() { return this.view === "tables"; }
  plain(value) {
    if (value === null || value === undefined || value === "") return "미기록";
    if (typeof value === "object") return (value.value ?? JSON.stringify(value)) + (value.truncated ? "… [일부 표시]" : "");
    return String(value);
  }
  name(record) { return this.plain(record.title || record.name || "이름 미기록"); }

  setSchema(schema) {
    this.schema = schema;
    this.capabilities = schema.domain_views || {};
    this.version++;
    this.offset = 0; this.focus = ""; this.search = "";
    this.$("domain-search").value = "";
    if (!this.isRaw && !this.capabilities[this.view]) this.view = "tables";
    this.updateChrome(false);
  }

  updateChrome(loadRaw) {
    this.$("view-tabs").hidden = !this.schema?.name;
    document.querySelectorAll("[data-view]").forEach(button => {
      button.setAttribute("aria-selected", String(button.dataset.view === this.view));
      button.disabled = !this.schema?.name || (button.dataset.view !== "tables" && !this.capabilities[button.dataset.view]);
      button.title = button.disabled ? "이 DB에는 이 조회에 필요한 저장 구조가 없습니다." : "";
    });
    this.$("domain-explorer").hidden = this.isRaw;
    this.$("domain-title").textContent = this.labels[this.view];
    this.$("domain-explorer").setAttribute("aria-labelledby", "view-" + this.view);
    this.$("domain-show-all").hidden = !this.focus;
    this.$("domain-search").placeholder = this.view === "tasks" ? "Task 이름·목표·scope 검색…" : `${this.labels[this.view]} 이름 검색…`;
    this.rawVisibility(this.isRaw, loadRaw);
  }

  select(view, focus = "", load = true) {
    if (this.busy() || (view !== "tables" && !this.capabilities[view])) return;
    this.view = view; this.focus = focus; this.offset = 0; this.search = "";
    this.$("domain-search").value = "";
    this.version++;
    this.$("detail").close();
    this.updateChrome(load);
    if (load && !this.isRaw) this.load();
  }

  showRaw(load = true) { this.select("tables", "", load); }
  refresh() { if (!this.isRaw) this.load(); }
  path(route, params = {}) { return `/api/${route}?` + new URLSearchParams({database: this.schema.path, view: this.view, ...params}); }

  async load() {
    if (this.isRaw || !this.schema?.name) return;
    const version = this.version, request = ++this.request;
    this.$("domain-table").replaceChildren();
    this.$("domain-note").textContent = "자료를 읽고 있습니다…";
    this.$("domain-note").classList.remove("error");
    this.$("domain-page-info").textContent = "";
    this.$("domain-previous").disabled = this.$("domain-next").disabled = true;
    try {
      const data = await this.api(this.path("domain", {search: this.search, focus: this.focus, offset: this.offset, limit: this.limit}));
      if (version !== this.version || request !== this.request) return;
      this.render(data);
      this.$("domain-note").textContent = data.notes.join("\n");
      this.$("domain-previous").disabled = this.offset === 0;
      this.$("domain-next").disabled = !data.has_more;
      this.$("domain-page-info").textContent = data.groups.length ? `${this.offset + 1}번부터 ${data.groups.length}개 항목 · ${data.has_more ? "다음 자료 있음" : "마지막 페이지"}` : "조건에 맞는 항목이 없습니다.";
      const focused = this.$("domain-table").querySelector("tr.focused-record");
      if (focused) { focused.scrollIntoView({block: "nearest"}); focused.focus({preventScroll: true}); }
    } catch (error) {
      if (version === this.version && request === this.request) {
        this.$("domain-note").textContent = error.message;
        this.$("domain-note").classList.add("error");
      }
    }
  }

  cell(value, className = "") {
    const cell = this.node("td", this.plain(value), className);
    if (value === null || value === undefined || value === "") cell.classList.add("missing-value");
    return cell;
  }
  button(name, action) {
    const button = this.node("button", name, "record-link");
    button.type = "button";
    button.addEventListener("click", event => { event.stopPropagation(); action(); });
    return button;
  }
  refs(values, view) {
    const cell = this.node("td");
    if (!values?.length) { cell.append(this.node("span", "—", "missing-value")); return cell; }
    const list = this.node("ul", undefined, "record-list");
    for (const item of values) {
      const li = this.node("li"); li.append(this.button(item.name, () => this.select(view, item.id))); list.append(li);
    }
    cell.append(list); return cell;
  }
  objects(group, recorded) {
    const cell = this.node("td");
    if (!recorded) cell.append(this.node("span", "미기록", "missing-value"));
    else if (!group.objects.length) cell.append(this.node("span", "기록된 이름 없음", "missing-value"));
    else {
      const list = this.node("ul", undefined, "record-list");
      group.objects.forEach(name => list.append(this.node("li", name)));
      cell.append(list);
    }
    return cell;
  }
  status(value) {
    const cell = this.node("td"), raw = this.plain(value);
    const labels = {pending: "대기", running: "진행 중", completed: "완료", failed: "실패", blocked: "막힘", paused: "일시정지"};
    const badge = this.node("span", labels[raw] || raw, "status-label");
    badge.dataset.status = raw; badge.title = raw; cell.append(badge); return cell;
  }
  row(kind, id, title, parent = "") {
    const row = this.node("tr"); row.tabIndex = 0; row.dataset.recordId = id;
    row.setAttribute("aria-label", title + " 상세");
    row.addEventListener("click", event => { if (!event.target.closest("button")) this.detail(kind, id, parent); });
    row.addEventListener("keydown", event => { if (event.target === row && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); this.detail(kind, id, parent); } });
    row.classList.toggle("focused-record", !!this.focus && (id === this.focus || parent === this.focus));
    return row;
  }
  parentCell(group, span, kind) {
    const cell = this.node("td", undefined, "merged-cell"); cell.rowSpan = span;
    if (group.id) cell.append(this.button(group.name, () => this.detail(kind, group.id)));
    else cell.append(this.node("strong", group.name));
    if (kind === "tasks") cell.append(this.node("span", "Rev. " + this.plain(group.revision), "record-revision"));
    return cell;
  }

  render(data) {
    const columns = {
      scenes: ["Scene 이름", "등록된 ontological_holon", "등록된 객체 이름", "Scene Task 목록"],
      holons: ["ontological_holon 이름", "Scene", "부모 Holon", "등록된 객체 이름", "객체 수 (저장 요약)", "등록 상태"],
      phases: ["Phase 이름", "Task 이름", "Revision", "Task 목표", "Scope", "상태"],
      tasks: ["Task 이름 · Revision", "Task 목표", "Scope", "Step 이름", "상태", "Step 목표"]
    }[this.view];
    const head = this.node("thead"), header = this.node("tr");
    columns.forEach(name => header.append(this.node("th", name))); head.append(header);
    this.$("domain-table").append(head);
    for (const group of data.groups) {
      const body = this.node("tbody");
      if (this.view === "scenes") {
        const row = this.row("scenes", group.id, group.name);
        const name = this.node("td"); name.append(this.button(group.name, () => this.detail("scenes", group.id)));
        row.append(name, data.capabilities.holons ? this.refs(group.holons, "holons") : this.cell("미지원"),
                   this.objects(group, data.capabilities.object_names),
                   data.capabilities.tasks ? this.refs(group.tasks, "tasks") : this.cell("미지원")); body.append(row);
      } else if (this.view === "holons") {
        const row = this.row("holons", group.id, group.name);
        row.append(this.cell(group.name), this.refs(group.scenes, "scenes"), this.refs(group.parent ? [group.parent] : [], "holons"),
                   this.objects(group, data.capabilities.object_names), this.cell(group.object_count), this.cell(group.availability)); body.append(row);
      } else if (this.view === "phases") {
        const tasks = group.tasks.length ? group.tasks : [null];
        tasks.forEach((task, index) => {
          const row = task ? this.row("tasks", task.plan_id, this.name(task)) : this.node("tr");
          row.dataset.phaseId = group.id || "";
          if (!index) row.append(this.parentCell(group, tasks.length, "phases"));
          if (task) row.append(this.refs([{id: task.plan_id, name: this.name(task)}], "tasks"), this.cell(task.revision), this.cell(task.goal), this.cell(task.scope), this.status(task.status));
          else { const empty = this.cell("등록된 Task 없음", "missing-value"); empty.colSpan = 5; row.append(empty); }
          body.append(row);
        });
      } else {
        const steps = group.steps.length ? group.steps : [null];
        steps.forEach((step, index) => {
          const row = step ? this.row("steps", step.id, step.name, group.id) : this.row("tasks", group.id, group.name);
          row.dataset.taskId = group.id;
          if (!index) {
            const goal = this.cell(group.goal, "merged-cell"), scope = this.cell(group.scope, "merged-cell");
            goal.rowSpan = scope.rowSpan = steps.length;
            row.append(this.parentCell(group, steps.length, "tasks"), goal, scope);
          }
          if (step) {
            const name = this.node("td", undefined, "step-heading");
            name.append(this.button(step.name, () => this.detail("steps", step.id, group.id)), this.node("span", String(index + 1), "step-order"));
            row.append(name, this.status(step.status), this.cell(step.goal));
          } else { const empty = this.cell(data.capabilities.steps ? "등록된 Step 없음" : "Step 저장 구조 없음", "missing-value"); empty.colSpan = 3; row.append(empty); }
          body.append(row);
        });
      }
      this.$("domain-table").append(body);
    }
  }

  async detail(kind, id, parent = "") {
    const version = this.version, request = ++this.detailRequest;
    const dialog = this.$("detail");
    dialog.querySelector("h2").textContent = "상세 조회";
    this.$("detail-fields").replaceChildren(this.node("p", "자료를 읽고 있습니다…"));
    if (!dialog.open) dialog.showModal();
    try {
      const data = await this.api(this.path("domain-detail", {view: kind, id, parent}));
      if (version !== this.version || request !== this.detailRequest || !dialog.open) return;
      dialog.querySelector("h2").textContent = data.title;
      this.$("detail-fields").replaceChildren();
      for (const [key, original] of Object.entries(data.fields)) {
        let value = original;
        if (key.endsWith("_json") && typeof value === "string") { try { value = JSON.parse(value); } catch {} }
        const field = this.node("section", undefined, "detail-field"); field.append(this.node("h3", key));
        field.append(this.node(typeof value === "object" && value !== null ? "pre" : "p",
                               typeof value === "object" && value !== null ? JSON.stringify(value, null, 2) : this.plain(value)));
        this.$("detail-fields").append(field);
      }
    } catch (error) {
      if (version === this.version && request === this.detailRequest && dialog.open) this.$("detail-fields").replaceChildren(this.node("p", error.message));
    }
  }
};
