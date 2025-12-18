const REFRESH_INTERVAL = 1000;  // 1 second - balance between responsiveness and smoothness
const LEADERBOARD_REFRESH_INTERVAL = 5000;

const knownDevices = new Map();
let currentTab = 'devices';
let leaderboardInterval;
const LEVELS = Array.from({ length: 8 }, (_, idx) => idx + 1);
const LEVEL_BTN_ENABLED =
  "level-btn bg-sky-600 hover:bg-sky-500 text-gray-50 font-medium px-2.5 py-1 rounded-md text-sm transition-colors";
const LEVEL_BTN_DISABLED =
  "level-btn bg-gray-700 opacity-60 cursor-not-allowed text-gray-300 font-medium px-2.5 py-1 rounded-md text-sm";

async function fetchDevices() {
  const res = await fetch("devices");
  return res.json();
}

async function fetchLeaderboard() {
  const res = await fetch("leaderboard");
  return res.json();
}

function showTab(tab) {
  currentTab = tab;
  document.getElementById('devices').classList.toggle('hidden', tab !== 'devices');
  document.getElementById('leaderboard').classList.toggle('hidden', tab !== 'leaderboard');
  
  document.getElementById('tab-devices').className = tab === 'devices'
    ? 'px-4 py-2 rounded-lg bg-sky-600 text-white font-medium'
    : 'px-4 py-2 rounded-lg bg-gray-800 text-gray-400 font-medium hover:bg-gray-700';
  
  document.getElementById('tab-leaderboard').className = tab === 'leaderboard'
    ? 'px-4 py-2 rounded-lg bg-sky-600 text-white font-medium'
    : 'px-4 py-2 rounded-lg bg-gray-800 text-gray-400 font-medium hover:bg-gray-700';
  
  if (tab === 'leaderboard') {
    refreshLeaderboard();
    if (!leaderboardInterval) {
      leaderboardInterval = setInterval(refreshLeaderboard, LEADERBOARD_REFRESH_INTERVAL);
    }
  } else {
    if (leaderboardInterval) {
      clearInterval(leaderboardInterval);
      leaderboardInterval = null;
    }
  }
}

async function togglePause(deviceId) {
  await fetch(`command/${encodeURIComponent(deviceId)}/pause`, {
    method: "POST",
  });
}

async function sendReset(deviceId) {
  await fetch(`command/${encodeURIComponent(deviceId)}/reset`, {
    method: "POST",
  });
}

async function sendStart(deviceId) {
  await fetch(`command/${encodeURIComponent(deviceId)}/start`, {
    method: "POST",
  });
}

async function sendLevel(deviceId, level) {
  await fetch(`command/${encodeURIComponent(deviceId)}/level/${level}`, {
    method: "POST",
  });
}

function handleLevelButtonClick(deviceId, level) {
  if (!Number.isInteger(level) || level < 1 || level > 8) return;
  sendLevel(deviceId, level);
}

function handleReset(deviceId) {
  sendReset(deviceId);
}

function handleStart(deviceId) {
  sendStart(deviceId);
}

