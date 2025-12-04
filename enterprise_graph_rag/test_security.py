import pytest
from jose import jwt
from governance.auth.models import UserIdentity
from governance.policy.access_control import AccessControlPolicy

# 1. Test Auth Logic (Unit)
def test_token_generation():
    secret = "dev-secret"
    payload = {
        "sub": "user_123",
        "department": "hr",
        "roles": ["manager"]
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    print(f"\nGenerated Mock Token: {token[:20]}...")
    assert token is not None

# 2. Test RLS Policy Generation (Unit)
def test_rls_query_generation():
    user = UserIdentity(user_id="u1", email="a@b.com", department="sales")
    policy = AccessControlPolicy.get_rls_filters(user)
    
    assert "d.department = $user_dept" in policy['cypher']
    assert policy['params']['user_dept'] == "sales"
    print("\n✅ RLS Policy generated correctly for Sales user.")

# 3. Test Access Control Logic
def test_admin_access():
    admin = UserIdentity(user_id="u2", email="admin@b.com", roles=["admin"])
    policy = AccessControlPolicy.get_rls_filters(admin)
    assert policy['cypher'] == "1=1"
    print("✅ Admin gets full access.")

if __name__ == "__main__":
    test_token_generation()
    test_rls_query_generation()
    test_admin_access()