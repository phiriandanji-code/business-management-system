
const token = sessionStorage.getItem("access_token");

const userRole = document.getElementById("userRole");
const welcomeTitle = document.getElementById("welcomeTitle");
const businessName = document.getElementById("businessName");

// ==========================================
// DASHBOARD INITIALIZATION
// ==========================================

async function loadDashboard() {
    if (!token) {
        window.location.href = "/";
        return;
    }

    try {
        const headers = {
            "Authorization": `Bearer ${token}`
        };

        const [userResponse, businessResponse] = await Promise.all([
            fetch("/users/me", { headers }),
            fetch("/my-businesses/", { headers })
        ]);

        if (userResponse.status === 401 ||
            businessResponse.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!userResponse.ok || !businessResponse.ok) {
            throw new Error("Unable to load account information.");
        }

        const user = await userResponse.json();
        const businesses = await businessResponse.json();

        if (!businesses.length) {
            throw new Error("No active business membership found.");
        }

        sessionStorage.setItem("businesses", JSON.stringify(businesses));

        const business = businesses[0];
        const role = String(business.role || "").toLowerCase();

        userRole.textContent = role.toUpperCase();
        welcomeTitle.textContent = `Welcome, ${user.full_name}`;

        businessName.textContent =
            `${business.business_name} | ${business.business_type}`;

        if (!["owner", "manager", "cashier"].includes(role)) {
            throw new Error("Your business role is not recognized.");
        }

        const staffLink = document.getElementById("staffLink");
        const reportsLink = document.getElementById("reportsLink");
        const supplierCreditLink =
            document.getElementById("supplierCreditLink");
        const supplierCreditSection =
            document.getElementById("supplierCredit");
const backupsLink =
    document.getElementById("backupsLink");

const backupsSection =
    document.getElementById("backups");

        if (role === "cashier") {
            staffLink.hidden = true;
            reportsLink.hidden = true;
        }

        if (role === "owner" || role === "manager") {
            supplierCreditLink.hidden = false;
            supplierCreditSection.hidden = false;
        } else {
            supplierCreditLink.hidden = true;
            supplierCreditSection.hidden = true;
        }
if (role === "owner") {
    backupsLink.hidden = false;
    backupsSection.hidden = false;
} else {
    backupsLink.hidden = true;
    backupsSection.hidden = true;
}

        await loadBusinessProfile(business.business_id, role);

        // LOAD DASHBOARD MODULES AFTER BUSINESS INFORMATION IS READY

        await loadProducts();
        await loadInventoryAlerts();
        await loadStockAdjustmentProducts();
        await loadStockMovements();
        await loadSalesHistory();
        await loadBusinessReports();
        await loadPOSProducts();
        await loadStaffManagement();
await loadCustomerManagement();

        if (role === "owner" || role === "manager") {
            await loadSupplierCreditManagement();
        }

        renderPOSCart();

    } catch (error) {
        userRole.textContent = "Account Error";
        welcomeTitle.textContent = "Unable to load dashboard";
        businessName.textContent = error.message;
    }
}

document.getElementById("logoutButton").addEventListener(
    "click",
    function () {
        sessionStorage.clear();
        window.location.href = "/";
    }
);


// ==========================================
// PRODUCT MANAGEMENT
// ==========================================

async function loadProducts() {
    const productsMessage =
        document.getElementById("productsMessage");

    const tableBody =
        document.getElementById("productsTableBody");

    try {
        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) {
            throw new Error("No business information found.");
        }

        const businessId = businesses[0].business_id;

        const response = await fetch(
            `/businesses/${businessId}/products`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to retrieve products.");
        }

        const products = await response.json();

        // INVENTORY OVERVIEW INDICATORS

        const totalActiveProducts =
            document.getElementById("totalActiveProducts");

        const totalStockUnits =
            document.getElementById("totalStockUnits");

        const totalLowStockProducts =
            document.getElementById("totalLowStockProducts");

        const totalOutOfStockProducts =
            document.getElementById("totalOutOfStockProducts");

        const stockUnits = products.reduce(
            (total, product) =>
                total + Number(product.stock_quantity || 0),
            0
        );

        const lowStockCount = products.filter(
            product =>
                Number(product.stock_quantity) > 0 &&
                Number(product.stock_quantity) <=
                Number(product.low_stock_threshold)
        ).length;

        const outOfStockCount = products.filter(
            product => Number(product.stock_quantity) === 0
        ).length;

        totalActiveProducts.textContent = products.length;
        totalStockUnits.textContent =
            stockUnits.toLocaleString("en-US");

        totalLowStockProducts.textContent = lowStockCount;
        totalOutOfStockProducts.textContent = outOfStockCount;

        tableBody.replaceChildren();

        if (products.length === 0) {
            productsMessage.textContent =
                "No products registered yet.";
            return;
        }

        products.forEach(product => {
            const row = document.createElement("tr");

            const status =
                Number(product.stock_quantity) === 0
                    ? "Out of Stock"
                    : Number(product.stock_quantity) <=
                        Number(product.low_stock_threshold)
                        ? "Low Stock"
                        : "In Stock";

            const values = [
                product.name,
                product.sku,
                `MWK ${Number(product.selling_price).toLocaleString(
                    "en-US",
                    { minimumFractionDigits: 2 }
                )}`,
                product.stock_quantity,
                status
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value ?? "";
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });

        productsMessage.textContent =
            `${products.length} product(s) registered.`;

    } catch (error) {
        productsMessage.textContent = error.message;
    }
}


// ==========================================
// REGISTER PRODUCT
// ==========================================

const productForm = document.getElementById("productForm");

productForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businesses.length) return;

    const role = String(businesses[0].role || "").toLowerCase();

    if (!["owner", "manager"].includes(role)) return;

    const businessId = businesses[0].business_id;

    const message =
        document.getElementById("productFormMessage");

    const button =
        document.getElementById("registerProductButton");

    const productData = {
        name: document.getElementById("productName").value.trim(),
        sku: document.getElementById("productSku").value.trim(),
        description:
            document.getElementById("productDescription").value.trim() || null,
        cost_price:
            Number(document.getElementById("productCostPrice").value),
        selling_price:
            Number(document.getElementById("productSellingPrice").value),
        stock_quantity:
            Number(document.getElementById("productStock").value),
        low_stock_threshold:
            Number(document.getElementById("productThreshold").value)
    };

    button.disabled = true;
    button.textContent = "Registering...";

    try {
        const response = await fetch(
            `/businesses/${businessId}/products`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(productData)
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Product registration failed."
            );
        }

        message.style.color = "green";
        message.textContent =
            `${result.name} registered successfully.`;

        productForm.reset();
        document.getElementById("productThreshold").value = 5;

        await loadProducts();
        await loadInventoryAlerts();
        await loadPOSProducts();
        await loadStockAdjustmentProducts();

    } catch (error) {
        message.style.color = "red";
        message.textContent = error.message;

    } finally {
        button.disabled = false;
        button.textContent = "Register Product";
    }
});


