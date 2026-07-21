import pytest
from kernel.security import (
    SecurityService, UserPrincipal, AuthorizationPolicy,
    AuthProvider
)


class TestUserPrincipal:
    def test_defaults(self):
        u = UserPrincipal(id="1", username="admin")
        assert u.authenticated is False
        assert u.roles == set()
        assert u.permissions == set()

    def test_with_roles(self):
        u = UserPrincipal(id="1", username="admin", roles={"admin", "user"})
        assert "admin" in u.roles


class TestAuthorizationPolicy:
    def test_defaults(self):
        p = AuthorizationPolicy(name="test")
        assert p.deny is False
        assert p.roles == set()
        assert p.permissions == set()

    def test_deny_policy(self):
        p = AuthorizationPolicy(name="block", deny=True)
        assert p.deny is True


class TestSecurityService:
    def test_configure(self):
        svc = SecurityService()
        svc.configure(AuthProvider.API_KEY, {"key": "secret"})
        assert AuthProvider.API_KEY in svc._providers

    def test_add_api_key(self):
        svc = SecurityService()
        principal = UserPrincipal(id="1", username="admin")
        svc.add_api_key("key123", principal)
        result = svc.authenticate("key123", AuthProvider.API_KEY)
        assert result is not None
        assert result.authenticated is True
        assert result.username == "admin"

    def test_generate_api_key(self):
        svc = SecurityService()
        principal = UserPrincipal(id="1", username="admin")
        key = svc.generate_api_key(principal)
        assert key.startswith("ck_")
        result = svc.authenticate(key)
        assert result is not None
        assert result.username == "admin"

    def test_revoke_api_key(self):
        svc = SecurityService()
        principal = UserPrincipal(id="1", username="admin")
        key = svc.generate_api_key(principal)
        svc.revoke_api_key(key)
        result = svc.authenticate(key)
        assert result is None

    def test_authenticate_no_provider_fallback(self):
        svc = SecurityService()
        principal = UserPrincipal(id="1", username="admin")
        key = svc.generate_api_key(principal)
        result = svc.authenticate(key)
        assert result is not None

    def test_authenticate_unknown_key(self):
        svc = SecurityService()
        result = svc.authenticate("invalid")
        assert result is None

    def test_create_token(self):
        svc = SecurityService()
        principal = UserPrincipal(id="1", username="admin")
        token = svc.create_token(principal)
        assert token.startswith("ckt_")
        result = svc.authenticate(token, AuthProvider.JWT)
        assert result is not None

    def test_authorize_allows(self):
        svc = SecurityService()
        policy = AuthorizationPolicy(
            name="admin_only",
            roles={"admin"},
            permissions={"delete"}
        )
        svc.add_policy(policy)
        principal = UserPrincipal(id="1", username="admin", roles={"admin"}, permissions={"delete"})
        assert svc.authorize(principal, "admin_only") is True

    def test_authorize_denies_wrong_role(self):
        svc = SecurityService()
        policy = AuthorizationPolicy(name="admin_only", roles={"admin"})
        svc.add_policy(policy)
        principal = UserPrincipal(id="1", username="user", roles={"user"})
        assert svc.authorize(principal, "admin_only") is False

    def test_authorize_denies_wrong_permission(self):
        svc = SecurityService()
        policy = AuthorizationPolicy(name="delete_only", permissions={"delete"})
        svc.add_policy(policy)
        principal = UserPrincipal(id="1", username="user", permissions={"read"})
        assert svc.authorize(principal, "delete_only") is False

    def test_authorize_deny_policy(self):
        svc = SecurityService()
        policy = AuthorizationPolicy(name="blocked", deny=True)
        svc.add_policy(policy)
        principal = UserPrincipal(id="1", username="any")
        assert svc.authorize(principal, "blocked") is False

    def test_authorize_missing_policy(self):
        svc = SecurityService()
        principal = UserPrincipal(id="1", username="any")
        assert svc.authorize(principal, "nonexistent") is True

    def test_authorize_all(self):
        svc = SecurityService()
        svc.add_policy(AuthorizationPolicy(name="p1", roles={"admin"}))
        svc.add_policy(AuthorizationPolicy(name="p2", roles={"user"}))
        principal = UserPrincipal(id="1", username="admin", roles={"admin"})
        results = svc.authorize_all(principal, ["p1", "p2"])
        assert results["p1"] is True
        assert results["p2"] is False

    def test_hash_and_verify_password(self):
        svc = SecurityService()
        hashed = svc.hash_password("mysecret")
        assert svc.verify_password("mysecret", hashed) is True
        assert svc.verify_password("wrong", hashed) is False

    def test_sign_and_verify(self):
        svc = SecurityService()
        sig = svc.sign("important data")
        assert svc.verify_signature("important data", sig) is True
        assert svc.verify_signature("tampered data", sig) is False
