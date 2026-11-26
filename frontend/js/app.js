const API_BASE_URL = "";

const loginForm = document.getElementById("loginForm");
const loginButton = document.getElementById("loginButton");
const loginMessage = document.getElementById("loginMessage");

loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    loginButton.disabled = true;
    loginButton.textContent = "Signing in...";
    loginMessage.textContent = "";

    try {
        const loginResponse = await fetch(
            `${API_BASE_URL}/login/`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            }
        );

        const loginData = await loginResponse.json();

        if (!loginResponse.ok) {
            throw new Error(
                loginData.detail || "Login failed."
            );
        }

        const token = loginData.access_token;

        const businessResponse = await fetch(
            `${API_BASE_URL}/my-businesses/`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        const businesses = await businessResponse.json();

        if (!businessResponse.ok) {
            throw new Error(
                businesses.detail || "Unable to load your businesses."
            );
        }

        if (!businesses.length) {
            throw new Error(
                "Your account has no active business membership."
            );
        }

        sessionStorage.setItem("access_token", token);
        sessionStorage.setItem(
            "businesses",
            JSON.stringify(businesses)
        );

        loginMessage.style.color = "green";
        loginMessage.textContent = "Login successful!";

        window.location.href = "/app/dashboard.html";

    } catch (error) {
        loginMessage.style.color = "red";
        loginMessage.textContent = error.message;
    } finally {
        loginButton.disabled = false;
        loginButton.textContent = "Sign In";
    }
});