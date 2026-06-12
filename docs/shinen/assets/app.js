const state = {
  reports: [],
  activeCategory: "全部",
  search: "",
};

const categoryTabs = document.querySelector("#categoryTabs");
const reportGroups = document.querySelector("#reportGroups");
const emptyState = document.querySelector("#emptyState");
const searchInput = document.querySelector("#searchInput");
const totalCount = document.querySelector("#totalCount");
const categoryCount = document.querySelector("#categoryCount");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

function categories() {
  return [...new Set(state.reports.map((report) => report.category || "未分类"))].sort((a, b) => a.localeCompare(b, "zh-CN"));
}

function filteredReports() {
  const query = state.search.trim().toLowerCase();
  return state.reports.filter((report) => {
    const inCategory = state.activeCategory === "全部" || report.category === state.activeCategory;
    const haystack = `${report.title} ${report.category} ${report.description || ""}`.toLowerCase();
    return inCategory && (!query || haystack.includes(query));
  });
}

function renderTabs() {
  const tabs = ["全部", ...categories()];
  categoryTabs.innerHTML = tabs.map((category) => {
    const active = category === state.activeCategory ? "active" : "";
    return `<button class="${active}" type="button" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`;
  }).join("");
}

function renderReports() {
  totalCount.textContent = state.reports.length;
  categoryCount.textContent = categories().length;

  const reports = filteredReports();
  emptyState.hidden = reports.length > 0;
  const grouped = reports.reduce((groups, report) => {
    const category = report.category || "未分类";
    groups[category] = groups[category] || [];
    groups[category].push(report);
    return groups;
  }, {});

  reportGroups.innerHTML = Object.entries(grouped).map(([category, items]) => `
    <section class="report-section">
      <div class="section-heading">
        <h2>${escapeHtml(category)}</h2>
        <span>${items.length} 份</span>
      </div>
      <div class="report-grid">
        ${items.map((report) => `
          <article class="report-card">
            <div class="pdf-mark">PDF</div>
            <div class="report-copy">
              <h3>${escapeHtml(report.title)}</h3>
              <p>${escapeHtml(report.description || "检测报告")}</p>
              <span>上传时间：${formatDate(report.createdAt)}</span>
            </div>
            <div class="report-actions">
              <a href="uploads/${encodeURIComponent(report.filename)}" target="_blank" rel="noreferrer">预览</a>
              <a href="uploads/${encodeURIComponent(report.filename)}" download>下载</a>
            </div>
          </article>
        `).join("")}
      </div>
    </section>
  `).join("");
}

async function loadReports() {
  const response = await fetch("data/reports.json");
  state.reports = await response.json();
  renderTabs();
  renderReports();
}

categoryTabs.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-category]");
  if (!button) return;
  state.activeCategory = button.dataset.category;
  renderTabs();
  renderReports();
});

searchInput.addEventListener("input", (event) => {
  state.search = event.target.value;
  renderReports();
});

loadReports();
