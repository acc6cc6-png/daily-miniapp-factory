const state = {
  digest: null,
  history: [],
  usingLatest: true,
};

document.addEventListener("DOMContentLoaded", () => {
  void bootstrapFactory();
});

async function bootstrapFactory() {
  bindChromeEvents();

  try {
    const [digest, history] = await Promise.all([
      fetchJson("./data/latest/digest.json"),
      fetchJson("./data/history/index.json", []),
    ]);

    state.digest = digest;
    state.history = Array.isArray(history) ? history : [];

    renderHistory();
    renderFactory();
  } catch (error) {
    renderFactoryError(error);
  }
}

function bindChromeEvents() {
  document.querySelector("#history-open")?.addEventListener("click", () => toggleHistory(true));
  document.querySelector("#history-close")?.addEventListener("click", () => toggleHistory(false));
  document.querySelector("#history-close-button")?.addEventListener("click", () => toggleHistory(false));
}

async function fetchJson(url, fallback = null) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    if (fallback !== null) {
      return fallback;
    }
    throw error;
  }
}

function renderFactory() {
  const factory = state.digest?.miniappFactory;
  if (!factory) {
    renderFactoryError(new Error("当前快照里还没有 miniappFactory 数据"));
    return;
  }

  const plan = factory.todayPlan ?? {};
  setText("#factory-title", plan.name || "今日方案");
  setText("#factory-lead", factory.summary || "");
  setText("#factory-eyebrow", "Daily Miniapp Build");
  setText("#generated-badge", `${factory.generatedAt} 更新`);
  setText("#window-banner", `信号窗口：${factory.windowLabel}`);
  setText("#sidebar-window", factory.windowLabel);
  setText("#plan-name", plan.name || "今日自动生成小程序方案");
  setText("#plan-positioning", plan.positioning || "");
  setText("#core-need", plan.coreNeed || "");
  setText("#why-today", plan.whyToday || "");
  setText("#audience-copy", plan.audience || "");
  setText("#promotion-copy", plan.promotion || "");
  setText("#monetization-copy", plan.monetization || "");
  setText("#frontend-copy", plan.implementation?.frontend || "");
  setText("#backend-copy", plan.implementation?.backend || "");
  setText("#plan-mode", modeLabel(factory.mode));

  renderScoreGrid(factory.scores || {});
  renderTextList("#market-basis", plan.marketBasis || []);
  renderFeatureList("#features-list", plan.coreFeatures || [], "title", "detail");
  renderFeatureList("#pages-list", plan.pageStructure || [], "name", "purpose");
  renderTextList("#interaction-list", plan.interactionLogic || []);
  renderPills("#platform-list", plan.implementation?.platforms || []);
  renderEvidence(factory.evidenceSignals || []);
  renderCandidates(factory.candidateBoard || []);
  renderEngine(factory.engine || {});
  toggleLatestIndicator();
}

function renderScoreGrid(scores) {
  const container = document.querySelector("#score-grid");
  if (!container) {
    return;
  }

  const items = [
    { label: "需求强度", value: scores.demand ?? "-", tone: "is-bullish" },
    { label: "上线速度", value: scores.launch ?? "-", tone: "is-watch" },
    { label: "传播潜力", value: scores.viral ?? "-", tone: "is-bullish" },
    { label: "商业价值", value: scores.commercial ?? "-", tone: "is-bearish" },
    { label: "小程序适配", value: scores.fit ?? "-", tone: "is-watch" },
  ];

  container.innerHTML = items
    .map(
      (item) => `
        <article class="score-card">
          <span class="story-signal ${item.tone}">${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.value)}</strong>
        </article>
      `,
    )
    .join("");
}

function renderFeatureList(selector, items, titleKey, bodyKey) {
  const container = document.querySelector(selector);
  if (!container) {
    return;
  }

  container.innerHTML = items
    .map(
      (item) => `
        <article class="factory-card">
          <h4>${escapeHtml(item[titleKey] || "")}</h4>
          <p>${escapeHtml(item[bodyKey] || "")}</p>
        </article>
      `,
    )
    .join("");
}

function renderTextList(selector, items) {
  const container = document.querySelector(selector);
  if (!container) {
    return;
  }

  container.innerHTML = items
    .map(
      (item, index) => `
        <article class="stack-item">
          <span class="linkage-index">${String(index + 1).padStart(2, "0")}</span>
          <p>${escapeHtml(item)}</p>
        </article>
      `,
    )
    .join("");
}

function renderPills(selector, items) {
  const container = document.querySelector(selector);
  if (!container) {
    return;
  }

  container.innerHTML = items
    .map((item) => `<span class="source-pill source-pill--static"><span>${escapeHtml(item)}</span></span>`)
    .join("");
}

