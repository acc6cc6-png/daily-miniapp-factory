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

  const dailyBrief = factory.dailyBrief ?? {};

  setText("#factory-title", factory.title || "今日可造清单");
  setText("#factory-lead", factory.summary || "");
  setText("#factory-eyebrow", "Daily Creation Board");
  setText("#generated-badge", `${factory.generatedAt || "-"} 更新`);
  setText("#window-banner", `信号窗口：${factory.windowLabel || "-"}`);
  setText("#sidebar-window", factory.windowLabel || "-");
  setText("#headline-copy", dailyBrief.headline || "");
  setText("#policy-copy", dailyBrief.buildPolicy || "");
  setText("#schedule-copy", dailyBrief.schedule || "");
  setText("#mode-copy", modeLabel(factory.mode));
  setText("#mode-chip", modeLabel(factory.mode));

  renderScoreGrid(factory.scorecard || {});
  renderTextList("#shift-list", dailyBrief.marketShifts || []);
  renderCreations(factory.todayCreations || []);
  renderEvidence(factory.evidenceSignals || []);
  renderEngine(factory.engine || {});
  toggleLatestIndicator();
}

function renderScoreGrid(scorecard) {
  const container = document.querySelector("#score-grid");
  if (!container) {
    return;
  }

  const items = [
    { label: "变化强度", value: scorecard.change ?? "-", tone: "is-watch" },
    { label: "需求缺口", value: scorecard.demand ?? "-", tone: "is-bullish" },
    { label: "可造性", value: scorecard.build ?? "-", tone: "is-bullish" },
    { label: "想象空间", value: scorecard.bold ?? "-", tone: "is-watch" },
    { label: "AI 杠杆", value: scorecard.ai ?? "-", tone: "is-bullish" },
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

function renderCreations(items) {
  const container = document.querySelector("#creation-list");
  if (!container) {
    return;
  }

  container.innerHTML = items
    .map((item, index) => renderCreationCard(item, index))
    .join("");

  container.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.getAttribute("data-copy-target"));
      if (!target) {
        return;
      }

      try {
        await navigator.clipboard.writeText(target.textContent || "");
        const original = button.textContent;
        button.textContent = "已复制";
        window.setTimeout(() => {
          button.textContent = original;
        }, 1400);
      } catch (error) {
        console.error(error);
      }
    });
  });
}

