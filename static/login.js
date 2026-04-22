import {
    getCurrentUser,
    initAuth,
    isAuthConfigured,
    login,
    onAuthStateChanged,
    openDashboard
} from "./auth.js";

const authStatus = document.getElementById("auth-status");
const loginButton = document.getElementById("login-button");
const dashboardButton = document.getElementById("dashboard-button");

function updateAuthUi({ enabled, user, error }) {
    if (error) {
        authStatus.textContent = error.message;
        return;
    }

    if (!enabled) {
        authStatus.textContent =
            "Easy Auth is not available in this environment. Open the dashboard only after enabling App Service Authentication.";
        loginButton.disabled = true;
        dashboardButton.disabled = false;
        return;
    }

    loginButton.disabled = false;
    dashboardButton.disabled = false;

    if (user) {
        authStatus.textContent = `Signed in as ${user.email || user.userId}. Redirecting to your dashboard...`;
        window.location.assign("/dashboard");
        return;
    }

    authStatus.textContent = "Sign in with your App Service identity to save recipes and sync them across devices.";
}

loginButton.addEventListener("click", () => {
    login();
});

dashboardButton.addEventListener("click", () => {
    openDashboard();
});

onAuthStateChanged(updateAuthUi);

try {
    const authState = await initAuth();
    updateAuthUi({
        enabled: isAuthConfigured() || authState.enabled,
        user: authState.user
    });
} catch (error) {
    updateAuthUi({ enabled: false, user: getCurrentUser(), error });
}
