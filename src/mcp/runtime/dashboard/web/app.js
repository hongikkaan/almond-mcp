"use strict";
const $ = (id) => document.getElementById(id);
const node = (tag, text, className) => {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
};
let token =
  location.hash.slice(1) || sessionStorage.getItem("dashboard-token") || "";
if (token) sessionStorage.setItem("dashboard-token", token);
history.replaceState(null, "", location.pathname);
async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "X-Dashboard-Token": token,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "조회하지 못했습니다.");
  return result;
}
function message(text = "", error = false) {
  $("message").textContent = text;
  $("message").hidden = !text;
  $("message").classList.toggle("error", error);
}
const explorer = new DomainExplorer({ api, node, notify: message });
let loading = false;
async function loadSchema(pick = false) {
  if (loading) return;
  loading = true;
  $("open-button").disabled = $("refresh").disabled = true;
  try {
    const schema = await api(
      pick ? "/api/pick" : "/api/schema",
      pick ? {} : undefined,
    );
    if (schema.cancelled) return;
    message();
    $("database-name").textContent = schema.name || "DB를 선택하세요";
    $("database-name").title = schema.path || "";
    $("database-meta").textContent = schema.name
      ? `${schema.name} · ${schema.path}`
      : "로컬 읽기 전용";
    await explorer.setSchema(schema);
  } catch (error) {
    message(error.message, true);
  } finally {
    loading = false;
    $("open-button").disabled = false;
    $("refresh").disabled = !explorer.schema?.name;
  }
}
$("open-button").addEventListener("click", () => loadSchema(true));
$("refresh").addEventListener("click", () => loadSchema());
$("close-detail").addEventListener("click", () => $("detail").close());
$("detail").addEventListener("click", (event) => {
  const rect = $("detail").getBoundingClientRect();
  if (
    event.target === $("detail") &&
    (event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom)
  )
    $("detail").close();
});
loadSchema();
