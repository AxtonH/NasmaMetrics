/**
 * Dashboard JavaScript Module
 * Handles all chart rendering and data interactions
 */

// Chart instances
let activeUsersChart = null;
let requestsChart = null;
let easeComparisonChart = null;
let planningCoverageChart = null;

const NASMA_COLORS = {
    purpleSolid: "rgba(124, 58, 237, 1)",
    purpleSoft: "rgba(124, 58, 237, 0.85)",
    purpleBorder: "rgba(92, 29, 187, 1)",
    orangeSolid: "rgba(215, 106, 3, 1)",
    orangeSoft: "rgba(215, 106, 3, 0.2)",
};

const isAdminView =
    new URLSearchParams(window.location.search).get("admin") === "true";

// Ease comparison data
let easeData = { odoo: [], nasma: [] };

const CARD_LAYOUT_STORAGE_KEY = "nasma-dashboard-card-layout";
const THEME_STORAGE_KEY = "nasma-theme";
const dashboardFilters = {
    start: null,
    end: null,
};

let planningCoverageData = { monthly: [], weekly: [] };

/**
 * Initialize dashboard on page load
 */
document.addEventListener("DOMContentLoaded", function () {
    initCardInteractions();
    initFilterControls();
    updateFilterLabel();
    initThemeToggle();
    initPlanningCoverageControls();
    loadDashboardData();
    loadPlanningCoverage();
});

function initFilterControls() {
    const startInput = document.getElementById("filterStartDate");
    const endInput = document.getElementById("filterEndDate");
    const applyBtn = document.getElementById("applyFiltersBtn");
    const clearBtn = document.getElementById("clearFiltersBtn");

    if (!startInput || !endInput || !applyBtn || !clearBtn) {
        return;
    }

    applyBtn.addEventListener("click", () => {
        const startValue = startInput.value || null;
        const endValue = endInput.value || null;

        if (startValue && endValue && startValue > endValue) {
            alert("Start date must be before end date.");
            return;
        }

        dashboardFilters.start = startValue;
        dashboardFilters.end = endValue;
        updateFilterLabel();
        loadDashboardData();
    });

    clearBtn.addEventListener("click", () => {
        startInput.value = "";
        endInput.value = "";
        dashboardFilters.start = null;
        dashboardFilters.end = null;
        updateFilterLabel();
        loadDashboardData();
    });
}

function buildFilterQuery() {
    const params = new URLSearchParams();
    if (dashboardFilters.start) {
        params.append("start_date", formatDateForQuery(dashboardFilters.start));
    }
    if (dashboardFilters.end) {
        params.append("end_date", formatDateForQuery(dashboardFilters.end, true));
    }
    const query = params.toString();
    return query ? `?${query}` : "";
}

function formatDateForQuery(value, endOfDay = false) {
    if (!value) {
        return value;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    if (endOfDay) {
        date.setHours(23, 59, 59, 999);
    } else {
        date.setHours(0, 0, 0, 0);
    }
    return date.toISOString();
}

function formatDateLabel(value) {
    if (!value) {
        return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleDateString();
}

function formatMonthShort(value) {
    if (!value) {
        return "";
    }
    const date = new Date(`${ value }-01T00:00:00`);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleDateString(undefined, {
        month: "short",
        year: "2-digit",
    });
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
    if (!Number.isFinite(year) || !Number.isFinite(week)) {
        return period;
    }
    const startDate = new Date(Date.UTC(year, 0, 4));
    const dayOfWeek = startDate.getUTCDay() || 7;
    startDate.setUTCDate(startDate.getUTCDate() - dayOfWeek + 1 + (week - 1) * 7);
    return startDate.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
    });
}