// ==========================================
// INVENTORY ALERTS
// ==========================================

async function loadInventoryAlerts() {
    const inventoryMessage =
        document.getElementById("inventoryMessage");

    const lowStockProducts =
        document.getElementById("lowStockProducts");

    try {
        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) {
            throw new Error("No business information found.");
        }

        const businessId = businesses[0].business_id;

        const response = await fetch(
            `/businesses/${businessId}/low-stock-products`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to retrieve inventory alerts.");
        }

        const products = await response.json();

        lowStockProducts.replaceChildren();

        if (products.length === 0) {
            inventoryMessage.textContent =
                "All products have sufficient stock. No low-stock alerts.";
            return;
        }

        inventoryMessage.textContent =
            `${products.length} product(s) require stock replenishment.`;

        products.forEach(product => {
            const alertCard = document.createElement("div");

            alertCard.style.background = "#fff3cd";
            alertCard.style.padding = "18px";
            alertCard.style.marginTop = "12px";
            alertCard.style.borderRadius = "8px";

            const productTitle = document.createElement("h3");
            productTitle.textContent = product.name;

            const stockInformation = document.createElement("p");

            stockInformation.textContent =
                `Available stock: ${product.stock_quantity} | ` +
                `Minimum stock level: ${product.low_stock_threshold}`;

            alertCard.appendChild(productTitle);
            alertCard.appendChild(stockInformation);

            lowStockProducts.appendChild(alertCard);
        });

    } catch (error) {
        inventoryMessage.textContent = error.message;
    }
}


// ==========================================
// STOCK ADJUSTMENT
// ==========================================

async function loadStockAdjustmentProducts() {
    const productSelect =
        document.getElementById("adjustmentProduct");

    try {
        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) {
            throw new Error("No business information found.");
        }

        const businessId = businesses[0].business_id;

        const response = await fetch(
            `/businesses/${businessId}/products`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to load products.");
        }

        const products = await response.json();

        productSelect.replaceChildren();

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Select a product";
        productSelect.appendChild(defaultOption);

        products.forEach(product => {
            const option = document.createElement("option");

            option.value = product.id;
            option.textContent =
                `${product.name} (${product.sku}) - Stock: ${product.stock_quantity}`;

            productSelect.appendChild(option);
        });

    } catch (error) {
        document.getElementById(
            "stockAdjustmentMessage"
        ).textContent = error.message;
    }
}


// RECORD STOCK ADJUSTMENT

const stockAdjustmentForm =
    document.getElementById("stockAdjustmentForm");

stockAdjustmentForm.addEventListener(
    "submit",
    async function (event) {
        event.preventDefault();

        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) return;

        const role = String(
            businesses[0].role || ""
        ).toLowerCase();

        if (!["owner", "manager"].includes(role)) return;

        const businessId = businesses[0].business_id;

        const productId =
            document.getElementById("adjustmentProduct").value;

        const movementType =
            document.getElementById("adjustmentType").value;

        const quantity = Number(
            document.getElementById("adjustmentQuantity").value
        );

        const reason =
            document.getElementById("adjustmentReason").value.trim();

        const message =
            document.getElementById("stockAdjustmentMessage");

        const button =
            document.getElementById("stockAdjustmentButton");

        if (!productId || !Number.isInteger(quantity) || quantity <= 0) {
            message.style.color = "red";
            message.textContent =
                "Select a product and enter a valid quantity.";
            return;
        }

        if (!["add", "remove"].includes(movementType)) {
            message.style.color = "red";
            message.textContent = "Select a valid movement type.";
            return;
        }

        if (!reason) {
            message.style.color = "red";
            message.textContent = "Please provide a reason.";
            return;
        }

        const adjustmentData = {
            movement_type: movementType,
            quantity: quantity,
            reason: reason
        };

        button.disabled = true;
        button.textContent = "Recording...";

        try {
            const response = await fetch(
                `/businesses/${businessId}/products/${productId}/stock-adjustments`,
                {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(adjustmentData)
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Stock adjustment failed."
                );
            }

            message.style.color = "green";
            message.textContent =
                "Stock adjustment recorded successfully.";

            stockAdjustmentForm.reset();

            await loadStockAdjustmentProducts();
            await loadProducts();
            await loadInventoryAlerts();
            await loadPOSProducts();
            await loadStockMovements();

        } catch (error) {
            message.style.color = "red";
            message.textContent = error.message;

        } finally {
            button.disabled = false;
            button.textContent = "Record Stock Adjustment";
        }
    }
);


// ==========================================
// STOCK MOVEMENT HISTORY
// ==========================================

async function loadStockMovements() {
    const message =
        document.getElementById("stockMovementsMessage");

    const tableBody =
        document.getElementById("stockMovementsTableBody");

    try {
        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) {
            throw new Error("No business information found.");
        }

        const businessId = businesses[0].business_id;

        message.textContent = "Loading stock movement history...";

        const response = await fetch(
            `/businesses/${businessId}/stock-movements`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error(
                "Unable to retrieve stock movement history."
            );
        }

        const movements = await response.json();

        tableBody.replaceChildren();

        if (!movements.length) {
            message.textContent =
                "No stock movements have been recorded yet.";
            return;
        }

        movements.forEach(movement => {
            const row = document.createElement("tr");

            const movementDate = new Date(movement.created_at);

            const formattedDate =
                isNaN(movementDate.getTime())
                    ? "Date unavailable"
                    : movementDate.toLocaleString();

            const values = [
                movement.product_id,
                String(movement.movement_type || "").toUpperCase(),
                movement.quantity,
                movement.stock_before,
                movement.stock_after,
                movement.reason,
                formattedDate,
                movement.user_id
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value ?? "";
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });

        message.textContent =
            `${movements.length} stock movement(s) recorded.`;

    } catch (error) {
        message.textContent = error.message;
    }
}


// ==========================================
// SALES HISTORY
// ==========================================

