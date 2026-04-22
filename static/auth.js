const authStatusSubscribers = new Set();

let currentUser = null;
let authInitialized = false;
let authEnabled = true;

function emitAuthState(payload) {
    authStatusSubscribers.forEach((listener) => listener(payload));
}

function normalizeUser(principalEntry) {
    if (!principalEntry) {
        return null;
    }

    const claims = principalEntry.user_claims || [];
    const roleClaimTypes = new Set([
        "roles",
        "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
    ]);

    const findClaim = (...types) => {
        const normalized = new Set(types.map((value) => value.toLowerCase()));
        const match = claims.find((claim) => normalized.has(String(claim.typ || "").toLowerCase()));
        return match?.val || "";
    };

    const userId =
        principalEntry.user_id ||
        findClaim(
            "http://schemas.microsoft.com/identity/claims/objectidentifier",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
            "nameidentifier",
            "sub"
        );
    const email =
        principalEntry.user_details ||
        findClaim(
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "preferred_username",
            "emails"
        );
    const roles = claims
        .filter((claim) => roleClaimTypes.has(String(claim.typ || "").toLowerCase()))
        .map((claim) => claim.val);

    if (!userId && !email) {
        return null;
    }

    return {
        userId: userId || email,
        email,
        roles,
        identityProvider: principalEntry.identity_provider || ""
    };
}

async function fetchCurrentUser() {
    try {
        const response = await fetch("/.auth/me", {
            credentials: "same-origin"
        });

        if (!response.ok) {
            if (response.status === 404) {
                authEnabled = false;
                return null;
            }
            throw new Error("Unable to verify your sign-in session.");
        }

        const principals = await response.json();
        authEnabled = true;
        return normalizeUser(Array.isArray(principals) ? principals[0] : null);
    } catch (error) {
        if (error instanceof SyntaxError) {
            authEnabled = false;
            return null;
        }
        throw error;
    }
}

export async function initAuth() {
    if (authInitialized) {
        return { enabled: authEnabled, user: currentUser };
    }

    try {
        currentUser = await fetchCurrentUser();
        authInitialized = true;
        emitAuthState({ enabled: authEnabled, user: currentUser });
        return { enabled: authEnabled, user: currentUser };
    } catch (error) {
        emitAuthState({ enabled: authEnabled, user: null, error });
        throw error;
    }
}

export function login() {
    window.location.assign("/.auth/login/aad?post_login_redirect_uri=/dashboard");
}

export function openDashboard() {
    window.location.assign("/dashboard");
}

export async function logout() {
    currentUser = null;
    emitAuthState({ enabled: authEnabled, user: null });
    window.location.assign("/.auth/logout?post_logout_redirect_uri=/");
}

export function getCurrentUser() {
    return currentUser;
}

export function isAuthEnabled() {
    return authEnabled && Boolean(currentUser);
}

export function isAuthConfigured() {
    return authEnabled;
}

export function onAuthStateChanged(listener) {
    authStatusSubscribers.add(listener);
    return () => authStatusSubscribers.delete(listener);
}
