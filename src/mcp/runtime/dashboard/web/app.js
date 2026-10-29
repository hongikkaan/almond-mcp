"use strict";

const $ = id => document.getElementById(id);
const node = (tag, text, className) => {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
};
let token = location.hash.slice(1) || sessionStorage.getItem("dashboard-token") || "";
if (token) sessionStorage.setItem("dashboard-token", token);
history.replaceState(null, "", location.pathname);
const state = {schema: null, table: null, tab: "rows", offset: 0, search: "", sort: "", descending: false, epoch: 0, request: 0, loadingSchema: false};
const format = n => Number(n).toLocaleString("ko-KR", {maximumFractionDigits: 2});

function message(text = "", error = false) {
  $("message").textContent = text;
  $("message").hidden = !text;
  $("message").classList.toggle("error", error);
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {"X-Dashboard-Token": token, ...(body === undefined ? {} : {"Content-Type": "application/json"})},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "조회하지 못했습니다.");
  return result;
}

function visibleTables() {
  return (state.schema?.tables || []).filter(t => $("show-internal").checked || !t.internal);
}

function renderNavigation() {
  const tables = visibleTables();
  const search = $("table-filter").value.toLocaleLowerCase();
  $("table-count").textContent = tables.length;
  $("metric-tables").textContent = tables.length;
  $("metric-columns").textContent = format(tables.reduce((n, t) => n + t.columns.length, 0));
  $("metric-relations").textContent = format(tables.reduce((n, t) => n + new Set(t.relations.map(r => r.id)).size, 0));
  $("tables").replaceChildren();
  for (const table of tables.filter(t => t.name.toLocaleLowerCase().includes(search))) {
    const button = node("button", undefined, "table-nav" + (table.name === state.table?.name ? " active" : ""));
    button.title = table.name;
    button.setAttribute("aria-current", table.name === state.table?.name ? "true" : "false");
    button.append(node("span", table.type === "view" ? "◈" : "▦"), node("span", table.name, "nav-name"), node("span", table.columns.length, "nav-count"));
    button.addEventListener("click", () => activateTable(table));
    $("tables").append(button);
  }
  if (!$("tables").childElementCount) $("tables").append(node("p", "표시할 테이블이 없습니다.", "sidebar-empty"));
}

function applySchema(schema) {
  const previous = state.table?.name;
  state.schema = schema;
  state.epoch++;
  $("refresh").disabled = !schema.name;
  $("database-name").textContent = schema.name || "아직 선택된 파일이 없습니다";
  $("database-meta").textContent = schema.name ? `${format(schema.bytes / 1024)} KB · 구조 v${schema.schema_version} · ${schema.path}` : "SQLite · .db / .sqlite / .sqlite3 / 확장자 없는 DB";
  if (schema.path) $("db-path").value = schema.path;
  renderNavigation();
  const tables = visibleTables();
  activateTable(tables.find(t => t.name === previous) || tables[0] || null);
  if (schema.name && !tables.length) message("열린 DB에 표시할 테이블이 없습니다. 필요하면 SQLite 내부 테이블 포함을 선택하세요.");
}

async function loadSchema(body) {
  if (state.loadingSchema) return;
  state.loadingSchema = true;
  const epoch = ++state.epoch;
  $("open-button").disabled = true;
  $("refresh").disabled = true;
  message("파일 구조를 읽고 있습니다…");
  try {
    const schema = await api(body ? "/api/open" : "/api/schema", body);
    if (epoch !== state.epoch) return;
    message();
    state.loadingSchema = false;
    applySchema(schema);
  } catch (error) {
    if (epoch === state.epoch) message(error.message, true);
  } finally {
    state.loadingSchema = false;
    $("open-button").disabled = false;
    $("refresh").disabled = !state.schema?.name;
  }
}