function getFilterDescriptions() {
    if (!dashboardFilters.start && !dashboardFilters.end) {
        return {
            summaryText: "Showing all available data",
            rangeText: "today",
        };
    }

    const startText = dashboardFilters.start
        ? formatDateLabel(dashboardFilters.start)
        : "Beginning";
    const endText = dashboardFilters.end
        ? formatDateLabel(dashboardFilters.end)
        : "Present";

    const rangeText =
        dashboardFilters.start && dashboardFilters.end
            ? `${startText} - ${endText}`
            : dashboardFilters.start
            ? `since ${startText}`
            : `until ${endText}`;

    return {
        summaryText: `Showing data from ${startText} to ${endText}`,
        rangeText,
    };
}

function updateFilterLabel() {
    const descriptions = getFilterDescriptions();
    const filterLabel = document.getElementById("activeFilterLabel");
    if (filterLabel) {
        filterLabel.textContent = descriptions.summaryText;
    }
    const activitiesLabel = document.getElementById("activitiesRangeLabel");
    if (activitiesLabel) {
        activitiesLabel.textContent = descriptions.rangeText;
    }
}

function initThemeToggle() {
    const toggleBtn = document.getElementById("themeToggle");
    if (!toggleBtn) {
        return;
    }

    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) || "light";
    applyTheme(savedTheme);

    toggleBtn.addEventListener("click", () => {
        const newTheme = document.body.classList.contains("dark-mode") ? "light" : "dark";
        applyTheme(newTheme);
        localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    });
}

function applyTheme(theme) {
    const body = document.body;
    if (theme === "dark") {
        body.classList.add("dark-mode");
    } else {
        body.classList.remove("dark-mode");
    }

    const toggleBtn = document.getElementById("themeToggle");
    if (toggleBtn) {
        const iconEl = document.getElementById("themeIcon");
        if (iconEl) {
            iconEl.textContent = theme === "dark" ? "☀️" : "🌙";
        }
    }
}

/**
 * Load all dashboard data from API
 */
async function loadDashboardData() {
    try {
        const query = buildFilterQuery();

        // Load active users
        const activeUsersResponse = await fetch(`/api/active-users${query}`);
        const activeUsersData = await activeUsersResponse.json();
        if (activeUsersData.success) {
            renderActiveUsersChart(activeUsersData.data);
        }

        // Load requests
        const requestsResponse = await fetch(`/api/requests${query}`);
        const requestsData = await requestsResponse.json();
        if (requestsData.success) {
            renderRequestsChart(requestsData.data);
        }

        // Load adoption
        const adoptionResponse = await fetch(`/api/adoption${query}`);
        const adoptionData = await adoptionResponse.json();
        if (adoptionData.success) {
            document.getElementById("adoptionCount").textContent =
                adoptionData.data.count;
        }

        // Load messages
        const messagesResponse = await fetch(`/api/messages${query}`);
        const messagesData = await messagesResponse.json();
        if (messagesData.success) {
            const total = messagesData.data.total_messages ?? "-";
            const messagesEl = document.getElementById("messagesCount");
            if (messagesEl) {
                messagesEl.textContent = total;
            }
        }

        // Load log hours users
        const logHoursResponse = await fetch(`/api/log-hours${query}`);
        const logHoursData = await logHoursResponse.json();
        if (logHoursData.success) {
            renderLogHoursTable(logHoursData.data);
        } else {
            renderLogHoursTable([]);
        }

        const activitiesResponse = await fetch(`/api/activities-today${query}`);
        const activitiesData = await activitiesResponse.json();
        if (activitiesData.success) {
            renderActivitiesTable(activitiesData.data);
        } else {
            renderActivitiesTable([]);
        }

        // Load satisfaction
        const satisfactionResponse = await fetch("/api/satisfaction");
        const satisfactionData = await satisfactionResponse.json();
        if (satisfactionData.success) {
            const value =
                satisfactionData.data.overall_satisfaction || "";
            const valueDisplay = document.getElementById("satisfactionValue");
            if (valueDisplay) {
                valueDisplay.textContent = value || "-";
            }

            const input = document.getElementById("satisfactionInput");
            if (input) {
                input.value = value || "";
            }
        }

        // Load ease comparison
        const easeResponse = await fetch("/api/ease-comparison");
        const easeDataResponse = await easeResponse.json();
        if (easeDataResponse.success) {
            easeData = easeDataResponse.data;
            renderEaseComparisonChart(easeData);
        }

    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

function renderActiveUsersChart(data) {
    const ctx = document.getElementById("activeUsersChart").getContext("2d");

    // Destroy existing chart if it exists
    if (activeUsersChart) {
        activeUsersChart.destroy();
    }

    const subtitleEl = document.getElementById("activeUsersSubtitle");
    if (subtitleEl) {
        subtitleEl.textContent = "Active users by month (chat activity)";
    }

    const labels = data.map((item) => item.month);
    const values = data.map((item) => item.active_users);

    activeUsersChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Active Users",
                    data: values,
                    backgroundColor: NASMA_COLORS.purpleSoft,
                    borderColor: NASMA_COLORS.purpleBorder,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: "Active users",
                    },
                },
                x: {
                    title: {
                        display: true,
                        text: "Month",
                    },
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
            },
        },
    });
}