function formatRelativeTime(ms) {
  if (!ms) return "";
  const diff = Date.now() - ms;
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

// ============ GAME ANALYSIS FUNCTIONS ============

function analyzeSession(session) {
  const popEvents = session.events.filter((e) => e.event_type === "pop_result");
  if (popEvents.length === 0) return null;

  const moleStats = Array(8)
    .fill(0)
    .map(() => ({ hits: 0, total: 0 }));
  let totalReaction = 0;
  let hitCount = 0;
  let bestReaction = Infinity;

  popEvents.forEach((e) => {
    const mole = e.mole_id;
    moleStats[mole].total++;
    if (e.outcome === "hit") {
      moleStats[mole].hits++;
      hitCount++;
      totalReaction += e.reaction_ms;
      bestReaction = Math.min(bestReaction, e.reaction_ms);
    }
  });

  const hitRate = ((hitCount / popEvents.length) * 100).toFixed(1);
  const avgReaction = hitCount > 0 ? Math.round(totalReaction / hitCount) : 0;

  return {
    moleStats,
    hitRate,
    avgReaction,
    bestReaction: bestReaction === Infinity ? 0 : bestReaction,
  };
}

function renderMoleHeatmap(moleStats) {
  return moleStats
    .map((stat, idx) => {
      const rate = stat.total > 0 ? (stat.hits / stat.total) * 100 : 0;
      const color =
        rate >= 70
          ? "bg-emerald-600"
          : rate >= 40
          ? "bg-amber-600"
          : "bg-rose-600";
      const opacity = stat.total === 0 ? "opacity-30" : "";
      return `
      <div class="flex flex-col items-center gap-1">
        <div class="${color} ${opacity} w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-lg">
          ${idx + 1}
        </div>
        <span class="text-xs text-gray-400">${rate.toFixed(0)}%</span>
        <span class="text-xs text-gray-600">${stat.hits}/${stat.total}</span>
      </div>
    `;
    })
    .join("");
}

function renderAnalysisModal(session, deviceId, sessionIndex) {
  const analysis = analyzeSession(session);
  if (!analysis) return "";

  const safeDeviceId = String(deviceId).replace(/[^a-zA-Z0-9]/g, "_");
  const modalId = `analysis-${safeDeviceId}-${sessionIndex}`;
  const chartId = `chart-${modalId}`;

  const weakMoles = analysis.moleStats
    .map((stat, idx) => ({
      mole: idx + 1,
      rate: stat.total > 0 ? (stat.hits / stat.total) * 100 : 100,
    }))
    .filter((m) => m.rate < 50 && m.rate < 100)
    .sort((a, b) => a.rate - b.rate)
    .slice(0, 3);

  // Serialize events for the chart (will be parsed when modal opens)
  const eventsJson = JSON.stringify(session.events).replace(/"/g, '&quot;');

  return `
    <div id="${modalId}" class="hidden fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
      <div class="bg-gray-850 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-700">
        <div class="sticky top-0 bg-gray-800 px-6 py-4 border-b border-gray-700 flex justify-between items-center">
          <h3 class="text-xl font-bold text-white">📊 Game Analysis</h3>
          <button onclick="closeAnalysis('${modalId}')" class="text-gray-400 hover:text-white text-2xl">&times;</button>
        </div>

        <div class="p-6 space-y-6">
          <!-- Score Progression Chart -->
          <div>
            <h4 class="text-sm font-semibold text-gray-400 mb-3">📈 Score Progression</h4>
            <div class="bg-gray-900/50 rounded-lg p-4" style="height: 200px;">
              <canvas id="${chartId}" data-events="${eventsJson}"></canvas>
            </div>
            <div class="flex items-center justify-center gap-4 mt-2 text-xs text-gray-500">
              <span><span class="inline-block w-3 h-3 bg-emerald-500 rounded-full"></span> Hit</span>
              <span><span class="inline-block w-3 h-3 bg-rose-500 rounded-full"></span> Miss</span>
              <span><span class="inline-block w-3 h-3 bg-amber-500 rounded-full"></span> Late</span>
            </div>
          </div>

          <!-- Overall Stats -->
          <div class="grid grid-cols-3 gap-4">
            <div class="bg-gray-800/50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-emerald-400">${
                analysis.hitRate
              }%</div>
              <div class="text-xs text-gray-500 mt-1">Hit Rate</div>
            </div>
            <div class="bg-gray-800/50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-sky-400">${
                analysis.avgReaction
              }ms</div>
              <div class="text-xs text-gray-500 mt-1">Avg Reaction</div>
            </div>
            <div class="bg-gray-800/50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-amber-400">${
                analysis.bestReaction
              }ms</div>
              <div class="text-xs text-gray-500 mt-1">Best Time</div>
            </div>
          </div>

          <!-- Mole Heatmap -->
          <div>
            <h4 class="text-sm font-semibold text-gray-400 mb-3">Performance by Button</h4>
            <div class="grid grid-cols-8 gap-2">
              ${renderMoleHeatmap(analysis.moleStats)}
            </div>
            <div class="flex items-center justify-center gap-4 mt-3 text-xs text-gray-500">
              <span><span class="inline-block w-3 h-3 bg-emerald-600 rounded"></span> ≥70%</span>
              <span><span class="inline-block w-3 h-3 bg-amber-600 rounded"></span> 40-69%</span>
              <span><span class="inline-block w-3 h-3 bg-rose-600 rounded"></span> <40%</span>
            </div>
          </div>

          <!-- Practice Recommendations -->
          ${
            weakMoles.length > 0
              ? `
            <div class="bg-amber-900/20 border border-amber-700/50 rounded-lg p-4">
              <h4 class="text-sm font-semibold text-amber-400 mb-2">Practice Recommendations</h4>
              <p class="text-sm text-gray-300 mb-3">Focus on these buttons:</p>
              <div class="flex gap-2">
                ${weakMoles
                  .map(
                    (m) => `
                  <div class="bg-gray-800 px-3 py-2 rounded text-center">
                    <div class="text-lg font-bold text-white">Button ${
                      m.mole
                    }</div>
                    <div class="text-xs text-rose-400">${m.rate.toFixed(
                      0
                    )}% hit rate</div>
                  </div>
                `
                  )
                  .join("")}
              </div>
            </div>
          `
              : `
            <div class="bg-emerald-900/20 border border-emerald-700/50 rounded-lg p-4 text-center">
              <div class="text-2xl mb-2">🎯</div>
              <p class="text-sm text-emerald-400 font-semibold">Excellent performance across all buttons!</p>
            </div>
          `
          }
        </div>
      </div>
    </div>
  `;
}

function showAnalysis(modalId) {
  document.getElementById(modalId).classList.remove("hidden");
  // Render chart after modal is visible
  setTimeout(() => {
    const canvas = document.getElementById(`chart-${modalId}`);
    if (canvas && canvas.dataset.events) {
      const events = JSON.parse(canvas.dataset.events);
      renderScoreChart(canvas, events);
    }
  }, 50);
}

function closeAnalysis(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

// ============ SCORE LINE GRAPH FUNCTIONS ============

// Store chart instances to update instead of recreating
const chartInstances = new Map();

// Store last session data per device to persist graph after game ends
const lastSessionData = new Map();

/**
 * Compute cumulative score timeline from session events
 * Returns array of {pop, score, level, outcome} for each pop_result event
 */
function computeScoreTimeline(events) {
  const popEvents = events.filter(e => e.event_type === "pop_result");
  const timeline = [];
  let cumulativeScore = 0;

  popEvents.forEach((e, idx) => {
    // Calculate score for this hit (simplified scoring formula)
    if (e.outcome === "hit") {
      const lvl = e.lvl || 1;
      const reactionMs = e.reaction_ms || 1000;
      const speedBonus = Math.max(0.5, 2 - reactionMs / 1000);
      cumulativeScore += Math.trunc(100 * lvl * speedBonus);
    }

    timeline.push({
      pop: idx + 1,
      score: cumulativeScore,
      level: e.lvl || 1,
      outcome: e.outcome,
      reactionMs: e.reaction_ms || 0,
    });
  });

  return timeline;
}

/**
 * Render a score line chart on the given canvas
 */
function renderScoreChart(canvas, events) {
  const ctx = canvas.getContext("2d");
  const timeline = computeScoreTimeline(events);

  if (timeline.length === 0) return;

  // Destroy existing chart if any
  if (chartInstances.has(canvas.id)) {
    chartInstances.get(canvas.id).destroy();
  }

  // Find level transition points
  const levelTransitions = [];
  let lastLevel = 0;
  timeline.forEach((point, idx) => {
    if (point.level !== lastLevel) {
      levelTransitions.push({ idx, level: point.level });
      lastLevel = point.level;
    }
  });

  // Create gradient fill
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "rgba(14, 165, 233, 0.3)");
  gradient.addColorStop(1, "rgba(14, 165, 233, 0.0)");

  // Point colors based on outcome
  const pointColors = timeline.map(p =>
    p.outcome === "hit" ? "#10b981" :
    p.outcome === "miss" ? "#f43f5e" : "#f59e0b"
  );

  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: timeline.map(p => p.pop),
      datasets: [{
        label: "Score",
        data: timeline.map(p => p.score),
        borderColor: "#0ea5e9",
        backgroundColor: gradient,
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: pointColors,
        pointBorderColor: pointColors,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: "index",
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: "#1f2937",
          titleColor: "#f3f4f6",
          bodyColor: "#d1d5db",
          borderColor: "#374151",
          borderWidth: 1,
          padding: 12,
          callbacks: {
            title: (items) => `Pop #${items[0].label}`,
            label: (item) => {
              const point = timeline[item.dataIndex];
              return [
                `Score: ${point.score.toLocaleString()}`,
                `Level: ${point.level}`,
                `Result: ${point.outcome.toUpperCase()}`,
                point.outcome === "hit" ? `Reaction: ${point.reactionMs}ms` : "",
              ].filter(Boolean);
            },
          },
        },
        // Custom plugin to draw level markers
        annotation: {
          annotations: levelTransitions.slice(1).reduce((acc, t, i) => {
            acc[`level${t.level}`] = {
              type: "line",
              xMin: t.idx,
              xMax: t.idx,
              borderColor: "#6b7280",
              borderWidth: 1,
              borderDash: [5, 5],
              label: {
                display: true,
                content: `L${t.level}`,
                position: "start",
              }
            };
            return acc;
          }, {}),
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: "Pop #",
            color: "#9ca3af",
          },
          grid: {
            color: "#374151",
          },
          ticks: {
            color: "#9ca3af",
          },
        },
        y: {
          title: {
            display: true,
            text: "Score",
            color: "#9ca3af",
          },
          grid: {
            color: "#374151",
          },
          ticks: {
            color: "#9ca3af",
            callback: (value) => value.toLocaleString(),
          },
          beginAtZero: true,
        },
      },
    },
  });

  chartInstances.set(canvas.id, chart);
  return chart;
}