function activateTable(table) {
  if (state.loadingSchema) return;
  state.epoch++;
  state.table = table;
  state.offset = 0;
  state.search = "";
  state.sort = "";
  state.descending = false;
  $("row-search").value = "";
  $("detail").close();
  $("empty").hidden = !!table;
  $("explorer").hidden = !table;
  renderNavigation();
  if (!table) return;
  $("table-name").textContent = table.name;
  $("table-kind").textContent = (table.kind || table.type).toUpperCase();
  $("column-count").textContent = `${table.columns.length}개 열`;
  showTab(state.tab);
}

function showTab(tab) {
  state.tab = tab;
  for (const name of ["rows", "charts", "schema"]) {
    $("panel-" + name).hidden = name !== tab;
    $("tab-" + name).setAttribute("aria-selected", String(name === tab));
  }
  if (!state.table) return;
  if (tab === "rows") loadRows();
  if (tab === "charts") loadCharts();
  if (tab === "schema") { state.request++; renderStructure(); }
}

function queryPath(route, extra = {}) {
  return `/api/${route}?` + new URLSearchParams({database: state.schema.path, table: state.table.name, ...extra});
}

function cellText(cell) {
  if (cell === null) return "NULL";
  if (typeof cell === "object") {
    if (cell.kind === "blob") return `BLOB · ${format(cell.bytes)} bytes`;
    return cell.value + (cell.truncated ? "… [일부 표시]" : "");
  }
  return String(cell);
}

function jsonValue(value) {
  if (typeof value !== "string" || !/^[\s]*[\[{]/.test(value)) return null;
  try { return JSON.parse(value); } catch { return null; }
}

async function loadRows() {
  const epoch = state.epoch, request = ++state.request;
  $("data-table").replaceChildren();
  $("row-note").textContent = "자료를 읽고 있습니다…";
  $("page-info").textContent = "";
  $("previous").disabled = true;
  $("next").disabled = true;
  try {
    const data = await api(queryPath("rows", {offset: state.offset, search: state.search, sort: state.sort, descending: state.descending}));
    if (epoch !== state.epoch || request !== state.request) return;
    message();
    $("row-note").textContent = data.omitted_columns ? `처음 128개 열만 표시합니다. 나머지 ${data.omitted_columns}개 열의 정의는 구조와 관계에서 확인하세요.` : "";
    const head = node("thead"), header = node("tr"), body = node("tbody");
    header.append(node("th", "#"));
    for (const col of data.columns) {
      const th = node("th"), button = node("button", col.name + (state.sort === col.name ? (state.descending ? " ↓" : " ↑") : ""));
      button.title = `${col.name} 정렬`;
      button.addEventListener("click", () => {
        state.descending = state.sort === col.name ? !state.descending : false;
        state.sort = col.name; state.offset = 0; loadRows();
      });
      th.append(button, node("span", `${col.pk ? "PK · " : ""}${col.type || "ANY"}`, "column-type"));
      header.append(th);
    }
    head.append(header);
    data.rows.forEach((row, i) => {
      const tr = node("tr");
      tr.tabIndex = 0;
      tr.setAttribute("aria-label", `${data.offset + i + 1}번째 행 상세`);
      tr.append(node("td", format(data.offset + i + 1), "null"));
      for (const cell of row) {
        const text = cellText(cell), td = node("td", text.length > 150 ? text.slice(0, 150) + "…" : text);
        if (cell === null) td.className = "null";
        if (jsonValue(cell) !== null) td.className = "json-value";
        tr.append(td);
      }
      const open = () => showDetail(data.columns, row, data.offset + i + 1);
      tr.addEventListener("click", open);
      tr.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); } });
      body.append(tr);
    });
    $("data-table").append(head, body);
    if (!data.rows.length) $("row-note").textContent = state.search ? "검색 결과가 없습니다. 검색어를 지우고 다시 검색해 보세요." : "이 테이블에는 아직 자료가 없습니다.";
    $("page-info").textContent = data.rows.length ? `${format(data.offset + 1)}–${format(data.offset + data.rows.length)}행 표시 · 페이지당 50행${data.has_more ? " · 다음 자료 있음" : " · 마지막 페이지"}` : "0행 표시";
    $("previous").disabled = state.offset === 0;
    $("next").disabled = !data.has_more;
  } catch (error) {
    if (epoch === state.epoch && request === state.request) { $("row-note").textContent = "자료를 불러오지 못했습니다."; message(error.message, true); }
  }
}