/**
 * Render Requests Made Bar Chart
 */
function renderRequestsChart(data) {
    const ctx = document.getElementById("requestsChart").getContext("2d");

    // Destroy existing chart if it exists
    if (requestsChart) {
        requestsChart.destroy();
    }

    const labels = data.map((item) => item.attribute);
    const values = data.map((item) => item.value);

    requestsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Sum of Value",
                    data: values,
                    backgroundColor: NASMA_COLORS.purpleSoft,
                    borderColor: NASMA_COLORS.purpleBorder,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: "Sum of Value",
                    },
                },
                x: {
                    title: {
                        display: true,
                        text: "Attribute",
                    },
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
            },
        },
    });
}

/**
 * Render Ease Comparison Line Chart
 */
function renderEaseComparisonChart(data) {
    const ctx = document.getElementById("easeComparisonChart").getContext("2d");

    // Destroy existing chart if it exists
    if (easeComparisonChart) {
        easeComparisonChart.destroy();
    }

    const calcAverage = (items = []) => {
        if (!items.length) return 0;
        const sum = items.reduce((total, entry) => total + (entry.value || 0), 0);
        return parseFloat((sum / items.length).toFixed(2));
    };

    const odooAverage = calcAverage(data.odoo);
    const nasmaAverage = calcAverage(data.nasma);

    const valueLabelPlugin = {
        id: "valueLabelPlugin",
        afterDatasetsDraw(chart) {
            const { ctx } = chart;
            ctx.save();
            ctx.font = "bold 14px 'Inter', sans-serif";
            ctx.fillStyle = "#5c1dbb";
            ctx.textAlign = "left";
            chart.data.datasets.forEach((dataset, dataIndex) => {
                const meta = chart.getDatasetMeta(dataIndex);
                meta.data.forEach((element) => {
                    const { x, y } = element.tooltipPosition();
                    ctx.fillText(`${dataset.data[0]} `, x + 8, y + 5);
                });
            });
            ctx.restore();
        },
    };

    easeComparisonChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Tool"],
            datasets: [
                {
                    label: "Average of Odoo Ease",
                    data: [odooAverage],
                    backgroundColor: NASMA_COLORS.orangeSoft,
                    borderColor: NASMA_COLORS.orangeSolid,
                    borderWidth: 2,
                },
                {
                    label: "Average of Nasma Ease",
                    data: [nasmaAverage],
                    backgroundColor: NASMA_COLORS.purpleSoft,
                    borderColor: NASMA_COLORS.purpleBorder,
                    borderWidth: 2,
                },
            ],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    stacked: false,
                    title: {
                        display: true,
                        text: "Tool",
                    },
                },
                x: {
                    beginAtZero: true,
                    max: 10,
                    title: {
                        display: true,
                        text: "Ease + speed of Tool Scale (1-10)",
                    },
                    grid: {
                        drawBorder: false,
                    },
                },
            },
            plugins: {
                legend: {
                    position: "top",
                },
            },
        },
        plugins: [valueLabelPlugin],
    });
}

