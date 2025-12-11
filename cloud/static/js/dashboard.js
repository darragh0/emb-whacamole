const REFRESH_INTERVAL = 500;

const knownDevices = new Map();
const LEVELS = Array.from({ length: 8 }, (_, idx) => idx + 1);
const LEVEL_BTN_ENABLED =
  "level-btn bg-sky-600 hover:bg-sky-500 text-gray-50 font-medium px-2.5 py-1 rounded-md text-sm transition-colors";
const LEVEL_BTN_DISABLED =
  "level-btn bg-gray-700 opacity-60 cursor-not-allowed text-gray-300 font-medium px-2.5 py-1 rounded-md text-sm";

async function fetchDevices() {
  const res = await fetch("/devices");
  return res.json();
}

async function togglePause(deviceId) {
  await fetch(`/command/${encodeURIComponent(deviceId)}`, { method: "POST" });
}

async function sendReset(deviceId) {
  await fetch(`/command/${encodeURIComponent(deviceId)}/reset`, {
    method: "POST",
  });
}

async function sendStart(deviceId) {
  await fetch(`/command/${encodeURIComponent(deviceId)}/start`, {
    method: "POST",
  });
}

async function sendLevel(deviceId, level) {
  await fetch(`/command/${encodeURIComponent(deviceId)}/level/${level}`, {
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
        <span class="text-gray-500">L${event.lvl} ${event.pop}/${event.pops_total}</span>
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

function renderPastSession(session, index) {
  const date = new Date(session.started_at);
  const timeStr = date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const result = session.won
    ? '<span class="text-emerald-400">Won</span>'
    : '<span class="text-rose-400">Lost</span>';
  const eventCount = session.events.length;

  return `
    <details class="group">
      <summary class="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-800/50 text-sm">
        <span class="text-gray-400">${timeStr}</span>
        <span>${result}</span>
        <span class="text-gray-500">${eventCount} events</span>
        <span class="text-gray-600 group-open:rotate-180 transition-transform">▼</span>
      </summary>
      <div class="max-h-48 overflow-y-auto bg-gray-900/50">
        ${renderEventLog(session.events)}
      </div>
    </details>
  `;
}

function renderPastSessions(sessions) {
  if (!sessions || sessions.length === 0) return "";
  return `
    <div class="border-t border-gray-800">
      <div class="px-3 py-2 text-xs text-gray-500 uppercase tracking-wide">Past Sessions</div>
      ${sessions.map((s, i) => renderPastSession(s, i)).join("")}
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
    ? `<div class="event-log max-h-64 overflow-y-auto">${renderEventLog(device.current_session.events)}</div>`
    : "";

  return `
    <div class="bg-gray-850 rounded-xl shadow-xl overflow-hidden border border-gray-800 ${cardClass}" data-device="${device.device_id}">
      <div class="px-5 py-4 bg-gray-800/50">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div class="min-w-[200px]">
            <div class="flex items-center gap-2 mb-1">
              <span class="status-dot w-2 h-2 rounded-full ${statusConfig.dot}"></span>
              <h2 class="font-semibold text-lg text-white">${device.device_id}</h2>
            </div>
            <div class="flex items-center gap-2">
              <span class="status-text ${statusConfig.textClass} text-xs">${statusConfig.text}</span>
              ${device.status !== "online" && device.last_seen ? `<span class="text-gray-600 text-xs">${formatRelativeTime(device.last_seen)}</span>` : ""}
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
                      onclick="handleLevelButtonClick('${device.device_id}', ${lvl})"
                      class="${isOffline ? LEVEL_BTN_DISABLED : LEVEL_BTN_ENABLED}"
                      ${isOffline ? "disabled" : ""}
                    >
                      ${lvl}
                    </button>
                  `,
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
      <div class="past-sessions">${renderPastSessions(device.past_sessions)}</div>
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
        `<div class="event-log max-h-64 overflow-y-auto"></div>`,
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
    pastSessionsEl.innerHTML = renderPastSessions(device.past_sessions);
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

refresh();
setInterval(refresh, REFRESH_INTERVAL);
