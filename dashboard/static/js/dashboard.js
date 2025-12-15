const REFRESH_INTERVAL = 500;
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
  const res = await fetch("/jj/devices");
  return res.json();
}

async function fetchLeaderboard() {
  const res = await fetch("/jj/leaderboard");
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
  await fetch(`/jj/command/${encodeURIComponent(deviceId)}/pause`, {
    method: "POST",
  });
}

async function sendReset(deviceId) {
  await fetch(`/jj/command/${encodeURIComponent(deviceId)}/reset`, {
    method: "POST",
  });
}

async function sendStart(deviceId) {
  await fetch(`/jj/command/${encodeURIComponent(deviceId)}/start`, {
    method: "POST",
  });
}

async function sendLevel(deviceId, level) {
  await fetch(`/jj/command/${encodeURIComponent(deviceId)}/level/${level}`, {
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

  const modalId = `analysis-${deviceId}-${sessionIndex}`;

  const weakMoles = analysis.moleStats
    .map((stat, idx) => ({
      mole: idx + 1,
      rate: stat.total > 0 ? (stat.hits / stat.total) * 100 : 100,
    }))
    .filter((m) => m.rate < 50 && m.rate < 100)
    .sort((a, b) => a.rate - b.rate)
    .slice(0, 3);

  return `
    <div id="${modalId}" class="hidden fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
      <div class="bg-gray-850 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-700">
        <div class="sticky top-0 bg-gray-800 px-6 py-4 border-b border-gray-700 flex justify-between items-center">
          <h3 class="text-xl font-bold text-white">📊 Game Analysis</h3>
          <button onclick="closeAnalysis('${modalId}')" class="text-gray-400 hover:text-white text-2xl">&times;</button>
        </div>
        
        <div class="p-6 space-y-6">
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
}

function closeAnalysis(modalId) {
  document.getElementById(modalId).classList.add("hidden");
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
  const currentSessionHtml = hasCurrentSession
    ? `<div class="event-log max-h-64 overflow-y-auto">${renderEventLog(
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

  // Update current session event log
  let eventLog = card.querySelector(".event-log");
  const hasCurrentSession =
    device.current_session && device.current_session.events.length > 0;

  if (hasCurrentSession) {
    if (!eventLog) {
      const header = card.querySelector(".bg-gray-800\\/50");
      header.insertAdjacentHTML(
        "afterend",
        `<div class="event-log max-h-64 overflow-y-auto"></div>`
      );
      eventLog = card.querySelector(".event-log");
    }
    eventLog.innerHTML = renderEventLog(device.current_session.events);
    eventLog.scrollTop = eventLog.scrollHeight;
  } else if (eventLog) {
    eventLog.remove();
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