/**
 * Render a mini live chart for current session in device card
 * Updates existing chart if present to avoid visual jitter
 */
function renderLiveChart(canvasId, events) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const timeline = computeScoreTimeline(events);

  if (timeline.length === 0) {
    return;
  }

  const pointColors = timeline.map(p =>
    p.outcome === "hit" ? "#10b981" :
    p.outcome === "miss" ? "#f43f5e" : "#f59e0b"
  );

  // If chart already exists, update data instead of recreating
  if (chartInstances.has(canvasId)) {
    const chart = chartInstances.get(canvasId);
    chart.data.labels = timeline.map(p => p.pop);
    chart.data.datasets[0].data = timeline.map(p => p.score);
    chart.data.datasets[0].pointBackgroundColor = pointColors;
    chart.data.datasets[0].pointBorderColor = pointColors;
    chart.update('none'); // 'none' mode skips animations for smooth updates
    return;
  }

  // Create new chart only if one doesn't exist
  const ctx = canvas.getContext("2d");

  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: timeline.map(p => p.pop),
      datasets: [{
        data: timeline.map(p => p.score),
        borderColor: "#0ea5e9",
        backgroundColor: "rgba(14, 165, 233, 0.1)",
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointBackgroundColor: pointColors,
        pointBorderColor: pointColors,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false, // Disable initial animation for smoother live updates
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          backgroundColor: "#1f2937",
          titleColor: "#f3f4f6",
          bodyColor: "#d1d5db",
          callbacks: {
            title: (items) => `Pop #${items[0].label}`,
            label: (item) => {
              const point = timeline[item.dataIndex];
              return `${point.score.toLocaleString()} pts`;
            },
          },
        },
      },
      scales: {
        x: {
          display: false,
        },
        y: {
          display: false,
          beginAtZero: true,
        },
      },
    },
  });

  chartInstances.set(canvasId, chart);
}