async function loadSalesHistory() {
    const salesMessage =
        document.getElementById("salesMessage");

    const salesTableBody =
        document.getElementById("salesTableBody");

    try {
        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) {
            throw new Error("No business information found.");
        }

        const businessId = businesses[0].business_id;

        const response = await fetch(
            `/businesses/${businessId}/sales`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to retrieve sales records.");
        }

        const sales = await response.json();

        salesTableBody.replaceChildren();

        if (sales.length === 0) {
            salesMessage.textContent =
                "No sales transactions have been recorded yet.";
            return;
        }

        salesMessage.textContent =
            `${sales.length} sales transaction(s) found.`;

        sales.forEach(sale => {
            const row = document.createElement("tr");

            const receiptNumber =
                `SALE-${String(sale.id).padStart(6, "0")}`;

            const saleDate = new Date(sale.created_at);

            const formattedDate = isNaN(saleDate.getTime())
                ? "Date unavailable"
                : saleDate.toLocaleString();

            const totalQuantity = (sale.items || []).reduce(
                (sum, item) => sum + Number(item.quantity || 0),
                0
            );

            const formattedTotal =
                `MWK ${Number(sale.total_amount).toLocaleString(
                    "en-US",
                    { minimumFractionDigits: 2 }
                )}`;

            const values = [
                receiptNumber,
                formattedDate,
                sale.user_id,
                totalQuantity,
                formattedTotal
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value ?? "";
                row.appendChild(cell);
            });

            const actionCell = document.createElement("td");

            const printButton = document.createElement("button");
            printButton.textContent = "Print Receipt";
            printButton.type = "button";

            printButton.addEventListener("click", async function () {
                const printWindow = window.open("", "_blank");

                if (!printWindow) {
                    alert("Please allow pop-ups to print receipts.");
                    return;
                }

                printWindow.document.write(
                    "<p>Preparing receipt...</p>"
                );

                try {
                    const printResponse = await fetch(
                        `/businesses/${businessId}/sales/${sale.id}/print`,
                        {
                            headers: {
                                "Authorization": `Bearer ${token}`
                            }
                        }
                    );

                    if (!printResponse.ok) {
                        throw new Error("Unable to retrieve this receipt.");
                    }

                    const receiptHTML = await printResponse.text();

                    printWindow.document.open();
                    printWindow.document.write(receiptHTML);
                    printWindow.document.close();

                } catch (error) {
                    printWindow.document.body.textContent =
                        error.message;
                }
            });

            actionCell.appendChild(printButton);
            row.appendChild(actionCell);

            salesTableBody.appendChild(row);
        });

    } catch (error) {
        salesMessage.textContent = error.message;
    }
}


// ==========================================
// STAFF MANAGEMENT
// ==========================================

async function loadStaffManagement() {
    const staffSection =
        document.getElementById("staff");

    const staffLink =
        document.getElementById("staffLink");

    const staffMessage =
        document.getElementById("staffMessage");

    const staffTableBody =
        document.getElementById("staffTableBody");

    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businesses.length ||
        String(businesses[0].role).toLowerCase() !== "owner") {
        staffSection.hidden = true;
        staffLink.hidden = true;
        return;
    }

    staffSection.hidden = false;
    staffLink.hidden = false;

    try {
        const businessId = businesses[0].business_id;

        const response = await fetch(
            `/businesses/${businessId}/staff`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to retrieve employee records.");
        }

        const employees = await response.json();

        staffTableBody.replaceChildren();

        staffMessage.textContent =
            `${employees.length} employee(s) registered.`;

        employees.forEach(employee => {
            const row = document.createElement("tr");

            const values = [
                employee.full_name,
                employee.email,
                employee.role.toUpperCase(),
                employee.is_active ? "Active" : "Inactive"
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            const actionCell = document.createElement("td");

            const statusButton = document.createElement("button");

            statusButton.textContent = employee.is_active
                ? "Deactivate"
                : "Activate";

            statusButton.addEventListener("click", async function () {
                statusButton.disabled = true;

                try {
                    const updateResponse = await fetch(
                        `/businesses/${businessId}/staff/${employee.user_id}/status`,
                        {
                            method: "PATCH",
                            headers: {
                                "Authorization": `Bearer ${token}`,
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                is_active: !employee.is_active
                            })
                        }
                    );

                    if (!updateResponse.ok) {
                        throw new Error(
                            "Unable to update employee status."
                        );
                    }

                    await loadStaffManagement();

                } catch (error) {
                    staffMessage.textContent = error.message;
                    statusButton.disabled = false;
                }
            });

            actionCell.appendChild(statusButton);
            row.appendChild(actionCell);

            staffTableBody.appendChild(row);
        });

    } catch (error) {
        staffMessage.textContent = error.message;
    }
}


// ==========================================
// REGISTER STAFF
// ==========================================

const staffForm = document.getElementById("staffForm");

staffForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businesses.length ||
        String(businesses[0].role).toLowerCase() !== "owner") {
        return;
    }

    const businessId = businesses[0].business_id;

    const message =
        document.getElementById("staffFormMessage");

    const button =
        document.getElementById("registerStaffButton");

    const staffData = {
        full_name: document.getElementById("staffName").value.trim(),
        email: document.getElementById("staffEmail").value.trim(),
        password: document.getElementById("staffPassword").value,
        role: document.getElementById("staffRole").value
    };

    button.disabled = true;
    button.textContent = "Registering...";

    try {
        const response = await fetch(
            `/businesses/${businessId}/staff`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(staffData)
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Employee registration failed."
            );
        }

        message.style.color = "green";
        message.textContent =
            `${result.full_name} registered successfully as ${result.role}.`;

        staffForm.reset();

        await loadStaffManagement();

    } catch (error) {
        message.style.color = "red";
        message.textContent = error.message;

    } finally {
        button.disabled = false;
        button.textContent = "Register Employee";
    }
});


// ==========================================
// BUSINESS PERFORMANCE REPORTS
// ==========================================