/**
 * Render log hours user table
 */
function renderLogHoursTable(data) {
    const tableBody = document.getElementById("logHoursTableBody");
    if (!tableBody) {
        return;
    }

    if (!data || data.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="px-4 py-3 text-center text-gray-500">
                    No log hours activity found
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = data
        .map(
            (item, index) => `
                <tr class="border-t border-gray-100">
                    <td class="px-4 py-2 text-gray-500">${index + 1}</td>
                    <td class="px-4 py-2">${item.user_name}</td>
                </tr>
            `
        )
        .join("");
}

function renderActivitiesTable(data) {
    const tableBody = document.getElementById("activitiesTableBody");
    if (!tableBody) {
        return;
    }

    const { rangeText } = getFilterDescriptions();
    const readableRange =
        rangeText === "today"
            ? "today"
            : rangeText.includes("–")
            ? `between ${rangeText}`
            : rangeText;

    if (!data || data.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="px-4 py-3 text-center text-gray-500">
                    No activities recorded ${readableRange}
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = data
        .map(
            (item) => `
                <tr class="border-t border-gray-100">
                    <td class="px-4 py-3 font-medium text-gray-800">${item.user_name}</td>
                    <td class="px-4 py-3">${item.metric_type}</td>
                    <td class="px-4 py-3 text-right font-bold text-purple-600">${item.actions_today}</td>
                </tr>
            `
        )
        .join("");
}

function initCardInteractions() {
    if (typeof interact === "undefined") {
        console.warn("Interact.js not loaded; card editing disabled.");
        return;
    }

    const container = document.getElementById("dashboardLayout");
    const cards = document.querySelectorAll(".dashboard-card");
    const savedLayout = getSavedCardLayout();

    cards.forEach((card) => {
        card.style.position = "relative";
        card.style.touchAction = "none";
        card.dataset.x = card.dataset.x || 0;
        card.dataset.y = card.dataset.y || 0;
        const saved = savedLayout[card.id];
        if (saved) {
            applyCardState(card, saved);
        }
    });

    if (isAdminView) {
        document.querySelectorAll(".card-drag-handle").forEach((handle) => {
            handle.style.display = "inline";
        });

        interact(".dashboard-card")
            .draggable({
                allowFrom: ".card-drag-handle",
                listeners: {
                    move(event) {
                        dragMoveListener(event);
                    },
                    end(event) {
                        persistCardState(event.target);
                    },
                },
                modifiers: [
                    container
                        ? interact.modifiers.restrictRect({
                              restriction: container,
                              endOnly: true,
                          })
                        : null,
                ].filter(Boolean),
                inertia: true,
            })
            .resizable({
                edges: { left: true, right: true, bottom: true, top: true },
                listeners: {
                    move(event) {
                        const target = event.target;
                        let x = parseFloat(target.getAttribute("data-x")) || 0;
                        let y = parseFloat(target.getAttribute("data-y")) || 0;

                        target.style.width = `${ event.rect.width }px`;
                        target.style.height = `${ event.rect.height }px`;

                        x += event.deltaRect.left;
                        y += event.deltaRect.top;

                        target.style.transform = `translate(${ x }px, ${ y }px)`;
                        target.setAttribute("data-x", x);
                        target.setAttribute("data-y", y);
                    },
                    end(event) {
                        persistCardState(event.target);
                    },
                },
                modifiers: [
                    container
                        ? interact.modifiers.restrictEdges({
                              outer: container,
                          })
                        : null,
                    interact.modifiers.restrictSize({
                        min: { width: 220, height: 160 },
                    }),
                ].filter(Boolean),
            });
    } else {
        document.querySelectorAll(".card-drag-handle").forEach((handle) => {
            handle.style.display = "none";
        });
    }
}

function dragMoveListener(event) {
    const target = event.target;
    let x = (parseFloat(target.getAttribute("data-x")) || 0) + event.dx;
    let y = (parseFloat(target.getAttribute("data-y")) || 0) + event.dy;

    target.style.transform = `translate(${ x }px, ${ y }px)`;
    target.setAttribute("data-x", x);
    target.setAttribute("data-y", y);
}

function getSavedCardLayout() {
    try {
        const stored = localStorage.getItem(CARD_LAYOUT_STORAGE_KEY);
        return stored ? JSON.parse(stored) : {};
    } catch (error) {
        console.warn("Unable to read stored layout", error);
        return {};
    }
}

function applyCardState(card, state) {
    const x = state.x || 0;
    const y = state.y || 0;

    if (state.width) {
        card.style.width = state.width;
    }
    if (state.height) {
        card.style.height = state.height;
    }

    card.style.transform = `translate(${ x }px, ${ y }px)`;
    card.setAttribute("data-x", x);
    card.setAttribute("data-y", y);
}

function persistCardState(card) {
    if (!card || !card.id) {
        return;
    }

    const layout = getSavedCardLayout();
    layout[card.id] = {
        x: parseFloat(card.getAttribute("data-x")) || 0,
        y: parseFloat(card.getAttribute("data-y")) || 0,
        width: card.style.width || `${ card.offsetWidth }px`,
        height: card.style.height || `${ card.offsetHeight }px`,
    };

    try {
        localStorage.setItem(CARD_LAYOUT_STORAGE_KEY, JSON.stringify(layout));
    } catch (error) {
        console.warn("Unable to persist layout", error);
    }
}

function resetCardLayout() {
    try {
        localStorage.removeItem(CARD_LAYOUT_STORAGE_KEY);
    } catch (error) {
        console.warn("Unable to reset layout storage", error);
    }

    document.querySelectorAll(".dashboard-card").forEach((card) => {
        card.style.transform = "";
        card.style.width = "";
        card.style.height = "";
        card.removeAttribute("data-x");
        card.removeAttribute("data-y");
    });
}

window.resetCardLayout = resetCardLayout;

/**
 * Show ease editor modal
 */
function showEaseEditor() {
    const modal = document.getElementById("easeEditorModal");
    modal.classList.remove("hidden");

    // Populate editors
    populateEaseEditor("odoo", easeData.odoo || []);
    populateEaseEditor("nasma", easeData.nasma || []);
}

/**
 * Populate ease editor with data
 */
function populateEaseEditor(type, data) {
    const container = document.getElementById(`${ type }DataContainer`);
    container.innerHTML = "";

    if (data.length === 0) {
        addEaseDataPoint(type);
    } else {
        data.forEach((item, index) => {
            addEaseDataPoint(type, item.period, item.value, index);
        });
    }
}

/**
 * Add a data point to ease editor
 */
function addEaseDataPoint(type, period = "", value = "", index = null) {
    const container = document.getElementById(`${ type }DataContainer`);
    const div = document.createElement("div");
    div.className = "flex gap-2 mb-2";
    div.innerHTML = `
        < input 
            type = "text" 
            placeholder = "Period (e.g., Week 1)" 
            value = "${period}"
            class= "flex-1 px-3 py-2 border rounded"
            data - period
            />
        <input 
            type="number" 
            step="0.01"
            placeholder="Value (1-10)" 
            value="${value}"
            class="w-24 px-3 py-2 border rounded"
            data-value
            min="0"
            max="10"
        />
        <button 
            onclick="removeEaseDataPoint(this)" 
            class="bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600"
        >
            Remove
        </button>
    `;
    container.appendChild(div);
}

/**
 * Remove a data point from ease editor
 */
function removeEaseDataPoint(button) {
    button.parentElement.remove();
}

/**
 * Hide ease editor modal
 */
function hideEaseEditor() {
    document.getElementById("easeEditorModal").classList.add("hidden");
}

/**
 * Save ease comparison data
 */
async function saveEaseData() {
    // Collect Odoo data
    const odooContainer = document.getElementById("odooDataContainer");
    const odooInputs = odooContainer.querySelectorAll("div");
    const odooData = [];
    odooInputs.forEach((div) => {
        const period = div.querySelector('[data-period]').value;
        const value = parseFloat(div.querySelector('[data-value]').value);
        if (period && !isNaN(value)) {
            odooData.push({ period: period, value: value });
        }
    });

    // Collect Nasma data
    const nasmaContainer = document.getElementById("nasmaDataContainer");
    const nasmaInputs = nasmaContainer.querySelectorAll("div");
    const nasmaData = [];
    nasmaInputs.forEach((div) => {
        const period = div.querySelector('[data-period]').value;
        const value = parseFloat(div.querySelector('[data-value]').value);
        if (period && !isNaN(value)) {
            nasmaData.push({ period: period, value: value });
        }
    });

    try {
        const response = await fetch("/api/ease-comparison", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ odoo: odooData, nasma: nasmaData }),
        });

        const data = await response.json();
        if (data.success) {
            easeData = { odoo: odooData, nasma: nasmaData };
            renderEaseComparisonChart(easeData);
            hideEaseEditor();
            alert("Ease comparison data saved successfully!");
        } else {
            alert("Failed to save ease comparison data: " + data.error);
        }
    } catch (error) {
        console.error("Error saving ease comparison data:", error);
        alert("Error saving ease comparison data");
    }
}


