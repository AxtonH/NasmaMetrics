/**
 * Dashboard JavaScript Module
 * Handles all chart rendering and data interactions
 */

// Chart instances
let activeUsersChart = null;
let requestsChart = null;
let easeComparisonChart = null;

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

/**
 * Initialize dashboard on page load
 */
document.addEventListener("DOMContentLoaded", function () {
    initCardInteractions();
    loadDashboardData();
});

/**
 * Load all dashboard data from API
 */
async function loadDashboardData() {
    try {
        // Load active users
        const activeUsersResponse = await fetch("/api/active-users");
        const activeUsersData = await activeUsersResponse.json();
        if (activeUsersData.success) {
            renderActiveUsersChart(activeUsersData.data);
        }

        // Load requests
        const requestsResponse = await fetch("/api/requests");
        const requestsData = await requestsResponse.json();
        if (requestsData.success) {
            renderRequestsChart(requestsData.data);
        }

        // Load adoption
        const adoptionResponse = await fetch("/api/adoption");
        const adoptionData = await adoptionResponse.json();
        if (adoptionData.success) {
            document.getElementById("adoptionCount").textContent =
                adoptionData.data.count;
        }

        // Load messages
        const messagesResponse = await fetch("/api/messages");
        const messagesData = await messagesResponse.json();
        if (messagesData.success) {
            const total = messagesData.data.total_messages ?? "-";
            const messagesEl = document.getElementById("messagesCount");
            if (messagesEl) {
                messagesEl.textContent = total;
            }
        }

        // Load log hours users
        const logHoursResponse = await fetch("/api/log-hours");
        const logHoursData = await logHoursResponse.json();
        if (logHoursData.success) {
            renderLogHoursTable(logHoursData.data);
        } else {
            renderLogHoursTable([]);
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

        // Load activities today
        const activitiesResponse = await fetch("/api/activities-today");
        const activitiesData = await activitiesResponse.json();
        if (activitiesData.success) {
            renderActivitiesTable(activitiesData.data);
        } else {
            renderActivitiesTable([]);
        }
    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

/**
 * Render Active Users Bar Chart
 */
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
                <td colspan="2" class="px-4 py-3 text-center text-gray-500">
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