async function loadBusinessReports(startDate = "", endDate = "") {
    const section =
        document.getElementById("reports");

    const reportsLink =
        document.getElementById("reportsLink");

    const reportsMessage =
        document.getElementById("reportsMessage");

    const topProductsTableBody =
        document.getElementById("topProductsTableBody");

    const startInput =
        document.getElementById("reportStartDate");

    const endInput =
        document.getElementById("reportEndDate");

    const applyButton =
        document.getElementById("applyReportFilters");

    const resetButton =
        document.getElementById("resetReportFilters");

    if (applyButton && !applyButton.dataset.bound) {
        applyButton.dataset.bound = "true";

        applyButton.addEventListener("click", function () {
            const start = startInput.value;
            const end = endInput.value;

            if (start && end && start > end) {
                reportsMessage.textContent =
                    "Start date cannot be after end date.";
                return;
            }

            loadBusinessReports(start, end);
        });

        resetButton.addEventListener("click", function () {
            startInput.value = "";
            endInput.value = "";
            loadBusinessReports();
        });
    }

    try {
        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) {
            throw new Error("No business information found.");
        }

        const business = businesses[0];
        const role = String(business.role || "").toLowerCase();

        if (!["owner", "manager"].includes(role)) {
            section.hidden = true;
            reportsLink.hidden = true;
            return;
        }

        const businessId = business.business_id;

        const params = new URLSearchParams();

        if (startDate) params.set("start_date", startDate);
        if (endDate) params.set("end_date", endDate);

        const query = params.toString();

        const url =
            `/businesses/${businessId}/reports/summary` +
            (query ? `?${query}` : "");

        reportsMessage.textContent = "Loading business reports...";

        const response = await fetch(url, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to retrieve business reports.");
        }

        const report = await response.json();

        const formatCurrency = value =>
            `MWK ${Number(value).toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}`;

        document.getElementById("reportTotalRevenue").textContent =
            formatCurrency(report.total_revenue);

        document.getElementById("reportTransactions").textContent =
            report.transaction_count;

        document.getElementById("reportUnitsSold").textContent =
            report.units_sold;

        document.getElementById("reportAverageTransaction").textContent =
            formatCurrency(report.average_transaction);

// PROFIT AND LOSS STATEMENT

document.getElementById("plRevenue").textContent =
    formatCurrency(report.total_revenue);

document.getElementById("plCogs").textContent =
    formatCurrency(report.total_cogs);

document.getElementById("plGrossProfit").textContent =
    formatCurrency(report.gross_profit);

document.getElementById("plExpenses").textContent =
    formatCurrency(report.total_expenses);

document.getElementById("plOperatingProfit").textContent =
    formatCurrency(report.operating_profit);

document.getElementById("plInterestIncome").textContent =
    formatCurrency(report.customer_loan_interest_income);

document.getElementById("plInterestExpense").textContent =
    formatCurrency(report.borrowed_loan_interest_expense);

document.getElementById("plNetProfit").textContent =
    formatCurrency(report.profit_after_finance);
// NET PROFIT MARGIN
const netProfitMargin = Number(report.total_revenue) > 0
    ? (Number(report.profit_after_finance) / Number(report.total_revenue)) * 100
    : 0;

document.getElementById("reportProfitMargin").textContent =
    `${netProfitMargin.toFixed(2)}%`;
// GROSS PROFIT MARGIN
const grossProfitMargin = Number(report.total_revenue) > 0
    ? (Number(report.gross_profit) / Number(report.total_revenue)) * 100
    : 0;

document.getElementById("reportGrossProfitMargin").textContent =
    `${grossProfitMargin.toFixed(2)}%`;
// OPERATING PROFIT MARGIN
const operatingProfitMargin = Number(report.total_revenue) > 0
    ? (Number(report.operating_profit) / Number(report.total_revenue)) * 100
    : 0;

document.getElementById("reportOperatingProfitMargin").textContent =
    `${operatingProfitMargin.toFixed(2)}%`;
// NET PROFIT AFTER FINANCE
const netProfitAfterFinance = Number(report.profit_after_finance) || 0;

document.getElementById("reportNetProfitAfterFinance").textContent =
    `MWK ${netProfitAfterFinance.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
// TOTAL OPERATING EXPENSES
const totalOperatingExpenses = Number(report.total_expenses) || 0;

document.getElementById("reportTotalExpenses").textContent =
    `MWK ${totalOperatingExpenses.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
// TOTAL COST OF GOODS SOLD (COGS)
const totalCOGS = Number(report.total_cogs) || 0;

document.getElementById("reportTotalCOGS").textContent =
    `MWK ${totalCOGS.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
// GROSS PROFIT
const grossProfit = Number(report.gross_profit) || 0;

document.getElementById("reportGrossProfit").textContent =
    `MWK ${grossProfit.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
        topProductsTableBody.replaceChildren();

        if (!report.top_products.length) {
            reportsMessage.textContent =
                "Reports loaded. No sales products recorded yet.";
        } else {
            reportsMessage.textContent =
                "Business performance reports loaded successfully.";

            report.top_products.forEach(product => {
                const row = document.createElement("tr");

                const values = [
                    product.product_name,
                    product.sku,
                    product.quantity_sold,
                    formatCurrency(product.sales_value)
                ];

                values.forEach(value => {
                    const cell = document.createElement("td");
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                topProductsTableBody.appendChild(row);
            });
        }

    } catch (error) {
        reportsMessage.textContent = error.message;
    }
}


// ==========================================
// KABOWA POINT OF SALE (POS)
// ==========================================

let posProducts = [];
let posCart = [];

const posProductSelect =
    document.getElementById("posProduct");

const posQuantityInput =
    document.getElementById("posQuantity");

const posCartBody =
    document.getElementById("posCartBody");

const posTotalDisplay =
    document.getElementById("posTotal");

const posMessage =
    document.getElementById("posMessage");

const addToCartButton =
    document.getElementById("addToCartButton");

const completeSaleButton =
    document.getElementById("completeSaleButton");


function formatPOSCurrency(amount) {
    return `MWK ${Number(amount).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}


// LOAD AVAILABLE PRODUCTS

async function loadPOSProducts() {
    try {
        const businesses = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businesses.length) {
            throw new Error("No business information found.");
        }

        const businessId = businesses[0].business_id;

        const response = await fetch(
            `/businesses/${businessId}/products`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to load available products.");
        }

        posProducts = await response.json();

        posProductSelect.replaceChildren();

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Select a product";

        posProductSelect.appendChild(defaultOption);

        posProducts.forEach(product => {
            if (!product.is_active || product.stock_quantity <= 0) {
                return;
            }

            const option = document.createElement("option");

            option.value = product.id;

            option.textContent =
                `${product.name} (${product.sku}) - ` +
                `${formatPOSCurrency(product.selling_price)} ` +
                `| Stock: ${product.stock_quantity}`;

            posProductSelect.appendChild(option);
        });

        posMessage.textContent =
            `${posProducts.filter(
                p => p.is_active && p.stock_quantity > 0
            ).length} available product(s).`;

    } catch (error) {
        posMessage.textContent = error.message;
    }
}


// DISPLAY SHOPPING CART

function renderPOSCart() {
    posCartBody.replaceChildren();

    let total = 0;

    posCart.forEach(item => {
        const subtotal =
            Number(item.selling_price) * item.quantity;

        total += subtotal;

        const row = document.createElement("tr");

        const productCell = document.createElement("td");
        productCell.textContent = item.name;

        const priceCell = document.createElement("td");
        priceCell.textContent =
            formatPOSCurrency(item.selling_price);

        const quantityCell = document.createElement("td");
        quantityCell.textContent = item.quantity;

        const subtotalCell = document.createElement("td");
        subtotalCell.textContent =
            formatPOSCurrency(subtotal);

        const actionCell = document.createElement("td");

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.textContent = "Remove";

        removeButton.addEventListener("click", function () {
            posCart = posCart.filter(
                cartItem => cartItem.product_id !== item.product_id
            );

            renderPOSCart();
        });

        actionCell.appendChild(removeButton);

        row.append(
            productCell,
            priceCell,
            quantityCell,
            subtotalCell,
            actionCell
        );

        posCartBody.appendChild(row);
    });

    posTotalDisplay.textContent =
        formatPOSCurrency(total);

    completeSaleButton.disabled =
        posCart.length === 0;
}


// ADD PRODUCT TO CART

addToCartButton.addEventListener("click", function () {
    const productId = Number(posProductSelect.value);
    const quantity = Number(posQuantityInput.value);

    if (!productId) {
        posMessage.textContent = "Please select a product.";
        return;
    }

    if (!Number.isInteger(quantity) || quantity <= 0) {
        posMessage.textContent =
            "Enter a valid positive quantity.";
        return;
    }

    const product = posProducts.find(
        item => item.id === productId
    );

    if (!product) {
        posMessage.textContent =
            "Selected product was not found.";
        return;
    }

    const existingItem = posCart.find(
        item => item.product_id === productId
    );

    const existingQuantity = existingItem
        ? existingItem.quantity
        : 0;

    if (existingQuantity + quantity > product.stock_quantity) {
        posMessage.textContent =
            `Insufficient stock. Available: ${product.stock_quantity}.`;
        return;
    }

    if (existingItem) {
        existingItem.quantity += quantity;
    } else {
        posCart.push({
            product_id: product.id,
            name: product.name,
            selling_price: Number(product.selling_price),
            quantity: quantity
        });
    }

    posQuantityInput.value = 1;

    posMessage.textContent =
        "Product added to shopping cart.";

    renderPOSCart();
});


// COMPLETE CUSTOMER SALE

completeSaleButton.addEventListener("click", async function () {
    if (!posCart.length) {
        posMessage.textContent = "Your shopping cart is empty.";
        return;
    }

    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businesses.length) {
        posMessage.textContent =
            "Business information unavailable.";
        return;
    }

    const businessId = businesses[0].business_id;

    completeSaleButton.disabled = true;
    addToCartButton.disabled = true;

    posMessage.textContent = "Processing customer sale...";

    try {
        const response = await fetch(
            `/businesses/${businessId}/sales`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    items: posCart.map(item => ({
                        product_id: item.product_id,
                        quantity: item.quantity
                    }))
                })
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        const result = await response.json();

        if (!response.ok) {
            const detail = Array.isArray(result.detail)
                ? result.detail.map(item => item.msg).join(", ")
                : result.detail;

            throw new Error(
                detail || "Unable to complete the sale."
            );
        }

        const receiptNumber =
            `SALE-${String(result.id).padStart(6, "0")}`;

        posCart = [];

        renderPOSCart();

        posMessage.textContent =
            `Sale completed successfully! ` +
            `Receipt: ${receiptNumber}. ` +
            `Total: ${formatPOSCurrency(result.total_amount)}.`;

        await loadPOSProducts();
        await loadProducts();
        await loadInventoryAlerts();
        await loadStockAdjustmentProducts();
        await loadStockMovements();
        await loadSalesHistory();
        await loadBusinessReports();

    } catch (error) {
        posMessage.textContent = error.message;

    } finally {
        addToCartButton.disabled = false;
        completeSaleButton.disabled = posCart.length === 0;
    }
});


// ==========================================
// SUPPLIER CREDIT MANAGEMENT
// ==========================================

async function loadSupplierCreditManagement() {
    const businessList = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businessList.length) {
        console.error("No business information found.");
        return;
    }

    const businessId = businessList[0].business_id;

    const message =
        document.getElementById("supplierCreditMessage");

    const tableBody =
        document.getElementById("supplierCreditTableBody");

    try {
        message.textContent =
            "Loading supplier credit records...";

        const headers = {
            "Authorization": `Bearer ${token}`
        };

        const [creditResponse, supplierResponse] = await Promise.all([
            fetch(
                `/businesses/${businessId}/supplier-credits`,
                { headers }
            ),
            fetch(
                `/businesses/${businessId}/suppliers`,
                { headers }
            )
        ]);

        if (creditResponse.status === 401 ||
            supplierResponse.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        if (!creditResponse.ok) {
            throw new Error(
                "Could not load supplier credit records."
            );
        }

        if (!supplierResponse.ok) {
            throw new Error("Could not load suppliers.");
        }

        const credits = await creditResponse.json();
        const suppliers = await supplierResponse.json();

        const supplierNames = {};

        suppliers.forEach(supplier => {
            supplierNames[supplier.id] =
                supplier.company_name;
        });

        const money = amount =>
            Number(amount || 0).toLocaleString("en-MW", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

        // SUPPLIER CREDIT TOTALS

        const totalCredit = credits.reduce(
            (sum, credit) =>
                sum +
                Number(credit.amount_paid) +
                Number(credit.balance_due),
            0
        );

        const totalPaid = credits.reduce(
            (sum, credit) =>
                sum + Number(credit.amount_paid),
            0
        );

        const totalOutstanding = credits.reduce(
            (sum, credit) =>
                sum + Number(credit.balance_due),
            0
        );

        document.getElementById(
            "supplierCreditCount"
        ).textContent = credits.length;

        document.getElementById(
            "supplierCreditTotal"
        ).textContent = "MWK " + money(totalCredit);

        document.getElementById(
            "supplierCreditPaid"
        ).textContent = "MWK " + money(totalPaid);

        document.getElementById(
            "supplierCreditOutstanding"
        ).textContent = "MWK " + money(totalOutstanding);


        // DISPLAY SUPPLIER CREDIT ACCOUNTS

        tableBody.replaceChildren();

        credits.forEach(credit => {
            const supplierName =
                supplierNames[credit.supplier_id] || "Unknown supplier";

            const originalAmount =
                Number(credit.amount_paid) + Number(credit.balance_due);

            const row = document.createElement("tr");

            const values = [
                supplierName,
                credit.purchase_id || "—",
                `MWK ${money(originalAmount)}`,
                `MWK ${money(credit.amount_paid)}`,
                `MWK ${money(credit.balance_due)}`,
                credit.due_date
                    ? new Date(credit.due_date).toLocaleDateString()
                    : "—",
                credit.status || "—"
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            const actionCell = document.createElement("td");
            const viewButton = document.createElement("button");

            viewButton.type = "button";
            viewButton.textContent = "View Payments";

            viewButton.addEventListener("click", function () {
                viewSupplierCreditPayments(credit.id);
            });

            actionCell.appendChild(viewButton);
            row.appendChild(actionCell);

            tableBody.appendChild(row);
        });


        // PAYMENT FORM OPTIONS

        const paymentSelect =
            document.getElementById("supplierCreditSelect");

        paymentSelect.replaceChildren();

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Select supplier credit account";

        paymentSelect.appendChild(defaultOption);

        credits
            .filter(credit => Number(credit.balance_due) > 0)
            .forEach(credit => {
                const supplierName =
                    supplierNames[credit.supplier_id] ||
                    "Unknown supplier";

                const option = document.createElement("option");

                option.value = credit.id;
option.dataset.balance = credit.balance_due;

option.textContent =
    `${supplierName} - Credit #${credit.id} - ` +
    `Balance: MWK ${money(credit.balance_due)}`;

paymentSelect.appendChild(option);            });


        // SUPPLIER PAYMENT HISTORY

        const historyBody = document.getElementById(
            "supplierPaymentHistoryBody"
        );

        historyBody.replaceChildren();

        credits.forEach(credit => {
            (credit.payments || []).forEach(payment => {
                const row = document.createElement("tr");

                const values = [
                    supplierNames[credit.supplier_id] || "Unknown supplier",
                    credit.id,
                    payment.payment_date
                        ? new Date(payment.payment_date).toLocaleDateString()
                        : "Date unavailable",
                    `MWK ${money(payment.amount)}`,
                    payment.reference || "—"
                ];

                values.forEach(value => {
                    const cell = document.createElement("td");
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                historyBody.appendChild(row);
            });
        });

        message.textContent =
            "Supplier credit records loaded successfully.";

    } catch (error) {
        console.error("Supplier credit error:", error);
        message.textContent = error.message;
    }
}

// ==========================================
// RECORD SUPPLIER CREDIT PAYMENT
// ==========================================

const supplierCreditPaymentForm =
    document.getElementById("supplierCreditPaymentForm");

if (supplierCreditPaymentForm) {
    const paymentMessage =
        document.getElementById("supplierPaymentMessage");

    const paymentButton =
        document.getElementById("recordSupplierPaymentButton");

    const paymentDateInput =
        document.getElementById("supplierPaymentDate");

    // Set today's date using the browser's local date.
    if (paymentDateInput && !paymentDateInput.value) {
        const today = new Date();
        const localDate =
            `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

        paymentDateInput.value = localDate;
    }

    supplierCreditPaymentForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const creditSelect =
            document.getElementById("supplierCreditSelect");

        const amountInput =
            document.getElementById("supplierPaymentAmount");

        const referenceInput =
            document.getElementById("supplierPaymentReference");

        const creditId = creditSelect.value;
        const amount = Number(amountInput.value);
        const paymentDate = paymentDateInput.value;
        const reference = referenceInput.value.trim();

        paymentMessage.textContent = "";

        if (!creditId) {
            paymentMessage.textContent =
                "Please select a supplier credit account.";
            return;
        }

        if (!Number.isFinite(amount) || amount <= 0) {
            paymentMessage.textContent =
                "Enter a valid payment amount greater than zero.";
            return;
        }

        if (!paymentDate) {
            paymentMessage.textContent =
                "Please select the payment date.";
            return;
        }

        const selectedOption =
            creditSelect.options[creditSelect.selectedIndex];

        const outstanding = Number(selectedOption.dataset.balance);

        if (!Number.isFinite(outstanding)) {
            paymentMessage.textContent =
                "Unable to verify the outstanding balance. Please refresh the page.";
            return;
        }

        if (amount > outstanding + 0.001) {
            paymentMessage.textContent =
                `Payment cannot exceed the outstanding balance of MWK ${outstanding.toLocaleString("en-MW", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                })}.`;
            return;
        }

        const businessList = JSON.parse(
            sessionStorage.getItem("businesses") || "[]"
        );

        if (!businessList.length) {
            paymentMessage.textContent =
                "Business information is unavailable. Please log in again.";
            return;
        }

        const businessId = businessList[0].business_id;

        const paymentData = {
            amount: amount,
            payment_date: `${paymentDate}T00:00:00`,
            reference: reference || null
        };

        try {
            paymentButton.disabled = true;
            paymentButton.textContent = "Recording Payment...";
            paymentMessage.textContent =
                "Please wait. Recording supplier payment...";

            const response = await fetch(
                `/businesses/${businessId}/supplier-credits/${creditId}/payments`,
                {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(paymentData)
                }
            );

            const result = await response.json().catch(() => ({}));

            if (response.status === 401) {
                sessionStorage.clear();
                window.location.href = "/";
                return;
            }

            if (!response.ok) {
                throw new Error(
                    result.detail || "Could not record supplier payment."
                );
            }

            paymentMessage.textContent =
                "Payment recorded successfully.";

            amountInput.value = "";
            referenceInput.value = "";

            await loadSupplierCreditManagement();

            paymentMessage.textContent =
                "Payment recorded successfully. Supplier credit account updated.";

        } catch (error) {
            console.error("Supplier payment error:", error);
            paymentMessage.textContent = error.message;

        } finally {
            paymentButton.disabled = false;
            paymentButton.textContent = "Record Payment";
        }
    });
}


// ==========================================
// VIEW SUPPLIER CREDIT PAYMENTS
// ==========================================

window.viewSupplierCreditPayments = async function (creditId) {
    const businessList = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businessList.length) {
        alert("Business information unavailable.");
        return;
    }

    const businessId = businessList[0].business_id;

    const money = amount =>
        Number(amount || 0).toLocaleString("en-MW", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

    try {
        const response = await fetch(
            `/businesses/${businessId}/supplier-credits/${creditId}`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Unable to load payment history."
            );
        }

        const payments = result.payments || [];

        const suppliersResponse = await fetch(
            `/businesses/${businessId}/suppliers`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (!suppliersResponse.ok) {
            throw new Error("Unable to retrieve supplier information.");
        }

        const suppliers = await suppliersResponse.json();

        const matchingSupplier = suppliers.find(
            supplier => supplier.id === result.supplier_id
        );

        const originalAmount =
            Number(result.amount_paid || 0) +
            Number(result.balance_due || 0);

        document.getElementById("modalSupplierName").textContent =
            matchingSupplier?.company_name ||
            result.supplier_name ||
            `Supplier ID ${result.supplier_id}`;

        document.getElementById("modalCreditId").textContent =
            `Credit #${creditId}`;

        document.getElementById("modalOriginalAmount").textContent =
            `MWK ${money(originalAmount)}`;

        document.getElementById("modalTotalPaid").textContent =
            `MWK ${money(result.amount_paid || 0)}`;

        document.getElementById("modalRemainingBalance").textContent =
            `MWK ${money(result.balance_due || 0)}`;

        const paymentStatus =
            String(result.status || "Unknown").toLowerCase();

        const statusElement =
            document.getElementById("modalPaymentStatus");

        statusElement.textContent = paymentStatus;

        statusElement.style.backgroundColor =
            paymentStatus === "paid" ? "#dcfce7" :
            paymentStatus === "partially_paid" ? "#ffedd5" :
            paymentStatus === "unpaid" ? "#fee2e2" : "#e2e8f0";

        statusElement.style.color =
            paymentStatus === "paid" ? "#166534" :
            paymentStatus === "partially_paid" ? "#9a3412" :
            paymentStatus === "unpaid" ? "#991b1b" : "#334155";


        // PAYMENT TRANSACTIONS

        const historyBody = document.getElementById(
            "modalPaymentHistoryBody"
        );

        historyBody.replaceChildren();

        if (payments.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 3;
            cell.textContent = "No payments recorded yet.";

            row.appendChild(cell);
            historyBody.appendChild(row);

        } else {
            payments.forEach(payment => {
                const row = document.createElement("tr");

                const values = [
                    payment.payment_date
                        ? new Date(payment.payment_date).toLocaleDateString()
                        : "Date unavailable",
                    `MWK ${money(payment.amount)}`,
                    payment.reference || "—"
                ];

                values.forEach(value => {
                    const cell = document.createElement("td");
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                historyBody.appendChild(row);
            });
        }

        document.getElementById(
            "supplierPaymentModal"
        ).hidden = false;

    } catch (error) {
        alert(error.message);
    }
};


// CLOSE SUPPLIER PAYMENT HISTORY MODAL

document.getElementById("closeSupplierPaymentModal")
    .addEventListener("click", function () {
        document.getElementById("supplierPaymentModal").hidden = true;
    });

document.getElementById("closeSupplierPaymentModalFooter")
    .addEventListener("click", function () {
        document.getElementById("supplierPaymentModal").hidden = true;
    });


// ==========================================
// BUSINESS PROFILE MANAGEMENT
// ==========================================

async function loadBusinessProfile(businessId, role) {
    const message =
        document.getElementById("businessProfileMessage");

    const form =
        document.getElementById("businessProfileForm");

    const saveButton =
        document.getElementById("saveBusinessProfileButton");

    const nameInput =
        document.getElementById("profileBusinessName");

    const typeInput =
        document.getElementById("profileBusinessType");

    const phoneInput =
        document.getElementById("profilePhone");

    const emailInput =
        document.getElementById("profileEmail");

    const addressInput =
        document.getElementById("profileAddress");

    const isOwner = String(role).toLowerCase() === "owner";

    try {
        message.textContent = "Loading business profile...";

        const response = await fetch(
            `/businesses/${businessId}/profile`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (response.status === 401) {
            sessionStorage.clear();
            window.location.href = "/";
            return;
        }

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Unable to load business profile."
            );
        }

        nameInput.value = result.name || "";
        typeInput.value = result.business_type || "";
        phoneInput.value = result.phone || "";
        emailInput.value = result.email || "";
        addressInput.value = result.address || "";

        [phoneInput, emailInput, addressInput].forEach(input => {
            input.readOnly = !isOwner;
        });

        saveButton.hidden = !isOwner;

        message.textContent = isOwner
            ? "Business profile loaded. You can update your contact details."
            : "Business contact information.";

        if (!isOwner) return;

        // PREVENT DUPLICATE FORM EVENT LISTENERS

        if (form.dataset.bound === "true") return;

        form.dataset.bound = "true";

        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            saveButton.disabled = true;
            saveButton.textContent = "Saving...";

            try {
                const updateResponse = await fetch(
                    `/businesses/${businessId}/profile`,
                    {
                        method: "PUT",
                        headers: {
                            "Authorization": `Bearer ${token}`,
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            phone: phoneInput.value.trim() || null,
                            email: emailInput.value.trim() || null,
                            address: addressInput.value.trim() || null
                        })
                    }
                );

                const updateResult = await updateResponse.json();

                if (!updateResponse.ok) {
                    throw new Error(
                        updateResult.detail ||
                        "Unable to save business profile."
                    );
                }

                message.textContent =
                    "Business profile updated successfully.";

                message.style.color = "green";

            } catch (error) {
                message.textContent = error.message;
                message.style.color = "red";

            } finally {
                saveButton.disabled = false;
                saveButton.textContent = "Save Business Profile";
            }
        });

    } catch (error) {
        message.textContent = error.message;
        message.style.color = "red";
    }
}