function showDetail(columns, row, index) {
  $("detail").querySelector("h2").textContent = `${state.table.name} · ${index}행`;
  $("detail-fields").replaceChildren();
  columns.forEach((col, i) => {
    const field = node("section", undefined, "detail-field");
    field.append(node("h3", `${col.name} · ${col.type || "ANY"}${col.pk ? " · PK" : ""}`));
    const cell = row[i], parsed = jsonValue(cell);
    if (parsed !== null) {
      const details = node("details"); details.open = true;
      details.append(node("summary", "JSON 펼쳐 보기"), node("pre", JSON.stringify(parsed, null, 2)));
      field.append(details);
    } else if (cell?.kind === "blob") {
      field.append(node("p", `${format(cell.bytes)} bytes · 처음 32 bytes (16진수)`), node("pre", cell.hex));
    } else {
      field.append(node("p", cellText(cell), cell === null ? "null" : ""));
      if (cell?.truncated) field.append(node("p", `전체 ${format(cell.characters)}자 중 처음 8,192자만 표시합니다.`, "hint"));
    }
    $("detail-fields").append(field);
  });
  $("detail").showModal();
}

function histogram(values) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 400 130"); svg.setAttribute("class", "histogram");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", `숫자 구간별 표본 수: ${values.join(", ")}`);
  const max = Math.max(...values, 1), width = 400 / values.length;
  values.forEach((value, i) => {
    const rect = document.createElementNS(svg.namespaceURI, "rect"), height = value / max * 120;
    for (const [key, val] of Object.entries({x: i * width + 3, y: 130 - height, width: width - 6, height, rx: 3})) rect.setAttribute(key, val);
    const title = document.createElementNS(svg.namespaceURI, "title"); title.textContent = `${i + 1}구간 · ${value}행`;
    rect.append(title); svg.append(rect);
  });
  return svg;
}

async function loadCharts() {
  const epoch = state.epoch, request = ++state.request;
  $("charts").replaceChildren(); $("sample-note").textContent = "표본 자료를 읽고 있습니다…";
  try {
    const data = await api(queryPath("profile"));
    if (epoch !== state.epoch || request !== state.request) return;
    message();
    $("sample-note").textContent = `검색·정렬과 무관한 처음 ${data.sample_size}행의 표본입니다${data.has_more ? " (최대 300행, 전체 통계 아님)" : ""}. 숫자는 분포, 반복되는 짧은 텍스트는 빈도를 자동으로 표시합니다.`;
    if (data.omitted_columns) $("sample-note").append(document.createTextNode(` 처음 128개 열을 분석했습니다 (${data.omitted_columns}개 열 제외).`));
    let omitted = 0;
    for (const col of data.columns) {
      if (col.kind !== "number" && !(col.kind === "category" && col.top.length && (col.distinct <= 12 || col.top[0].count > 1))) { omitted++; continue; }
      const card = node("article", undefined, "chart-card");
      card.append(node("h3", col.name));
      if (col.kind === "number") {
        card.append(node("div", `숫자 분포 · 평균 ${format(col.mean)} · 빈 값 ${col.nulls}`, "chart-sub"), histogram(col.bins));
        const range = node("div", undefined, "chart-range"); range.append(node("span", `최소 ${format(col.minimum)}`), node("span", `최대 ${format(col.maximum)}`)); card.append(range);
      } else {
        card.append(node("div", `표본 내 ${col.distinct}종 · 상위 8개 · 빈 값 ${col.nulls}${col.excluded_long ? ` · 긴 텍스트 ${col.excluded_long}개 제외` : ""}`, "chart-sub"));
        for (const item of col.top) {
          const row = node("div", undefined, "chart-row"), label = node("span", item.label || "(빈 문자열)", "chart-label"), meter = node("meter");
          label.title = item.label; meter.min = 0; meter.max = data.sample_size || 1; meter.value = item.count;
          meter.setAttribute("aria-label", `${item.label}: ${item.count}행`);
          row.append(label, meter, node("span", item.count)); card.append(row);
        }
      }
      $("charts").append(card);
    }
    if (!$("charts").childElementCount) $("charts").append(node("p", "이 표본에는 차트로 묶을 숫자나 반복 범주가 없습니다. 자료 보기에서 개별 값과 JSON을 살펴보세요.", "section-note"));
    if (omitted) $("sample-note").append(document.createTextNode(` 고유 식별자·JSON·긴 텍스트·바이너리 등 ${omitted}개 열은 차트를 생략했습니다. JSON은 행 상세에서 펼쳐 볼 수 있습니다.`));
  } catch (error) {
    if (epoch === state.epoch && request === state.request) { $("sample-note").textContent = "표본을 불러오지 못했습니다."; message(error.message, true); }
  }
}