function renderEvidence(items) {
  const container = document.querySelector("#evidence-list");
  if (!container) {
    return;
  }

  container.innerHTML = items
    .map(
      (item) => `
        <article class="factory-card">
          <div class="pulse-meta">
            <span class="pulse-category">${escapeHtml(item.groupLabel || item.group || "")}</span>
            <span class="story-signal is-watch">${escapeHtml(item.source || "")}</span>
          </div>
          <h4>${escapeHtml(item.title || "")}</h4>
          <p>${escapeHtml(item.reason || "")}</p>
          <div class="story-footer">
            <span class="story-source">${escapeHtml(item.publishedAt || "时间未标注")}</span>
            <a class="story-link" href="${escapeAttribute(item.url || "#")}" target="_blank" rel="noreferrer">原文</a>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderCandidates(items) {
  const container = document.querySelector("#candidate-list");
  if (!container) {
    return;
  }

  container.innerHTML = items
    .map(
      (item) => `
        <article class="factory-card">
          <div class="pulse-meta">
            <span class="pulse-category">${escapeHtml(String(item.score ?? "-"))}</span>
            <span class="story-signal is-bullish">候选方向</span>
          </div>
          <h4>${escapeHtml(item.name || "")}</h4>
          <p>${escapeHtml(item.positioning || "")}</p>
          <p class="signal-copy">${escapeHtml(item.note || "")}</p>
        </article>
      `,
    )
    .join("");
}

function renderEngine(engine) {
  const sourceContainer = document.querySelector("#engine-source-list");
  const collection = document.querySelector("#collection-rules");
  const quality = document.querySelector("#quality-rules");
  const build = document.querySelector("#build-rules");

  if (sourceContainer) {
    sourceContainer.innerHTML = (engine.sources || [])
      .map(
        (item) => `
          <article class="factory-card factory-card--compact">
            <div class="pulse-meta">
              <span class="pulse-category">${escapeHtml(String(item.count ?? 0))} 条</span>
            </div>
            <h4>${escapeHtml(item.name || "")}</h4>
            <p>${escapeHtml((item.sources || []).join("、"))}</p>
          </article>
        `,
      )
      .join("");
  }

  renderTextList("#collection-rules", engine.collectionRules || []);
  renderTextList("#quality-rules", engine.qualityRules || []);
  renderTextList("#build-rules", engine.buildRules || []);
}

function renderHistory() {
  const container = document.querySelector("#history-list");
  if (!container) {
    return;
  }

  const items = [
    { id: "latest", label: "最新方案", path: "latest", mode: "latest" },
    ...state.history.map((item) => ({ ...item, mode: "history" })),
  ];

  container.innerHTML = items
    .map(
      (item) => `
        <div class="history-entry">
          <span class="history-badge">${item.mode === "latest" ? "Latest" : "Archive"}</span>
          <div class="history-entry-copy">${escapeHtml(item.label)}</div>
          <button class="history-entry-button" data-history-path="${escapeHtml(item.path)}" type="button">打开</button>
        </div>
      `,
    )
    .join("");

  container.querySelectorAll("[data-history-path]").forEach((button) => {
    button.addEventListener("click", async () => {
      const path = button.getAttribute("data-history-path");
      await loadEdition(path);
      toggleHistory(false);
    });
  });
}

async function loadEdition(path) {
  try {
    state.digest =
      path === "latest"
        ? await fetchJson("./data/latest/digest.json")
        : await fetchJson(`./${path}`);
    state.usingLatest = path === "latest";
    renderFactory();
  } catch (error) {
    renderFactoryError(error);
  }
}

function toggleHistory(open) {
  const modal = document.querySelector("#history-modal");
  if (!modal) {
    return;
  }
  modal.classList.toggle("hidden", !open);
  modal.setAttribute("aria-hidden", String(!open));
}

function toggleLatestIndicator() {
  const indicator = document.querySelector("#latest-indicator");
  if (!indicator) {
    return;
  }
  indicator.classList.toggle("hidden", !state.usingLatest);
}

function renderFactoryError(error) {
  console.error(error);
  setText("#factory-title", "页面加载失败");
  setText("#factory-lead", error?.message ?? "无法读取今日方案");
  setText("#window-banner", "请确认 docs/data/latest/digest.json 已生成，并且包含 miniappFactory 字段。");
  setText("#core-need", "如果这是历史快照，可能还未包含新的小程序方案结构。");
}

function modeLabel(mode) {
  return mode === "ai" ? "AI 深挖" : "规则引擎";
}

function setText(selector, value) {
  const node = document.querySelector(selector);
  if (node) {
    node.textContent = value ?? "";
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
