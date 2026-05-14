/* Apple Health Clinical Dashboard — Chart.js frontend logic */
/* DATA is injected by the Jinja2 template as window.HEALTH_DATA */

(function () {
  "use strict";

  /* ── Palette ─────────────────────────────────────────────────────────────── */
  const C = {
    accent:  "#6c8ff8",
    accent2: "#a78bfa",
    green:   "#34d399",
    yellow:  "#fbbf24",
    red:     "#f87171",
    orange:  "#fb923c",
    muted:   "#8b92b8",
    grid:    "rgba(45,49,72,.6)",
    bg:      "#1a1d27",
  };

  /* ── Chart.js global defaults ────────────────────────────────────────────── */
  Chart.defaults.color = C.muted;
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.plugins.legend.display = false;
  Chart.defaults.plugins.tooltip.backgroundColor = "#22263a";
  Chart.defaults.plugins.tooltip.borderColor = "#2d3148";
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.titleColor = "#e8eaf6";
  Chart.defaults.plugins.tooltip.bodyColor = "#8b92b8";

  const GRID_OPTS = {
    color: C.grid,
    drawBorder: false,
  };

  function scaleDefaults(title) {
    return {
      grid: GRID_OPTS,
      ticks: { maxTicksLimit: 6 },
      title: title ? { display: true, text: title, color: C.muted, font: { size: 10 } } : undefined,
    };
  }

  /* ── Helpers ─────────────────────────────────────────────────────────────── */
  function fmt(val, decimals = 1) {
    if (val === null || val === undefined || isNaN(val)) return "—";
    return Number(val).toFixed(decimals);
  }

  function badgeClass(classification) {
    return "kpi-badge badge-" + (classification || "").toLowerCase().replace(/\s+/g, "_");
  }

  /* ── Tabs ────────────────────────────────────────────────────────────────── */
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });

  /* ── Line chart helper ───────────────────────────────────────────────────── */
  function lineChart(canvasId, labels, datasets, yTitle) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            ...scaleDefaults(null),
            ticks: {
              maxTicksLimit: 8,
              maxRotation: 0,
              callback: function(val, idx) {
                const label = this.getLabelForValue(val);
                return label ? label.slice(5) : ""; // show MM-DD
              },
            },
          },
          y: scaleDefaults(yTitle),
        },
        plugins: {
          legend: { display: datasets.length > 1 },
          tooltip: {
            callbacks: {
              title: items => items[0].label,
            },
          },
        },
      },
    });
  }

  function sparkLine(canvasId, values, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !values || values.length === 0) return;
    const ctx = canvas.getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: values.map((_, i) => i),
        datasets: [{ data: values, borderColor: color, borderWidth: 2, pointRadius: 0, tension: 0.4, fill: false }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { display: false }, y: { display: false } },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        animation: false,
      },
    });
  }

  /* ── Main render ─────────────────────────────────────────────────────────── */
  const D = window.HEALTH_DATA;
  if (!D) { console.error("HEALTH_DATA not found"); return; }

  renderCardio(D.cardio);
  renderSleep(D.sleep);
  renderActivity(D.activity);
  renderRunning(D.running);
  renderAudio(D.audio);
  renderGait(D.gait);

  /* ── Cardio ──────────────────────────────────────────────────────────────── */
  function renderCardio(c) {
    if (!c) return;
    setText("kpi-rhr", fmt(c.rhr_mean, 0) + " bpm");
    setBadge("badge-rhr", c.rhr_classification);
    setText("kpi-hrv", fmt(c.hrv_mean, 0) + " ms");
    setBadge("badge-hrv", c.hrv_classification);
    setText("kpi-vo2", c.vo2max_latest ? fmt(c.vo2max_latest, 1) + " mL/kg/min" : "—");
    if (c.vo2max_classification) setBadge("badge-vo2", c.vo2max_classification);
    setText("kpi-hrmax", fmt(c.hr_max_tanaka, 0) + " bpm");

    // Render trend arrows
    if (c.rhr_trend) renderTrend("trend-rhr", c.rhr_trend.slope_per_day, false);
    if (c.hrv_trend) renderTrend("trend-hrv", c.hrv_trend.slope_per_day, true);
  }

  /* ── Sleep ───────────────────────────────────────────────────────────────── */
  function renderSleep(s) {
    if (!s) return;
    setText("kpi-sleep-dur", fmt(s.mean_duration_h, 1) + "h");
    setBadge("badge-sleep-dur", s.duration_classification);
    setText("kpi-sleep-eff", fmt(s.mean_efficiency_pct, 0) + "%");
    setBadge("badge-sleep-eff", s.efficiency_classification);
    setText("kpi-deep", fmt(s.mean_deep_pct, 0) + "%");
    setText("kpi-rem", fmt(s.mean_rem_pct, 0) + "%");
    setText("kpi-nights", s.n_nights);

    // Donut chart for sleep stages
    const stageCanvas = document.getElementById("chart-sleep-stages");
    if (stageCanvas) {
      const awake = s.mean_awake_pct || 0;
      const deep   = s.mean_deep_pct || 0;
      const rem    = s.mean_rem_pct || 0;
      const core   = Math.max(0, 100 - awake - deep - rem);
      new Chart(stageCanvas.getContext("2d"), {
        type: "doughnut",
        data: {
          labels: ["Core", "Deep", "REM", "Awake"],
          datasets: [{
            data: [core, deep, rem, awake],
            backgroundColor: [C.accent, C.accent2, C.green, C.muted],
            borderWidth: 0,
            hoverOffset: 6,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: "68%",
          plugins: {
            legend: { display: true, position: "right", labels: { boxWidth: 10, padding: 12 } },
          },
        },
      });
    }
  }

  /* ── Activity ────────────────────────────────────────────────────────────── */
  function renderActivity(a) {
    if (!a) return;
    setText("kpi-steps", Math.round(a.mean_daily_steps).toLocaleString());
    setText("kpi-steps-pct", fmt(a.steps_goal_pct, 0) + "% of goal");
    setText("kpi-energy", fmt(a.mean_active_energy_kcal, 0) + " kcal");
    setText("kpi-exercise", fmt(a.mean_exercise_min, 0) + " min/day");
    setText("kpi-distance", fmt(a.total_distance_km, 0) + " km total");
    if (a.steps_trend) renderTrend("trend-steps", a.steps_trend.slope_per_day, true);
  }

  /* ── Running ─────────────────────────────────────────────────────────────── */
  function renderRunning(r) {
    if (!r) return;
    setText("kpi-runs", r.n_runs);
    setText("kpi-run-dist", fmt(r.total_distance_km, 0) + " km");
    if (r.mean_pace_min_per_km) {
      const min = Math.floor(r.mean_pace_min_per_km);
      const sec = Math.round((r.mean_pace_min_per_km - min) * 60);
      setText("kpi-pace", min + ":" + String(sec).padStart(2, "0") + " /km");
    }
    if (r.longest_run_km) setText("kpi-longest", fmt(r.longest_run_km, 1) + " km");
  }

  /* ── Audio ───────────────────────────────────────────────────────────────── */
  function renderAudio(a) {
    if (!a) return;
    setText("kpi-audio-env", fmt(a.mean_env_db, 1) + " dB");
    setBadge("badge-audio-env", a.env_classification);
    if (a.mean_headphone_db) {
      setText("kpi-audio-hp", fmt(a.mean_headphone_db, 1) + " dB");
      if (a.headphone_classification) setBadge("badge-audio-hp", a.headphone_classification);
    }
    setText("kpi-audio-pct", fmt(a.pct_time_above_safe, 0) + "% above 70 dB");
  }

  /* ── Gait ────────────────────────────────────────────────────────────────── */
  function renderGait(g) {
    if (!g) return;
    setText("kpi-gait-speed", fmt(g.mean_walking_speed_ms, 2) + " m/s");
    setBadge("badge-gait-speed", g.speed_classification);
    if (g.mean_double_support_pct != null) setText("kpi-double-support", fmt(g.mean_double_support_pct, 1) + "%");
    if (g.mean_asymmetry_pct != null)      setText("kpi-asymmetry", fmt(g.mean_asymmetry_pct, 2) + "%");
    if (g.mean_step_length_m != null)      setText("kpi-step-length", fmt(g.mean_step_length_m, 2) + " m");
  }

  /* ── Utilities ───────────────────────────────────────────────────────────── */
  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? "—";
  }

  function setBadge(id, classification) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = (classification || "").replace(/_/g, " ");
    el.className = badgeClass(classification);
  }

  function renderTrend(id, slopePerDay, positiveIsGood) {
    const el = document.getElementById(id);
    if (!el) return;
    const abs = Math.abs(slopePerDay);
    if (abs < 0.01) {
      el.innerHTML = '<span class="trend trend-flat">→ stable</span>';
      return;
    }
    const up = slopePerDay > 0;
    const good = positiveIsGood ? up : !up;
    const cls = good ? "trend-up" : "trend-down";
    const arrow = up ? "↑" : "↓";
    el.innerHTML = `<span class="trend ${cls}">${arrow} ${fmt(abs * 30, 1)}/mo</span>`;
  }

})();