function renderStructure() {
  const table = state.table;
  $("relations").replaceChildren();
  for (const source of state.schema.tables) {
    const grouped = new Map();
    for (const relation of source.relations) {
      if (source.name !== table.name && relation.target !== table.name) continue;
      if (!grouped.has(relation.id)) grouped.set(relation.id, []);
      grouped.get(relation.id).push(relation);
    }
    for (const group of grouped.values()) {
      group.sort((a, b) => a.sequence - b.sequence);
      const relation = group[0], card = node("div", undefined, "relation");
      for (const [index, name] of [source.name, relation.target].entries()) {
        if (index) card.append(node("span", "→", "relation-arrow"));
        const button = node("button", name);
        button.append(node("small", group.map(r => index ? (r.to || "PRIMARY KEY") : r.from).join(", ")));
        button.title = `${name} · ${group.map(r => index ? (r.to || "PRIMARY KEY") : r.from).join(", ")}`;
        const target = state.schema.tables.find(t => t.name === name);
        button.disabled = !target;
        button.addEventListener("click", () => activateTable(target));
        card.append(button);
      }
      $("relations").append(card);
    }
  }
  if (!$("relations").childElementCount) $("relations").append(node("p", "이 테이블에 선언된 외래키 연결이 없습니다.", "section-note"));
  const head = node("thead"), header = node("tr"), body = node("tbody");
  for (const title of ["열 이름", "자료형", "키", "NULL 제약", "기본값 / 생성 열"]) header.append(node("th", title));
  head.append(header);
  for (const col of table.columns) {
    const row = node("tr");
    for (const value of [col.name, col.type || "ANY", col.pk ? `PK ${col.pk}` : "—", col.not_null ? "NOT NULL" : "명시 없음", col.hidden ? `생성/숨김 열 (${col.hidden})` : (col.default ?? "—")]) row.append(node("td", value));
    body.append(row);
  }
  $("schema-table").replaceChildren(head, body);
  $("table-sql").textContent = table.sql || "정의 SQL 없음";
}

$("open-form").addEventListener("submit", event => { event.preventDefault(); loadSchema({path: $("db-path").value}); });
$("refresh").addEventListener("click", () => loadSchema());
$("table-filter").addEventListener("input", renderNavigation);
$("show-internal").addEventListener("change", () => {
  renderNavigation();
  if (!visibleTables().some(t => t.name === state.table?.name)) activateTable(visibleTables()[0] || null);
});
$("search-form").addEventListener("submit", event => { event.preventDefault(); state.search = $("row-search").value; state.offset = 0; loadRows(); });
$("previous").addEventListener("click", () => { state.offset = Math.max(0, state.offset - 50); loadRows(); });
$("next").addEventListener("click", () => { state.offset += 50; loadRows(); });
$("close-detail").addEventListener("click", () => $("detail").close());
document.querySelectorAll("[data-tab]").forEach(button => button.addEventListener("click", () => showTab(button.dataset.tab)));
loadSchema();
