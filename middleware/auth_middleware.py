import json
from functools import wraps
from urllib import request as urlrequest

import jwt
from flask import g, jsonify, request


class AuthError(Exception):
    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AzureB2CAuth:
    def __init__(
        self,
        tenant_name,
        tenant_domain,
        policy_name,
        client_id,
        audience="",
        required_scopes="",
    ):
        self.tenant_name = tenant_name
        self.tenant_domain = tenant_domain or (
            f"{tenant_name}.onmicrosoft.com" if tenant_name else ""
        )
        self.policy_name = policy_name
        self.client_id = client_id
        self.audience = audience or client_id
        self.required_scopes = [
            scope.strip() for scope in required_scopes.split(",") if scope.strip()
        ]
        self.is_enabled = bool(
            self.tenant_name and self.tenant_domain and self.policy_name and self.client_id
        )

        if self.is_enabled:
            self.known_authority = f"{self.tenant_name}.b2clogin.com"
            self.authority = (
                f"https://{self.known_authority}/"
                f"{self.tenant_domain}/{self.policy_name}"
            )
            self.openid_config_url = (
                f"{self.authority}/v2.0/.well-known/openid-configuration"
            )
        else:
            self.known_authority = ""
            self.authority = ""
            self.openid_config_url = ""

        self._openid_config = None
        self._jwks_client = None

    def ensure_configured(self):
        if not self.is_enabled:
            raise AuthError(
                "Azure AD B2C authentication is not configured. Set the AZURE_B2C_* "
                "environment variables before using protected routes.",
                status_code=503,
            )

    def _fetch_openid_config(self):
        self.ensure_configured()
        if self._openid_config:
            return self._openid_config

        with urlrequest.urlopen(self.openid_config_url, timeout=15) as response:
            self._openid_config = json.loads(response.read().decode("utf-8"))

        return self._openid_config

    def _get_jwks_client(self):
        if self._jwks_client:
            return self._jwks_client

        openid_config = self._fetch_openid_config()
        self._jwks_client = jwt.PyJWKClient(openid_config["jwks_uri"])
        return self._jwks_client

    def validate_token(self, token):
        self.ensure_configured()

        try:
            signing_key = self._get_jwks_client().get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self._fetch_openid_config()["issuer"],
            )
        except Exception as exc:
            raise AuthError(f"Invalid or expired token: {exc}") from exc

        return claims

    @staticmethod
    def extract_user(claims):
        emails = claims.get("emails") or []
        email = (
            claims.get("email")
            or claims.get("preferred_username")
            or (emails[0] if emails else "")
        )

        return {
            "userId": claims.get("oid") or claims.get("sub") or "",
            "email": email,
            "name": claims.get("name") or "",
            "roles": claims.get("roles") or [],
            "claims": claims,
        }


def _extract_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthError("Missing Authorization bearer token.")
    return auth_header.split(" ", 1)[1].strip()


def requires_auth(auth_client):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            try:
                token = _extract_bearer_token()
                claims = auth_client.validate_token(token)
                g.current_user = auth_client.extract_user(claims)
            except AuthError as exc:
                return jsonify({"error": exc.message}), exc.status_code

            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def requires_role(auth_client, allowed_roles):
    def decorator(view_func):
        @requires_auth(auth_client)
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user_roles = set(g.current_user.get("roles", []))
            if not user_roles.intersection(set(allowed_roles)):
                return jsonify({"error": "You do not have permission to access this route."}), 403
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