function getStatusConfig(status) {
  switch (status) {
    case "online":
      return {
        dot: "bg-emerald-500",
        text: "Online",
        textClass: "text-emerald-400",
      };
    case "serial_error":
      return {
        dot: "bg-orange-500",
        text: "Serial Error",
        textClass: "text-orange-400",
      };
    default:
      return {
        dot: "bg-gray-500",
        text: "Offline",
        textClass: "text-gray-500",
      };
  }
}

function getGameStateBadge(device) {
  const text = device.game_state === "playing" ? "Playing" : "Idle";
  const bgClass =
    device.game_state === "playing" ? "bg-emerald-600" : "bg-gray-600";
  return `<span class="px-2 py-0.5 rounded text-xs font-medium ${bgClass}">${text}</span>`;
}

function renderLives(lives) {
  return (
    '<span class="text-rose-400">' +
    "♥".repeat(lives) +
    "</span>" +
    '<span class="text-gray-600">' +
    "♥".repeat(5 - lives) +
    "</span>"
  );
}

function renderEvent(event) {
  const type = event.event_type;

  if (type === "pop_result") {
    const outcomeClass =
      event.outcome === "hit"
        ? "text-emerald-400"
        : event.outcome === "miss"
        ? "text-rose-400"
        : "text-amber-400";
    const outcomeText = event.outcome.toUpperCase();
    return `
      <div class="flex items-center gap-3 py-1.5 px-3 text-sm font-mono border-b border-gray-800/50 last:border-0">
        <span class="${outcomeClass} font-semibold w-12">${outcomeText}</span>
        <span class="text-gray-500">Mole #${event.mole_id}</span>
        <span class="text-gray-400">${event.reaction_ms}ms</span>
        <span class="text-gray-500">L${event.lvl} ${event.pop}/${
      event.pops_total
    }</span>
        <span class="ml-auto">${renderLives(event.lives)}</span>
      </div>
    `;
  }

  if (type === "lvl_complete") {
    return `
      <div class="flex items-center gap-2 py-2 px-3 text-sm font-mono bg-emerald-900/30 border-b border-gray-800/50">
        <span class="text-emerald-400 font-semibold">Level ${event.lvl} Complete!</span>
      </div>
    `;
  }

  if (type === "session_end") {
    const won = event.win === "true";
    const text = won ? "Victory!" : "Game Over";
    const cls = won
      ? "text-emerald-400 bg-emerald-900/30"
      : "text-rose-400 bg-rose-900/30";
    return `
      <div class="flex items-center justify-center py-3 px-3 text-sm font-semibold ${cls}">
        ${text}
      </div>
    `;
  }

  return "";
}

