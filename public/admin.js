const uploadForm = document.querySelector("#uploadForm");
const uploadMessage = document.querySelector("#uploadMessage");
const adminList = document.querySelector("#adminList");
const refreshButton = document.querySelector("#refreshButton");

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
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function showMessage(text, type = "ok") {
  uploadMessage.textContent = text;
  uploadMessage.dataset.type = type;
}

async function fetchReports() {
  const response = await fetch("/shinen/api/reports");
  const data = await response.json();
  return data.reports || [];
}

function renderAdminList(reports) {
  if (!reports.length) {
    adminList.innerHTML = `<p class="empty-state">还没有上传报告。</p>`;
    return;
  }

  adminList.innerHTML = reports.map((report) => `
    <article class="admin-item" data-id="${escapeHtml(report.id)}">
      <div class="admin-item-meta">
        <strong>${escapeHtml(report.originalName)}</strong>
        <span>${formatDate(report.createdAt)}</span>
      </div>
      <label>
        标题
        <input name="title" value="${escapeHtml(report.title || "")}">
      </label>
      <label>
        分类
        <input name="category" value="${escapeHtml(report.category || "")}">
      </label>
      <label>
        说明
        <input name="description" value="${escapeHtml(report.description || "")}">
      </label>
      <div class="admin-actions">
        <a href="/shinen/uploads/${encodeURIComponent(report.filename)}" target="_blank" rel="noreferrer">查看 PDF</a>
        <button type="button" data-action="save">保存修改</button>
        <button type="button" data-action="delete" class="danger-button">删除</button>
      </div>
    </article>
  `).join("");
}

async function loadAdminReports() {
  renderAdminList(await fetchReports());
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage("正在上传...");
  const formData = new FormData(uploadForm);

  try {
    const response = await fetch("/shinen/api/reports", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "上传失败");
    uploadForm.reset();
    showMessage("上传成功");
    await loadAdminReports();
  } catch (error) {
    showMessage(error.message, "error");
  }
});

adminList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const item = button.closest(".admin-item");
  const id = item.dataset.id;

  if (button.dataset.action === "delete") {
    if (!confirm("确定删除这份报告吗？")) return;
    const response = await fetch(`/shinen/api/reports/${id}`, { method: "DELETE" });
    if (!response.ok) {
      alert("删除失败");
      return;
    }
    await loadAdminReports();
    return;
  }

  const payload = {
    title: item.querySelector('input[name="title"]').value,
    category: item.querySelector('input[name="category"]').value,
    description: item.querySelector('input[name="description"]').value,
  };
  const response = await fetch(`/shinen/api/reports/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    alert("保存失败");
    return;
  }
  showMessage("修改已保存");
  await loadAdminReports();
});

refreshButton.addEventListener("click", loadAdminReports);

loadAdminReports();
