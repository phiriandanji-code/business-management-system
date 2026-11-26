from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import BusinessMembership, User


def require_business_role(*allowed_roles: str):

    permitted_roles = {
        role.lower() for role in allowed_roles
    }

    def check_business_access(
        business_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):

        membership = db.query(BusinessMembership).filter(
            BusinessMembership.user_id == current_user.id,
            BusinessMembership.business_id == business_id,
            BusinessMembership.is_active == True
        ).first()

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this business."
            )

        if membership.role.lower() not in permitted_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action."
            )

        return membership

    return check_business_access