// ==========================================
// START DASHBOARD
// ==========================================

loadDashboard();
// ==========================================
// CUSTOMER MANAGEMENT
// ==========================================

let allCustomers = [];

async function loadCustomerManagement() {
    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businesses.length) return;

    const businessId = businesses[0].business_id;

    const customerMessage = document.getElementById("customerMessage");
    const tableBody = document.getElementById("customersTableBody");

    try {
        const response = await fetch(
            `/businesses/${businessId}/customers`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Unable to load customers.");
        }

        allCustomers = await response.json();
        displayCustomers(allCustomers);

        customerMessage.textContent =
            `${allCustomers.length} customer(s) registered.`;

    } catch (error) {
        customerMessage.textContent = error.message;
    }
}


// DISPLAY CUSTOMERS IN THE TABLE

function displayCustomers(customers) {
    const tableBody = document.getElementById("customersTableBody");

    tableBody.replaceChildren();

    customers.forEach(customer => {
        const row = document.createElement("tr");

        const nameCell = document.createElement("td");
        nameCell.textContent = customer.full_name;

        const phoneCell = document.createElement("td");
        phoneCell.textContent = customer.phone;

        const emailCell = document.createElement("td");
        emailCell.textContent = customer.email || "-";

        const addressCell = document.createElement("td");
        addressCell.textContent = customer.address || "-";

        const actionCell = document.createElement("td");
        const editButton = document.createElement("button");

        editButton.textContent = "Edit";

        editButton.addEventListener("click", function () {
            editCustomer(customer);
        });

        actionCell.appendChild(editButton);

        row.append(
            nameCell,
            phoneCell,
            emailCell,
            addressCell,
            actionCell
        );

        tableBody.appendChild(row);
    });
}


