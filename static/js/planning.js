const NASMA_COLORS = {
    purpleSolid: "rgba(124, 58, 237, 1)",
    purpleSoft: "rgba(124, 58, 237, 0.85)",
    purpleBorder: "rgba(92, 29, 187, 1)",
    orangeSolid: "rgba(215, 106, 3, 1)",
    orangeSoft: "rgba(215, 106, 3, 0.2)",
};

let planningCoverageLargeChart = null;
let planningCoverageData = { monthly: [], weekly: [] };

document.addEventListener("DOMContentLoaded", () => {
    const selector = document.getElementById("planningLargeView");
    if (selector) {
        selector.addEventListener("change", () => renderPlanningChart(selector.value));
    }
    loadPlanningCoverageData().then(() => {
        const initialView = selector ? selector.value : "monthly";
        renderPlanningChart(initialView);
    });
});

async function loadPlanningCoverageData() {
    try {
        const response = await fetch("/api/odoo/planning-coverage");
        const payload = await response.json();
        if (payload && payload.ok && payload.data) {
            planningCoverageData = {
                monthly: Array.isArray(payload.data.monthly) ? payload.data.monthly : [],
                weekly: Array.isArray(payload.data.weekly) ? payload.data.weekly : [],
            };
        } else {
            planningCoverageData = { monthly: [], weekly: [] };
        }
    } catch (error) {
        console.error("Failed to load planning coverage data:", error);
        planningCoverageData = { monthly: [], weekly: [] };
    }
}

function renderPlanningChart(view = "monthly") {
    const canvas = document.getElementById("planningCoverageLargeChart");
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext("2d");
    const dataset = planningCoverageData[view] || [];
    const limit = view === "monthly" ? 12 : 20;
    const trimmed = dataset.slice(-limit);

    if (planningCoverageLargeChart) {
        planningCoverageLargeChart.destroy();
    }

    if (!trimmed.length) {
        return;
    }

    const labels = trimmed.map((entry) =>
        view === "monthly" ? formatMonthShort(entry.period) : formatWeekLabel(entry.period),
    );
    const values = trimmed.map((entry) =>
        typeof entry.coverage_pct === "number" ? Number(entry.coverage_pct.toFixed(2)) : 0,
    );

    planningCoverageLargeChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Planned vs Logged %",
                    data: values,
                    backgroundColor: NASMA_COLORS.orangeSoft,
                    borderColor: NASMA_COLORS.orangeSolid,
                    borderWidth: 2,
                    borderRadius: 12,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: 100,
                    title: {
                        display: true,
                        text: "Coverage %",
                    },
                    grid: {
                        color: "rgba(124, 58, 237, 0.08)",
                    },
                },
                x: {
                    title: {
                        display: true,
                        text: view === "monthly" ? "Month" : "Week",
                    },
                    grid: {
                        display: false,
                    },
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        afterBody(context) {
                            const index = context[0].dataIndex;
                            const entry = trimmed[index];
                            if (!entry) {
                                return "";
                            }
                            const plannedSlots = entry.planned_slots ?? 0;
                            const loggedSlots = entry.logged_slots ?? 0;
                            return [
                                `Planned days: ${ entry.planned_days }`,
                                `Logged days: ${ entry.logged_days }`,
                                `Planned slots: ${ plannedSlots }`,
                                `Logged slots: ${ loggedSlots }`,
                            ];
                        },
                    },
                },
            },
        },
    });
}

function formatMonthShort(value) {
    if (!value) {
        return "";
    }
    const date = new Date(`${ value }-01T00:00:00`);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function formatWeekLabel(period) {
    if (!period || typeof period !== "string") {
        return "";
    }
    const match = period.match(/^(\d{4})-W(\d{2})$/);
    if (!match) {
        return period;
    }
    const year = Number(match[1]);
    const week = Number(match[2]);
    const startDate = getIsoWeekStartDate(year, week);
    if (!startDate) {
        return period;
    }
    const formatted = startDate.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
    });
    return `Week of ${ formatted }`;
}

function getIsoWeekStartDate(year, week) {
    if (!Number.isFinite(year) || !Number.isFinite(week)) {
        return null;
    }
    const simple = new Date(Date.UTC(year, 0, 4));
    const dayOfWeek = simple.getUTCDay() || 7;
    simple.setUTCDate(simple.getUTCDate() - dayOfWeek + 1);
    simple.setUTCDate(simple.getUTCDate() + (week - 1) * 7);
    return simple;
}
