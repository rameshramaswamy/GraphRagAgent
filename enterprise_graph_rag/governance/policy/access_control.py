from typing import Dict, Any
from governance.auth.models import UserIdentity

class AccessControlPolicy:
    """
    Central Policy Engine.
    Determines what Cypher constraints apply to a given user.
    """

    @staticmethod
    def get_rls_filters(user: UserIdentity) -> Dict[str, Any]:
        """
        Returns a Cypher WHERE clause fragment and parameters.
        """
        # Admins see everything
        if "admin" in user.roles:
            return {"cypher": "1=1", "params": {}}

        # Logic:
        # A document is accessible IF:
        # 1. It has no 'department' property (Public)
        # 2. OR its 'department' matches the user's department
        # 3. OR the user is explicitly listed in 'allowed_users'
        
        cypher_clause = """
        (
            d.department IS NULL 
            OR d.department = $user_dept 
            OR $user_id IN d.allowed_users
        )
        """
        
        params = {
            "user_dept": user.department,
            "user_id": user.user_id
        }
        
        return {"cypher": cypher_clause, "params": params}