// REGISTER CUSTOMER

const customerForm = document.getElementById("customerForm");

customerForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    if (!businesses.length) return;

    const businessId = businesses[0].business_id;

    const message = document.getElementById("customerFormMessage");
    const registerButton =
        document.getElementById("registerCustomerButton");

    const customerData = {
        full_name: document.getElementById("customerName").value.trim(),
        phone: document.getElementById("customerPhone").value.trim(),
        email: document.getElementById("customerEmail").value.trim() || null,
        address: document.getElementById("customerAddress").value.trim() || null
    };

    try {
        registerButton.disabled = true;
        message.textContent = "Registering customer...";

        const response = await fetch(
            `/businesses/${businessId}/customers`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(customerData)
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Unable to register customer."
            );
        }

        message.textContent = "Customer registered successfully!";
        customerForm.reset();

        await loadCustomerManagement();

    } catch (error) {
        message.textContent = error.message;

    } finally {
        registerButton.disabled = false;
    }
});


// SEARCH CUSTOMERS

document.getElementById("customerSearch").addEventListener(
    "input",
    function () {
        const searchTerm = this.value.toLowerCase().trim();

        const filteredCustomers = allCustomers.filter(customer =>
            customer.full_name.toLowerCase().includes(searchTerm) ||
            customer.phone.toLowerCase().includes(searchTerm)
        );

        displayCustomers(filteredCustomers);

        document.getElementById("customerMessage").textContent =
            `${filteredCustomers.length} matching customer(s).`;
    }
);


