/**
 * Shared front-end helpers for the IPRN SMS panel.
 */

/* Chart helpers (Chart.js must be loaded from CDN before this script) */

function initLineChart(canvasId, labels, data, label, color) {
    var el = document.getElementById(canvasId);
    if (!el || typeof Chart === "undefined") return null;

    var ctx = el.getContext("2d");
    var gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, color || "rgba(56, 189, 248, 0.7)");
    gradient.addColorStop(1, "rgba(15, 23, 42, 0.05)");

    return new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: label || "",
                    data: data,
                    borderColor: color || "#38bdf8",
                    backgroundColor: gradient,
                    tension: 0.35,
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHitRadius: 10,
                },
            ],
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(15, 23, 42, 0.98)",
                    borderColor: "rgba(148, 163, 184, 0.7)",
                    borderWidth: 1,
                    padding: 10,
                    titleColor: "#e5e7eb",
                    bodyColor: "#e5e7eb",
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: "#9ca3af",
                        font: { size: 11 },
                    },
                    grid: { display: false },
                },
                y: {
                    ticks: {
                        color: "#9ca3af",
                        font: { size: 11 },
                        precision: 0,
                    },
                    grid: {
                        color: "rgba(31, 41, 55, 0.7)",
                        drawBorder: false,
                    },
                },
            },
        },
    });
}

/**
 * Simple helper to auto-refresh a container with HTML from a URL.
 */
function setupAutoRefresh(url, containerId, intervalMs) {
    var container = document.getElementById(containerId);
    if (!container) return;

    function refresh() {
        fetch(url, { credentials: "same-origin" })
            .then(function (res) {
                return res.text();
            })
            .then(function (html) {
                container.innerHTML = html;
            })
            .catch(function () {
                // ignore errors in UI
            });
    }

    refresh();
    setInterval(refresh, intervalMs || 5000);
}

/**
 * Wire the "Test API" button in the Admin API Sources page.
 * Expects:
 *   - a button with id="btn-test-api"
 *   - an input with id="api-url"
 *   - a container with id="test-api-result"
 */
function wireTestApi() {
    var btn = document.getElementById("btn-test-api");
    var input = document.getElementById("api-url");
    var result = document.getElementById("test-api-result");
    if (!btn || !input || !result) return;

    btn.addEventListener("click", function () {
        var url = input.value.trim();
        if (!url) {
            result.innerHTML =
                '<div class="alert alert-danger">Please enter an API URL.</div>';
            return;
        }

        result.innerHTML =
            '<div class="alert alert-info">Testing API, please wait...</div>';

        fetch("/admin/test_api.php", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: "url=" + encodeURIComponent(url),
            credentials: "same-origin",
        })
            .then(function (res) {
                return res.json();
            })
            .then(function (data) {
                if (data.success) {
                    var html =
                        '<div class="alert alert-success">' +
                        data.message +
                        "</div>";
                    if (data.sample) {
                        html +=
                            '<pre style="max-height:220px;overflow:auto;font-size:11px;background:rgba(15,23,42,0.9);padding:8px;border-radius:8px;border:1px solid rgba(148,163,184,0.4);">' +
                            JSON.stringify(data.sample, null, 2) +
                            "</pre>";
                    }
                    result.innerHTML = html;
                } else {
                    result.innerHTML =
                        '<div class="alert alert-danger">' +
                        (data.message || "API test failed") +
                        "</div>";
                }
            })
            .catch(function () {
                result.innerHTML =
                    '<div class="alert alert-danger">Error while testing API.</div>';
            });
    });
}

document.addEventListener("DOMContentLoaded", function () {
    // Auto-wire components when present
    wireTestApi();
});