function renderEventLog(events) {
  if (!events || events.length === 0) return "";
  return events.map(renderEvent).join("");
}

function renderPastSession(session, index, deviceId) {
  const date = new Date(session.started_at);
  const timeStr = date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const result = session.won
    ? '<span class="text-emerald-400">Won</span>'
    : '<span class="text-rose-400">Lost</span>';
  const eventCount = session.events.length;

  const hasPopEvents = session.events.some(
    (e) => e.event_type === "pop_result"
  );

  const modalId = `analysis-${deviceId}-${index}`;

  return `
    <details class="group">
      <summary class="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-800/50 text-sm">
        <span class="text-gray-400">${timeStr}</span>
        <span>${result}</span>
        <span class="text-gray-500">${eventCount} events</span>
        <span class="text-gray-600 group-open:rotate-180 transition-transform">▼</span>
      </summary>
      <div class="bg-gray-900/50">
        <div class="max-h-48 overflow-y-auto">
          ${renderEventLog(session.events)}
        </div>
        ${
          hasPopEvents
            ? `
          <div class="px-3 py-2 border-t border-gray-800">
            <button 
              onclick="showAnalysis('${modalId}')" 
              class="w-full bg-sky-600 hover:bg-sky-500 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
            >
              View Game Analysis
            </button>
          </div>
        `
            : ""
        }
      </div>
    </details>
    ${hasPopEvents ? renderAnalysisModal(session, deviceId, index) : ""}
  `;
}

function renderPastSessions(sessions, deviceId) {
  if (!sessions || sessions.length === 0) return "";
  return `
    <div class="border-t border-gray-800">
      <div class="px-3 py-2 text-xs text-gray-500 uppercase tracking-wide">Past Sessions</div>
      ${sessions.map((s, i) => renderPastSession(s, i, deviceId)).join("")}
    </div>
  `;
}