// EDIT CUSTOMER

async function editCustomer(customer) {
    const fullName = prompt("Enter customer full name:", customer.full_name);

    if (fullName === null) return;

    const phone = prompt("Enter customer phone number:", customer.phone);

    if (phone === null) return;

    const email = prompt("Enter customer email:", customer.email || "");

    if (email === null) return;

    const address = prompt("Enter customer address:", customer.address || "");

    if (address === null) return;

    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    const businessId = businesses[0].business_id;

    try {
        const response = await fetch(
            `/businesses/${businessId}/customers/${customer.id}`,
            {
                method: "PUT",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    full_name: fullName.trim(),
                    phone: phone.trim(),
                    email: email.trim() || null,
                    address: address.trim() || null
                })
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Unable to update customer."
            );
        }

        alert("Customer updated successfully!");

        await loadCustomerManagement();

    } catch (error) {
        alert(error.message);
    }
}

// ==========================================
// BUSINESS BACKUP AND RESTORE
// ==========================================

function getBackupBusiness() {
    const businesses = JSON.parse(
        sessionStorage.getItem("businesses") || "[]"
    );

    const business = businesses[0];

    if (!business || String(business.role).toLowerCase() !== "owner") {
        throw new Error("Only the business owner can manage backups.");
    }

    return business;
}

