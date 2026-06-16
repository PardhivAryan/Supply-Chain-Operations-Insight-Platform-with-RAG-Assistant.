const chartColors = {
    blue: "#2563eb",
    teal: "#0f766e",
    amber: "#b7791f",
    rose: "#be123c",
    green: "#15803d",
    purple: "#7c3aed",
    grid: "rgba(104, 113, 125, 0.18)",
};

async function fetchChartData(url) {
    const response = await fetch(url, { headers: { "Accept": "application/json" } });
    if (!response.ok) {
        return [];
    }
    const payload = await response.json();
    return payload.data || [];
}

function money(value) {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
    }).format(value || 0);
}

function baseOptions(extra = {}) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { boxWidth: 12, color: "#3d4754" } },
            tooltip: { mode: "index", intersect: false },
        },
        scales: {
            x: { grid: { display: false }, ticks: { color: "#68717d" } },
            y: { grid: { color: chartColors.grid }, ticks: { color: "#68717d" } },
        },
        ...extra,
    };
}

function renderEmpty(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const wrapper = canvas.parentElement;
    canvas.remove();
    const empty = document.createElement("div");
    empty.className = "text-muted py-5 text-center";
    empty.textContent = "No chart data available.";
    wrapper.appendChild(empty);
}

async function renderMonthlyRevenue() {
    const data = await fetchChartData("/api/charts/monthly-revenue/");
    if (!data.length) return renderEmpty("monthlyRevenueChart");
    new Chart(document.getElementById("monthlyRevenueChart"), {
        type: "line",
        data: {
            labels: data.map((item) => item.label),
            datasets: [
                {
                    label: "Revenue",
                    data: data.map((item) => item.revenue),
                    borderColor: chartColors.blue,
                    backgroundColor: "rgba(37, 99, 235, 0.12)",
                    fill: true,
                    tension: 0.25,
                    pointRadius: 2,
                },
                {
                    label: "Order Volume",
                    data: data.map((item) => item.order_volume),
                    borderColor: chartColors.teal,
                    yAxisID: "orders",
                    tension: 0.25,
                    pointRadius: 2,
                },
            ],
        },
        options: baseOptions({
            scales: {
                x: { grid: { display: false }, ticks: { color: "#68717d", maxTicksLimit: 14 } },
                y: {
                    grid: { color: chartColors.grid },
                    ticks: { color: "#68717d", callback: (value) => money(value) },
                },
                orders: {
                    position: "right",
                    grid: { drawOnChartArea: false },
                    ticks: { color: "#68717d" },
                },
            },
        }),
    });
}

async function renderCategoryRevenue() {
    const data = await fetchChartData("/api/charts/category-revenue/");
    if (!data.length) return renderEmpty("categoryRevenueChart");
    new Chart(document.getElementById("categoryRevenueChart"), {
        type: "bar",
        data: {
            labels: data.map((item) => item.label),
            datasets: [
                {
                    label: "Revenue",
                    data: data.map((item) => item.revenue),
                    backgroundColor: chartColors.blue,
                    borderRadius: 4,
                },
                {
                    label: "Profit",
                    data: data.map((item) => item.profit),
                    backgroundColor: chartColors.green,
                    borderRadius: 4,
                },
            ],
        },
        options: baseOptions({
            scales: {
                x: { grid: { display: false }, ticks: { color: "#68717d", maxRotation: 50, minRotation: 0 } },
                y: { grid: { color: chartColors.grid }, ticks: { color: "#68717d", callback: (value) => money(value) } },
            },
        }),
    });
}

async function renderRegionLateDelivery() {
    const data = await fetchChartData("/api/charts/region-late-delivery/");
    if (!data.length) return renderEmpty("regionLateChart");
    new Chart(document.getElementById("regionLateChart"), {
        type: "bar",
        data: {
            labels: data.map((item) => item.label),
            datasets: [
                {
                    label: "Late Delivery Rate",
                    data: data.map((item) => item.late_delivery_rate),
                    backgroundColor: chartColors.rose,
                    borderRadius: 4,
                },
            ],
        },
        options: baseOptions({
            scales: {
                x: { grid: { display: false }, ticks: { color: "#68717d", maxRotation: 50, minRotation: 0 } },
                y: {
                    grid: { color: chartColors.grid },
                    ticks: { color: "#68717d", callback: (value) => `${value}%` },
                },
            },
        }),
    });
}

async function renderShippingMode() {
    const data = await fetchChartData("/api/charts/shipping-mode/");
    if (!data.length) return renderEmpty("shippingModeChart");
    new Chart(document.getElementById("shippingModeChart"), {
        type: "doughnut",
        data: {
            labels: data.map((item) => item.label),
            datasets: [
                {
                    label: "Orders",
                    data: data.map((item) => item.order_volume),
                    backgroundColor: [chartColors.blue, chartColors.teal, chartColors.amber, chartColors.purple, chartColors.green],
                    borderWidth: 2,
                    borderColor: "#ffffff",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "bottom", labels: { boxWidth: 12, color: "#3d4754" } },
            },
        },
    });
}

async function renderCountryRevenue() {
    const data = await fetchChartData("/api/charts/country-revenue/");
    if (!data.length) return renderEmpty("countryRevenueChart");
    new Chart(document.getElementById("countryRevenueChart"), {
        type: "bar",
        data: {
            labels: data.map((item) => item.label),
            datasets: [
                {
                    label: "Revenue",
                    data: data.map((item) => item.revenue),
                    backgroundColor: chartColors.teal,
                    borderRadius: 4,
                },
            ],
        },
        options: baseOptions({
            indexAxis: "y",
            scales: {
                x: { grid: { color: chartColors.grid }, ticks: { color: "#68717d", callback: (value) => money(value) } },
                y: { grid: { display: false }, ticks: { color: "#68717d" } },
            },
        }),
    });
}

document.addEventListener("DOMContentLoaded", () => {
    renderMonthlyRevenue();
    renderCategoryRevenue();
    renderRegionLateDelivery();
    renderShippingMode();
    renderCountryRevenue();
});