function createDeviceCard(device) {
  const statusConfig = getStatusConfig(device.status);
  const isOffline = device.status === "offline";
  const cardClass = isOffline ? "card-offline" : "";
  const pauseDisabled = isOffline
    ? "disabled opacity-50 cursor-not-allowed"
    : "";
  const startDisabled = pauseDisabled;
  const resetDisabled = pauseDisabled;

  const hasCurrentSession =
    device.current_session && device.current_session.events.length > 0;
  const hasPopEvents = hasCurrentSession &&
    device.current_session.events.some(e => e.event_type === "pop_result");
  const liveChartId = `live-chart-${device.device_id.replace(/[^a-zA-Z0-9]/g, '_')}`;

  const currentSessionHtml = hasCurrentSession
    ? `
      ${hasPopEvents ? `
        <div class="px-4 py-3 border-b border-gray-800 live-chart-section">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-500 uppercase tracking-wide live-label">Live Score</span>
            <span class="text-sm font-bold text-sky-400 live-score">${device.current_session.score.toLocaleString()} pts</span>
          </div>
          <div style="height: 80px;">
            <canvas id="${liveChartId}" class="live-chart"></canvas>
          </div>
        </div>
      ` : ''}
      <div class="event-log max-h-48 overflow-y-auto">${renderEventLog(
        device.current_session.events
      )}</div>`
    : "";

  return `
    <div class="bg-gray-850 rounded-xl shadow-xl overflow-hidden border border-gray-800 ${cardClass}" data-device="${
    device.device_id
  }">
      <div class="px-5 py-4 bg-gray-800/50">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div class="min-w-[200px]">
            <div class="flex items-center gap-2 mb-1">
              <span class="status-dot w-2 h-2 rounded-full ${
                statusConfig.dot
              }"></span>
              <h2 class="font-semibold text-lg text-white">${
                device.device_id
              }</h2>
            </div>
            <div class="flex items-center gap-2">
              <span class="status-text ${statusConfig.textClass} text-xs">${
    statusConfig.text
  }</span>
              ${
                device.status !== "online" && device.last_seen
                  ? `<span class="text-gray-600 text-xs">${formatRelativeTime(
                      device.last_seen
                    )}</span>`
                  : ""
              }
            </div>
          </div>
          <div class="flex flex-col gap-2 w-full lg:w-auto">
            <span class="game-badge">${getGameStateBadge(device)}</span>
            <div class="flex flex-wrap items-center gap-2 level-control">
              <span class="text-xs text-gray-500">Level</span>
              <div class="flex flex-wrap gap-1 level-buttons">
                ${LEVELS.map(
                  (lvl) => `
                    <button
                      onclick="handleLevelButtonClick('${
                        device.device_id
                      }', ${lvl})"
                      class="${
                        isOffline ? LEVEL_BTN_DISABLED : LEVEL_BTN_ENABLED
                      }"
                      ${isOffline ? "disabled" : ""}
                    >
                      ${lvl}
                    </button>
                  `
                ).join("")}
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                onclick="handleStart('${device.device_id}')"
                class="start-btn bg-emerald-500 hover:bg-emerald-400 text-gray-900 ${startDisabled} font-medium py-1.5 px-3 rounded-lg text-sm transition-colors"
                ${isOffline ? "disabled" : ""}
              >
                Start
              </button>
              <button
                onclick="togglePause('${device.device_id}')"
                class="pause-btn bg-amber-500 hover:bg-amber-400 text-gray-900 ${pauseDisabled} font-medium py-1.5 px-4 rounded-lg text-sm transition-colors"
                ${isOffline ? "disabled" : ""}
              >
                Pause
              </button>
              <button
                onclick="handleReset('${device.device_id}')"
                class="reset-btn bg-rose-600 hover:bg-rose-500 text-gray-50 ${resetDisabled} font-medium py-1.5 px-3 rounded-lg text-sm transition-colors"
                ${isOffline ? "disabled" : ""}
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      </div>
      ${currentSessionHtml}
      <div class="past-sessions">${renderPastSessions(
        device.past_sessions,
        device.device_id
      )}</div>
    </div>
  `;
}