function showBackupMessage(message, isError = false) {
    const messageElement = document.getElementById("backupMessage");
    messageElement.textContent = message;
    messageElement.style.color = isError ? "#dc2626" : "#15803d";
}

async function loadBackupHistory() {
    const tableBody = document.getElementById("backupsTableBody");

    try {
        const business = getBackupBusiness();

        const response = await fetch(
            `/businesses/${business.business_id}/backups`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        const backups = await response.json();

        if (!response.ok) {
            throw new Error(
                backups.detail || "Unable to load backup history."
            );
        }

        tableBody.innerHTML = "";

        if (!backups.length) {
            tableBody.innerHTML =
                '<tr><td colspan="4">No backups available.</td></tr>';
            return;
        }

        backups.forEach(backup => {
            const row = document.createElement("tr");

            const dateCell = document.createElement("td");
            dateCell.textContent =
                new Date(backup.created_at).toLocaleString();

            const typeCell = document.createElement("td");
            typeCell.textContent = backup.backup_type;

            const sizeCell = document.createElement("td");
            sizeCell.textContent =
                `${(backup.size_bytes / 1024).toFixed(2)} KB`;

            const actionsCell = document.createElement("td");

            const downloadButton = document.createElement("button");
            downloadButton.type = "button";
            downloadButton.textContent = "Download";
            downloadButton.addEventListener("click", () => {
                downloadBusinessBackup(backup.backup_id);
            });

            const restoreButton = document.createElement("button");
            restoreButton.type = "button";
            restoreButton.textContent = "Restore";
            restoreButton.addEventListener("click", () => {
                restoreBusinessBackup(backup.backup_id);
            });

            actionsCell.append(downloadButton, restoreButton);
            row.append(dateCell, typeCell, sizeCell, actionsCell);
            tableBody.appendChild(row);
        });

    } catch (error) {
        showBackupMessage(error.message, true);
    }
}

async function createBusinessBackup() {
    try {
        const business = getBackupBusiness();

        const response = await fetch(
            `/businesses/${business.business_id}/backups`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Backup creation failed.");
        }

        showBackupMessage("Backup created successfully!");
        await loadBackupHistory();

    } catch (error) {
        showBackupMessage(error.message, true);
    }
}

async function downloadBusinessBackup(backupId) {
    try {
        const business = getBackupBusiness();

        const response = await fetch(
            `/businesses/${business.business_id}/backups/${backupId}/download`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            const result = await response.json();
            throw new Error(result.detail || "Backup download failed.");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download =
            `business_${business.business_id}_${backupId}.json`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);

        showBackupMessage("Backup downloaded successfully!");

    } catch (error) {
        showBackupMessage(error.message, true);
    }
}

async function restoreBusinessBackup(backupId) {
    if (!confirm(
        "Restore this backup? Current business records will be replaced. " +
        "A safety backup will be created automatically first."
    )) {
        return;
    }

    try {
        const business = getBackupBusiness();

        const response = await fetch(
            `/businesses/${business.business_id}/backups/${backupId}/restore`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Backup restoration failed.");
        }

        showBackupMessage(
            "Business restored successfully. A safety backup was created."
        );

        await loadBackupHistory();

    } catch (error) {
        showBackupMessage(error.message, true);
    }
}

document.getElementById("createBackupButton")
    .addEventListener("click", createBusinessBackup);

document.getElementById("refreshBackupsButton")
    .addEventListener("click", loadBackupHistory);