function initPlanningCoverageControls() {
    const select = document.getElementById("planningCoverageView");
    if (!select) {
        return;
    }
    select.addEventListener("change", () => {
        renderPlanningCoverageChart(select.value);
    });
}

/**
 * Load planning coverage data
 */
async function loadPlanningCoverage() {
    const canvas = document.getElementById("planningCoverageChart");
    if (!canvas) {
        return;
    }

    try {
        const response = await fetch("/api/odoo/planning-coverage");
        const payload = await response.json();
        if (payload && payload.ok) {
            const data = payload.data || {};
            planningCoverageData = {
                monthly: Array.isArray(data.monthly) ? data.monthly : [],
                weekly: Array.isArray(data.weekly) ? data.weekly : [],
            };
            const viewSelect = document.getElementById("planningCoverageView");
            const selectedView = viewSelect ? viewSelect.value : "monthly";
            renderPlanningCoverageChart(selectedView);
        } else {
            planningCoverageData = { monthly: [], weekly: [] };
            renderPlanningCoverageChart("monthly");
        }
    } catch (error) {
        console.error("Error loading planning coverage:", error);
        planningCoverageData = { monthly: [], weekly: [] };
        renderPlanningCoverageChart("monthly");
    }
}

/**
 * Render planning coverage chart for selected view
 */
function renderPlanningCoverageChart(view = "monthly") {
    const canvas = document.getElementById("planningCoverageChart");
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext("2d");
    const dataset = planningCoverageData[view] || [];
    const limit = view === "monthly" ? 12 : 20;
    const trimmed = dataset.slice(-limit);

    if (planningCoverageChart) {
        planningCoverageChart.destroy();
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

    planningCoverageChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Planned vs Logged %",
                    data: values,
                    backgroundColor: NASMA_COLORS.orangeSoft,
                    borderColor: NASMA_COLORS.orangeSolid,
                    borderWidth: 1,
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
                        text: "Planned vs Logged %",
                    },
                },
                x: {
                    title: {
                        display: true,
                        text: view === "monthly" ? "Month" : "Week",
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
                                `Planned: ${ entry.planned_days } | Logged: ${ entry.logged_days }`,
                                `Planned slots: ${ plannedSlots } | Logged slots: ${ loggedSlots }`,
                            ];
                        },
                    },
                },
            },
        },
    });
}