function updateDeviceCard(card, device) {
  const statusConfig = getStatusConfig(device.status);
  const isOffline = device.status === "offline";

  const dot = card.querySelector(".status-dot");
  dot.className = `status-dot w-2 h-2 rounded-full ${statusConfig.dot}`;

  const statusText = card.querySelector(".status-text");
  statusText.className = `status-text ${statusConfig.textClass} text-xs`;
  statusText.textContent = statusConfig.text;

  const gameBadge = card.querySelector(".game-badge");
  gameBadge.innerHTML = getGameStateBadge(device);

  const pauseBtn = card.querySelector(".pause-btn");
  pauseBtn.disabled = isOffline;
  if (isOffline) {
    pauseBtn.className =
      "pause-btn bg-gray-600 opacity-50 cursor-not-allowed font-medium py-1.5 px-4 rounded-lg text-sm transition-colors";
  } else {
    pauseBtn.className =
      "pause-btn bg-amber-500 hover:bg-amber-400 text-gray-900 font-medium py-1.5 px-4 rounded-lg text-sm transition-colors";
  }

  const startBtn = card.querySelector(".start-btn");
  if (startBtn) {
    startBtn.disabled = isOffline;
    startBtn.className = isOffline
      ? "start-btn bg-gray-600 opacity-50 cursor-not-allowed font-medium py-1.5 px-3 rounded-lg text-sm transition-colors"
      : "start-btn bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-medium py-1.5 px-3 rounded-lg text-sm transition-colors";
  }

  const resetBtn = card.querySelector(".reset-btn");
  if (resetBtn) {
    resetBtn.disabled = isOffline;
    resetBtn.className = isOffline
      ? "reset-btn bg-gray-700 opacity-60 cursor-not-allowed text-gray-300 font-medium py-1.5 px-3 rounded-lg text-sm transition-colors"
      : "reset-btn bg-rose-600 hover:bg-rose-500 text-gray-50 font-medium py-1.5 px-3 rounded-lg text-sm transition-colors";
  }

  const levelBtns = card.querySelectorAll(".level-btn");
  levelBtns.forEach((btn) => {
    btn.disabled = isOffline;
    btn.className = isOffline ? LEVEL_BTN_DISABLED : LEVEL_BTN_ENABLED;
  });

  if (isOffline) {
    card.classList.add("card-offline");
  } else {
    card.classList.remove("card-offline");
  }

  // Update current session event log and live chart
  let eventLog = card.querySelector(".event-log");
  let liveChartContainer = card.querySelector(".live-chart-section");
  const hasCurrentSession =
    device.current_session && device.current_session.events.length > 0;
  const hasPopEvents = hasCurrentSession &&
    device.current_session.events.some(e => e.event_type === "pop_result");
  const safeDeviceId = device.device_id.replace(/[^a-zA-Z0-9]/g, '_');
  const liveChartId = `live-chart-${safeDeviceId}`;

  // Check if a NEW game session has started (to clear old persisted data)
  // Compare started_at timestamp - each session has a unique start time
  const storedData = lastSessionData.get(device.device_id);
  const currentStartedAt = device.current_session?.started_at || 0;
  const storedStartedAt = storedData?.startedAt || 0;
  const isNewSession = hasCurrentSession &&
    storedData &&
    currentStartedAt > 0 &&
    currentStartedAt !== storedStartedAt;

  // Clear persisted Final Score chart if new session starts
  // Only clear if stored data exists AND it's marked as not live (game ended)
  if (isNewSession && storedData && !storedData.isLive) {
    lastSessionData.delete(device.device_id);
    if (chartInstances.has(liveChartId)) {
      chartInstances.get(liveChartId).destroy();
      chartInstances.delete(liveChartId);
    }
    if (liveChartContainer) {
      liveChartContainer.remove();
      liveChartContainer = null;
    }
  }

  const header = card.querySelector(".bg-gray-800\\/50");

  if (hasCurrentSession && hasPopEvents) {
    // Active game with pop events - store data for persistence
    lastSessionData.set(device.device_id, {
      events: device.current_session.events,
      score: device.current_session.score,
      startedAt: device.current_session.started_at,
      isLive: true
    });

    if (!liveChartContainer) {
      header.insertAdjacentHTML(
        "afterend",
        `<div class="px-4 py-3 border-b border-gray-800 live-chart-section">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-500 uppercase tracking-wide live-label">Live Score</span>
            <span class="text-sm font-bold text-sky-400 live-score">0 pts</span>
          </div>
          <div style="height: 80px;">
            <canvas id="${liveChartId}" class="live-chart"></canvas>
          </div>
        </div>`
      );
      liveChartContainer = card.querySelector(".live-chart-section");
    }

    // Update live score display
    const liveScoreEl = card.querySelector(".live-score");
    if (liveScoreEl) {
      liveScoreEl.textContent = `${device.current_session.score.toLocaleString()} pts`;
    }
    const liveLabel = card.querySelector(".live-label");
    if (liveLabel) {
      liveLabel.textContent = "Live Score";
    }

    // Render/update the live chart
    renderLiveChart(liveChartId, device.current_session.events);

    // Add/update event log (only if event count changed to reduce flicker)
    if (!eventLog) {
      const insertAfter = liveChartContainer || header;
      insertAfter.insertAdjacentHTML(
        "afterend",
        `<div class="event-log max-h-48 overflow-y-auto"></div>`
      );
      eventLog = card.querySelector(".event-log");
    }
    const prevEventCount = eventLog.dataset.eventCount || 0;
    const newEventCount = device.current_session.events.length;
    if (newEventCount !== parseInt(prevEventCount)) {
      eventLog.innerHTML = renderEventLog(device.current_session.events);
      eventLog.dataset.eventCount = newEventCount;
      eventLog.scrollTop = eventLog.scrollHeight;
    }

  } else if (!hasCurrentSession && storedData) {
    // Game ended - persist the final chart
    storedData.isLive = false;

    if (!liveChartContainer) {
      header.insertAdjacentHTML(
        "afterend",
        `<div class="px-4 py-3 border-b border-gray-800 live-chart-section">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-500 uppercase tracking-wide live-label">Final Score</span>
            <span class="text-sm font-bold text-sky-400 live-score">0 pts</span>
          </div>
          <div style="height: 80px;">
            <canvas id="${liveChartId}" class="live-chart"></canvas>
          </div>
        </div>`
      );
      liveChartContainer = card.querySelector(".live-chart-section");
    }

    // Update to show "Final Score" instead of "Live Score"
    const liveLabel = card.querySelector(".live-label");
    if (liveLabel) {
      liveLabel.textContent = "Final Score";
    }
    const liveScoreEl = card.querySelector(".live-score");
    if (liveScoreEl) {
      liveScoreEl.textContent = `${storedData.score.toLocaleString()} pts`;
    }

    // Keep the chart showing with stored data
    renderLiveChart(liveChartId, storedData.events);

    // Remove event log when game ends (it moves to past sessions)
    if (eventLog) {
      eventLog.remove();
    }

  } else if (hasCurrentSession && !hasPopEvents) {
    // Game started but no pop events yet - show event log only
    if (!eventLog) {
      header.insertAdjacentHTML(
        "afterend",
        `<div class="event-log max-h-48 overflow-y-auto"></div>`
      );
      eventLog = card.querySelector(".event-log");
    }
    const prevEventCount = eventLog.dataset.eventCount || 0;
    const newEventCount = device.current_session.events.length;
    if (newEventCount !== parseInt(prevEventCount)) {
      eventLog.innerHTML = renderEventLog(device.current_session.events);
      eventLog.dataset.eventCount = newEventCount;
      eventLog.scrollTop = eventLog.scrollHeight;
    }

  } else {
    // No session and no stored data - clean up everything
    if (liveChartContainer) {
      if (chartInstances.has(liveChartId)) {
        chartInstances.get(liveChartId).destroy();
        chartInstances.delete(liveChartId);
      }
      liveChartContainer.remove();
    }
    if (eventLog) {
      eventLog.remove();
    }
  }

  // Update past sessions only if count changed
  const pastSessionsEl = card.querySelector(".past-sessions");
  const prevDevice = knownDevices.get(device.device_id);
  const prevCount = prevDevice?.past_sessions?.length ?? 0;
  const newCount = device.past_sessions?.length ?? 0;

  if (pastSessionsEl && newCount !== prevCount) {
    pastSessionsEl.innerHTML = renderPastSessions(
      device.past_sessions,
      device.device_id
    );
  }
}