function renderCreationCard(item, index) {
  const promptId = `creation-prompt-${index}`;
  return `
    <article class="factory-card creation-card">
      <div class="section-head creation-head">
        <div>
          <p class="eyebrow">Creation ${String(index + 1).padStart(2, "0")}</p>
          <h3>${escapeHtml(item.name || "")}</h3>
          <p class="signal-copy">${escapeHtml(item.tagline || "")}</p>
        </div>
        <div class="pill-list creation-metrics">
          <span class="source-pill source-pill--static"><span>${escapeHtml(item.aiBuildability || "")}</span></span>
          <span class="source-pill source-pill--static"><span>需求 ${escapeHtml(item.scores?.demand ?? "-")}</span></span>
          <span class="source-pill source-pill--static"><span>可造 ${escapeHtml(item.scores?.buildability ?? "-")}</span></span>
          <span class="source-pill source-pill--static"><span>大胆 ${escapeHtml(item.scores?.boldness ?? "-")}</span></span>
        </div>
      </div>

      <div class="summary-stack">
        <div class="summary-block">
          <span class="summary-label">因为发生了什么</span>
          <p>${escapeHtml(item.because || "")}</p>
        </div>
        <div class="summary-block">
          <span class="summary-label">所以今天造什么</span>
          <p>${escapeHtml(item.createWhat || "")}</p>
        </div>
        <div class="summary-block">
          <span class="summary-label">为什么现在就能做</span>
          <p>${escapeHtml(item.whyNow || "")}</p>
        </div>
      </div>

      <div class="creation-grid">
        <div class="creation-column">
          <p class="section-mini-title">适合谁用</p>
          <div class="summary-block">
            <p>${escapeHtml(item.targetUsers || "")}</p>
          </div>
        </div>
        <div class="creation-column">
          <p class="section-mini-title">典型场景</p>
          <div class="summary-block">
            <p>${escapeHtml(item.scene || "")}</p>
          </div>
        </div>
      </div>

      <div class="creation-grid">
        <div class="creation-column">
          <p class="section-mini-title">核心模块</p>
          <div class="card-list card-list--compact">
            ${(item.coreModules || [])
              .map(
                (module) => `
                  <article class="factory-card factory-card--compact">
                    <h4>${escapeHtml(module.title || "")}</h4>
                    <p>${escapeHtml(module.detail || "")}</p>
                  </article>
                `,
              )
              .join("")}
          </div>
        </div>
        <div class="creation-column">
          <p class="section-mini-title">页面结构</p>
          <div class="card-list card-list--compact">
            ${(item.pageStructure || [])
              .map(
                (page) => `
                  <article class="factory-card factory-card--compact">
                    <h4>${escapeHtml(page.name || "")}</h4>
                    <p>${escapeHtml(page.purpose || "")}</p>
                  </article>
                `,
              )
              .join("")}
          </div>
        </div>
      </div>

      <div class="creation-grid">
        <div class="creation-column">
          <p class="section-mini-title">关键流程</p>
          <div class="stack-list">
            ${(item.workflow || [])
              .map(
                (line, workflowIndex) => `
                  <article class="stack-item">
                    <span class="linkage-index">${String(workflowIndex + 1).padStart(2, "0")}</span>
                    <p>${escapeHtml(line)}</p>
                  </article>
                `,
              )
              .join("")}
          </div>
        </div>
        <div class="creation-column">
          <p class="section-mini-title">首发实现</p>
          <div class="summary-stack creation-delivery">
            <div class="summary-block">
              <span class="summary-label">首版边界</span>
              <p>${escapeHtml(item.firstVersion || "")}</p>
            </div>
            <div class="summary-block">
              <span class="summary-label">前端</span>
              <p>${escapeHtml(item.delivery?.frontend || "")}</p>
            </div>
            <div class="summary-block">
              <span class="summary-label">后端</span>
              <p>${escapeHtml(item.delivery?.backend || "")}</p>
            </div>
            <div class="summary-block">
              <span class="summary-label">首发平台</span>
              <div class="pill-list">
                ${(item.delivery?.platforms || [])
                  .map((platform) => `<span class="source-pill source-pill--static"><span>${escapeHtml(platform)}</span></span>`)
                  .join("")}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="creation-grid">
        <div class="creation-column">
          <p class="section-mini-title">怎么推广</p>
          <div class="summary-block">
            <p>${escapeHtml(item.launchPlan || "")}</p>
          </div>
        </div>
        <div class="creation-column">
          <p class="section-mini-title">怎么赚钱</p>
          <div class="summary-block">
            <p>${escapeHtml(item.monetization || "")}</p>
          </div>
        </div>
      </div>

      <div class="summary-block prompt-block">
        <div class="prompt-toolbar">
          <span class="summary-label">给 AI 的接力提示词</span>
          <button class="ghost-button" type="button" data-copy-target="${escapeAttribute(promptId)}">复制提示词</button>
        </div>
        <pre class="prompt-box" id="${escapeAttribute(promptId)}">${escapeHtml(item.aiBuildPrompt || "")}</pre>
      </div>

      <div class="creation-source-list">
        ${(item.sources || [])
          .map(
            (source) => `
              <article class="factory-card factory-card--compact">
                <div class="pulse-meta">
                  <span class="pulse-category">${escapeHtml(source.groupLabel || "")}</span>
                  <span class="story-signal is-watch">${escapeHtml(source.source || "")}</span>
                </div>
                <h4>${escapeHtml(source.title || "")}</h4>
                <p>${escapeHtml(source.reason || "")}</p>
                <div class="story-footer">
                  <span class="story-source">${escapeHtml(source.publishedAt || "时间未标注")}</span>
                  <a class="story-link" href="${escapeAttribute(source.url || "#")}" target="_blank" rel="noreferrer">原文</a>
                </div>
              </article>
            `,
          )
          .join("")}
      </div>
    </article>
  `;
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

function renderEngine(engine) {
  const sourceContainer = document.querySelector("#engine-source-list");
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

function renderHistory() {
  const container = document.querySelector("#history-list");
  if (!container) {
    return;
  }

  const items = [
    { id: "latest", label: "最新结果", path: "latest", mode: "latest" },
    ...state.history.map((item) => ({ ...item, mode: "history" })),
  ];

  container.innerHTML = items
    .map(
      (item) => `
        <div class="history-entry">
          <span class="history-badge">${item.mode === "latest" ? "Latest" : "Archive"}</span>
          <div class="history-entry-copy">${escapeHtml(item.label)}</div>
          <button class="history-entry-button" data-history-path="${escapeAttribute(item.path)}" type="button">打开</button>
        </div>
      `,
    )
    .join("");

  container.querySelectorAll("[data-history-path]").forEach((button) => {
    button.addEventListener("click", async () => {
      const path = button.getAttribute("data-history-path");
      if (!path) {
        return;
      }

      try {
        if (path === "latest") {
          state.digest = await fetchJson("./data/latest/digest.json");
          state.usingLatest = true;
        } else {
          state.digest = await fetchJson(`./data/${path}`);
          state.usingLatest = false;
        }
        renderFactory();
        toggleHistory(false);
      } catch (error) {
        renderFactoryError(error);
      }
    });
  });
}

function toggleHistory(open) {
  const modal = document.querySelector("#history-modal");
  if (!modal) {
    return;
  }

  modal.classList.toggle("hidden", !open);
  modal.setAttribute("aria-hidden", open ? "false" : "true");
}

function toggleLatestIndicator() {
  const chip = document.querySelector("#latest-indicator");
  if (!chip) {
    return;
  }
  chip.textContent = state.usingLatest ? "Latest" : "Archive";
}

function renderFactoryError(error) {
  console.error(error);
  setText("#factory-title", "生成结果读取失败");
  setText("#factory-lead", "请确认 docs/data/latest/digest.json 已生成，并且包含 miniappFactory 字段。");
  setText("#window-banner", "当前无法读取今日可造清单。");
}

function modeLabel(mode) {
  if (mode === "ai") {
    return "AI 强化";
  }
  return "规则引擎";
}

function setText(selector, value) {
  const element = document.querySelector(selector);
  if (element) {
    element.textContent = value || "";
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
