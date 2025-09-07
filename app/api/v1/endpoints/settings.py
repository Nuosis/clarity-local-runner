"""
System settings management endpoints.
"""

from typing import List, Optional

from auth.dependencies import get_current_user, require_admin
from database.session import db_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.system import SystemSetting
from models.user import User
from pydantic import BaseModel
from schemas.common import APIResponse
from sqlalchemy.orm import Session

router = APIRouter()


class SystemSettingResponse(BaseModel):
    """System setting information."""

    id: int
    setting_key: str
    setting_value: Optional[str]
    setting_type: str
    description: Optional[str]
    is_public: bool
    category: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SystemSettingCreate(BaseModel):
    """Schema for creating system settings."""

    setting_key: str
    setting_value: Optional[str] = None
    setting_type: str = "string"
    description: Optional[str] = None
    is_public: bool = False
    category: str = "general"


class SystemSettingUpdate(BaseModel):
    """Schema for updating system settings."""

    setting_value: Optional[str] = None
    description: Optional[str] = None


@router.get("", response_model=APIResponse[List[SystemSettingResponse]])
async def get_system_settings(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_public: Optional[bool] = Query(None, description="Filter by public visibility"),
):
    """
    Get system settings.

    Access: ADMIN (all), PUBLIC (public settings only)
    """
    try:
        query = db.query(SystemSetting)

        # Non-admin users can only see public settings
        if current_user.role != "admin":
            query = query.filter(SystemSetting.is_public == True)
        elif is_public is not None:
            query = query.filter(SystemSetting.is_public == is_public)

        if category:
            query = query.filter(SystemSetting.category == category)

        settings = query.order_by(
            SystemSetting.category, SystemSetting.setting_key
        ).all()

        # Convert to response format
        settings_data = []
        for setting in settings:
            setting_data = SystemSettingResponse(
                id=setting.id,
                setting_key=setting.setting_key,
                setting_value=setting.setting_value,
                setting_type=setting.setting_type,
                description=setting.description,
                is_public=setting.is_public,
                category=setting.category,
                created_at=str(setting.created_at),
                updated_at=str(setting.updated_at),
            )
            settings_data.append(setting_data)

        return APIResponse(
            success=True,
            data=settings_data,
            message="System settings retrieved successfully",
        )

    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to retrieve system settings: {str(e)}",
        )


@router.put("/{setting_id}", response_model=APIResponse[SystemSettingResponse])
async def update_system_setting(
    setting_id: int,
    setting_update: SystemSettingUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
):
    """
    Update system setting.

    Access: ADMIN only
    """
    try:
        # Get the setting
        setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="System setting not found"
            )

        # Update fields
        if setting_update.setting_value is not None:
            setting.setting_value = setting_update.setting_value

        if setting_update.description is not None:
            setting.description = setting_update.description

        db.commit()
        db.refresh(setting)

        # Convert to response format
        setting_data = SystemSettingResponse(
            id=setting.id,
            setting_key=setting.setting_key,
            setting_value=setting.setting_value,
            setting_type=setting.setting_type,
            description=setting.description,
            is_public=setting.is_public,
            category=setting.category,
            created_at=str(setting.created_at),
            updated_at=str(setting.updated_at),
        )

        return APIResponse(
            success=True,
            data=setting_data,
            message="System setting updated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to update system setting: {str(e)}",
        )


@router.delete("/{setting_id}", response_model=APIResponse[dict])
async def delete_system_setting(
    setting_id: int,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
):
    """
    Delete a system setting.

    Access: ADMIN only
    """
    try:
        # Get the setting
        setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="System setting not found"
            )

        # Store setting key for response
        setting_key = setting.setting_key

        # Delete the setting
        db.delete(setting)
        db.commit()

        return APIResponse(
            success=True,
            data={"id": setting_id, "setting_key": setting_key, "deleted": True},
            message="System setting deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to delete system setting: {str(e)}",
        )