async function refresh() {
  const container = document.getElementById("devices");
  const devices = await fetchDevices();

  if (devices.length === 0) {
    container.innerHTML = `
      <div class="col-span-full flex items-center justify-center py-16 text-gray-500">
        <div class="text-center">
          <div class="text-5xl mb-4 opacity-50">&#128225;</div>
          <div class="text-lg">No devices connected</div>
        </div>
      </div>
    `;
    knownDevices.clear();
    return;
  }

  const currentDeviceIds = new Set(devices.map((d) => d.device_id));

  for (const deviceId of knownDevices.keys()) {
    if (!currentDeviceIds.has(deviceId)) {
      const card = document.querySelector(`[data-device="${deviceId}"]`);
      if (card) card.remove();
      knownDevices.delete(deviceId);
    }
  }

  for (const device of devices) {
    let card = document.querySelector(`[data-device="${device.device_id}"]`);

    if (!card) {
      const placeholder = container.querySelector(".col-span-full");
      if (placeholder) placeholder.remove();

      container.insertAdjacentHTML("beforeend", createDeviceCard(device));
      card = document.querySelector(`[data-device="${device.device_id}"]`);
      knownDevices.set(device.device_id, device);
    }

    updateDeviceCard(card, device);
    knownDevices.set(device.device_id, device);
  }
}

async function refreshLeaderboard() {
  const list = document.getElementById('leaderboard-list');
  const entries = await fetchLeaderboard();

  if (entries.length === 0) {
    list.innerHTML = `
      <div class="flex items-center justify-center py-16 text-gray-500">
        <div class="text-center">
          <div class="text-5xl mb-4 opacity-50">🏆</div>
          <div class="text-lg">No scores yet</div>
        </div>
      </div>
    `;
    return;
  }

  list.innerHTML = entries.map((entry, idx) => {
    const date = new Date(entry.timestamp);
    const timeStr = date.toLocaleString();
    const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `${idx + 1}.`;
    
    return `
      <div class="flex items-center justify-between px-5 py-4 hover:bg-gray-800/30">
        <div class="flex items-center gap-4">
          <span class="text-2xl w-8">${medal}</span>
          <div>
            <div class="font-semibold text-white">${entry.device_id}</div>
            <div class="text-xs text-gray-500">${timeStr}</div>
          </div>
        </div>
        <div class="text-right">
          <div class="text-2xl font-bold text-sky-400">${entry.score.toLocaleString()}</div>
          <div class="text-xs text-gray-500">points</div>
        </div>
      </div>
    `;
  }).join('');
}

refresh();
setInterval(refresh, REFRESH_INTERVAL);