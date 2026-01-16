"""Interface Preferences Service - manages interface customization settings.

This service handles sensory-friendly interface customization including:
- Dark mode toggle
- Font size adjustment
- Contrast and spacing settings
- Persistence to user profile

Requirements: 8.2, 8.4
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning_profile import (
    LearningProfileORM,
    InterfacePreferences,
)
from src.models.enums import FontSize


class SpacingSettings(BaseModel):
    """Spacing customization settings."""
    
    line_height: float = Field(default=1.5, ge=1.0, le=3.0, description="Line height multiplier")
    paragraph_spacing: float = Field(default=1.0, ge=0.5, le=3.0, description="Paragraph spacing multiplier")
    element_spacing: float = Field(default=1.0, ge=0.5, le=2.0, description="Element spacing multiplier")


class InterfaceCustomization(BaseModel):
    """Complete interface customization settings.
    
    Extends InterfacePreferences with additional spacing settings.
    """
    
    # Core preferences (from InterfacePreferences)
    dark_mode: bool = False
    font_size: FontSize = FontSize.MEDIUM
    reduced_motion: bool = False
    high_contrast: bool = False
    
    # Extended spacing settings
    spacing: SpacingSettings = Field(default_factory=SpacingSettings)
    
    # Additional accessibility settings
    focus_indicators: bool = True  # Enhanced focus indicators for keyboard navigation
    simplified_layout: bool = False  # Reduce visual complexity
    
    def to_interface_preferences(self) -> InterfacePreferences:
        """Convert to base InterfacePreferences for storage."""
        return InterfacePreferences(
            dark_mode=self.dark_mode,
            font_size=self.font_size,
            reduced_motion=self.reduced_motion,
            high_contrast=self.high_contrast,
        )


class InterfacePreferencesUpdate(BaseModel):
    """Schema for updating interface preferences."""
    
    dark_mode: Optional[bool] = None
    font_size: Optional[FontSize] = None
    reduced_motion: Optional[bool] = None
    high_contrast: Optional[bool] = None
    spacing: Optional[SpacingSettings] = None
    focus_indicators: Optional[bool] = None
    simplified_layout: Optional[bool] = None


class InterfaceState(BaseModel):
    """Current interface state for a user session."""
    
    user_id: UUID
    customization: InterfaceCustomization
    last_updated: datetime
    
    # Computed CSS variables for frontend
    css_variables: dict[str, str] = Field(default_factory=dict)


class InterfacePreferencesService:
    """Service for managing interface customization settings.
    
    Provides methods to:
    - Toggle dark mode
    - Adjust font size
    - Configure contrast and spacing settings
    - Persist all changes to user profile
    
    Requirements: 8.2 (dark mode), 8.4 (interface customization)
    """
    
    # Font size to CSS value mapping
    FONT_SIZE_MAP = {
        FontSize.SMALL: "14px",
        FontSize.MEDIUM: "16px",
        FontSize.LARGE: "20px",
    }
    
    # Font size to scale factor mapping
    FONT_SCALE_MAP = {
        FontSize.SMALL: 0.875,
        FontSize.MEDIUM: 1.0,
        FontSize.LARGE: 1.25,
    }
    
    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session.
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        # In-memory cache for extended settings not stored in DB
        self._extended_settings: dict[str, dict] = {}
    
    async def get_interface_preferences(self, user_id: UUID) -> InterfaceCustomization:
        """Get the current interface customization settings for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            InterfaceCustomization with all settings
            
        Requirements: 8.4 - Retrieve customization settings
        """
        result = await self.db.execute(
            select(LearningProfileORM).where(
                LearningProfileORM.user_id == str(user_id)
            )
        )
        profile_orm = result.scalar_one_or_none()
        
        if not profile_orm:
            # Return defaults if no profile exists
            return InterfaceCustomization()
        
        # Get base preferences from profile
        base_prefs = InterfacePreferences(**profile_orm.interface_preferences)
        
        # Get extended settings from cache
        extended = self._extended_settings.get(str(user_id), {})
        
        return InterfaceCustomization(
            dark_mode=base_prefs.dark_mode,
            font_size=base_prefs.font_size,
            reduced_motion=base_prefs.reduced_motion,
            high_contrast=base_prefs.high_contrast,
            spacing=SpacingSettings(**extended.get("spacing", {})) if extended.get("spacing") else SpacingSettings(),
            focus_indicators=extended.get("focus_indicators", True),
            simplified_layout=extended.get("simplified_layout", False),
        )
    
    async def toggle_dark_mode(self, user_id: UUID) -> InterfaceCustomization:
        """Toggle dark mode on/off for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.2 - Dark mode option
        """
        current = await self.get_interface_preferences(user_id)
        return await self.update_interface_preferences(
            user_id,
            InterfacePreferencesUpdate(dark_mode=not current.dark_mode)
        )
    
    async def set_dark_mode(self, user_id: UUID, enabled: bool) -> InterfaceCustomization:
        """Set dark mode to a specific value.
        
        Args:
            user_id: The user's ID
            enabled: Whether dark mode should be enabled
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.2 - Dark mode option
        """
        return await self.update_interface_preferences(
            user_id,
            InterfacePreferencesUpdate(dark_mode=enabled)
        )
    
    async def set_font_size(self, user_id: UUID, size: FontSize) -> InterfaceCustomization:
        """Set the font size preference.
        
        Args:
            user_id: The user's ID
            size: The desired font size (SMALL, MEDIUM, LARGE)
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.4 - Font size customization
        """
        return await self.update_interface_preferences(
            user_id,
            InterfacePreferencesUpdate(font_size=size)
        )
    
    async def increase_font_size(self, user_id: UUID) -> InterfaceCustomization:
        """Increase font size by one step.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.4 - Font size adjustment
        """
        current = await self.get_interface_preferences(user_id)
        size_order = [FontSize.SMALL, FontSize.MEDIUM, FontSize.LARGE]
        current_index = size_order.index(current.font_size)
        
        if current_index < len(size_order) - 1:
            new_size = size_order[current_index + 1]
            return await self.set_font_size(user_id, new_size)
        
        return current  # Already at maximum
    
    async def decrease_font_size(self, user_id: UUID) -> InterfaceCustomization:
        """Decrease font size by one step.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.4 - Font size adjustment
        """
        current = await self.get_interface_preferences(user_id)
        size_order = [FontSize.SMALL, FontSize.MEDIUM, FontSize.LARGE]
        current_index = size_order.index(current.font_size)
        
        if current_index > 0:
            new_size = size_order[current_index - 1]
            return await self.set_font_size(user_id, new_size)
        
        return current  # Already at minimum
    
    async def set_high_contrast(self, user_id: UUID, enabled: bool) -> InterfaceCustomization:
        """Set high contrast mode.
        
        Args:
            user_id: The user's ID
            enabled: Whether high contrast should be enabled
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.4 - Contrast customization
        """
        return await self.update_interface_preferences(
            user_id,
            InterfacePreferencesUpdate(high_contrast=enabled)
        )
    
    async def set_spacing(self, user_id: UUID, spacing: SpacingSettings) -> InterfaceCustomization:
        """Set spacing preferences.
        
        Args:
            user_id: The user's ID
            spacing: The spacing settings to apply
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.4 - Spacing customization
        """
        return await self.update_interface_preferences(
            user_id,
            InterfacePreferencesUpdate(spacing=spacing)
        )
    
    async def set_reduced_motion(self, user_id: UUID, enabled: bool) -> InterfaceCustomization:
        """Set reduced motion preference.
        
        Args:
            user_id: The user's ID
            enabled: Whether reduced motion should be enabled
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.3 (implied) - Avoid sudden animations
        """
        return await self.update_interface_preferences(
            user_id,
            InterfacePreferencesUpdate(reduced_motion=enabled)
        )
    
    async def update_interface_preferences(
        self, 
        user_id: UUID, 
        updates: InterfacePreferencesUpdate
    ) -> InterfaceCustomization:
        """Update interface preferences with partial updates.
        
        Args:
            user_id: The user's ID
            updates: The updates to apply
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.4 - Interface customization persistence
        """
        result = await self.db.execute(
            select(LearningProfileORM).where(
                LearningProfileORM.user_id == str(user_id)
            )
        )
        profile_orm = result.scalar_one_or_none()
        
        if not profile_orm:
            raise ValueError(f"No profile found for user {user_id}")
        
        # Get current preferences
        current_prefs = dict(profile_orm.interface_preferences)
        
        # Apply updates to base preferences
        if updates.dark_mode is not None:
            current_prefs["dark_mode"] = updates.dark_mode
        if updates.font_size is not None:
            current_prefs["font_size"] = updates.font_size.value
        if updates.reduced_motion is not None:
            current_prefs["reduced_motion"] = updates.reduced_motion
        if updates.high_contrast is not None:
            current_prefs["high_contrast"] = updates.high_contrast
        
        # Update profile in database
        profile_orm.interface_preferences = current_prefs
        profile_orm.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(profile_orm)
        
        # Handle extended settings in memory cache
        user_key = str(user_id)
        if user_key not in self._extended_settings:
            self._extended_settings[user_key] = {}
        
        if updates.spacing is not None:
            self._extended_settings[user_key]["spacing"] = updates.spacing.model_dump()
        if updates.focus_indicators is not None:
            self._extended_settings[user_key]["focus_indicators"] = updates.focus_indicators
        if updates.simplified_layout is not None:
            self._extended_settings[user_key]["simplified_layout"] = updates.simplified_layout
        
        return await self.get_interface_preferences(user_id)
    
    async def get_interface_state(self, user_id: UUID) -> InterfaceState:
        """Get the complete interface state including computed CSS variables.
        
        Args:
            user_id: The user's ID
            
        Returns:
            InterfaceState with customization and CSS variables
            
        Requirements: 8.4 - Interface customization application
        """
        customization = await self.get_interface_preferences(user_id)
        css_variables = self._compute_css_variables(customization)
        
        return InterfaceState(
            user_id=user_id,
            customization=customization,
            last_updated=datetime.utcnow(),
            css_variables=css_variables,
        )
    
    def _compute_css_variables(self, customization: InterfaceCustomization) -> dict[str, str]:
        """Compute CSS variables from customization settings.
        
        Args:
            customization: The interface customization settings
            
        Returns:
            Dictionary of CSS variable names to values
        """
        variables = {}
        
        # Font size
        variables["--font-size-base"] = self.FONT_SIZE_MAP[customization.font_size]
        variables["--font-scale"] = str(self.FONT_SCALE_MAP[customization.font_size])
        
        # Spacing
        variables["--line-height"] = str(customization.spacing.line_height)
        variables["--paragraph-spacing"] = f"{customization.spacing.paragraph_spacing}em"
        variables["--element-spacing"] = f"{customization.spacing.element_spacing}rem"
        
        # Colors based on dark mode and contrast
        if customization.dark_mode:
            if customization.high_contrast:
                variables["--bg-color"] = "#000000"
                variables["--text-color"] = "#ffffff"
                variables["--accent-color"] = "#00ffff"
                variables["--border-color"] = "#ffffff"
            else:
                variables["--bg-color"] = "#1a1a2e"
                variables["--text-color"] = "#e8e8e8"
                variables["--accent-color"] = "#7b68ee"
                variables["--border-color"] = "#3a3a5e"
        else:
            if customization.high_contrast:
                variables["--bg-color"] = "#ffffff"
                variables["--text-color"] = "#000000"
                variables["--accent-color"] = "#0000ff"
                variables["--border-color"] = "#000000"
            else:
                variables["--bg-color"] = "#f5f5f5"
                variables["--text-color"] = "#333333"
                variables["--accent-color"] = "#6b5b95"
                variables["--border-color"] = "#cccccc"
        
        # Motion
        if customization.reduced_motion:
            variables["--transition-duration"] = "0ms"
            variables["--animation-duration"] = "0ms"
        else:
            variables["--transition-duration"] = "200ms"
            variables["--animation-duration"] = "300ms"
        
        # Focus indicators
        if customization.focus_indicators:
            variables["--focus-outline"] = "3px solid var(--accent-color)"
            variables["--focus-outline-offset"] = "2px"
        else:
            variables["--focus-outline"] = "1px solid var(--accent-color)"
            variables["--focus-outline-offset"] = "0px"
        
        return variables
    
    async def reset_to_defaults(self, user_id: UUID) -> InterfaceCustomization:
        """Reset all interface preferences to defaults.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Default InterfaceCustomization
            
        Requirements: 8.4 - Interface customization
        """
        default = InterfaceCustomization()
        
        result = await self.db.execute(
            select(LearningProfileORM).where(
                LearningProfileORM.user_id == str(user_id)
            )
        )
        profile_orm = result.scalar_one_or_none()
        
        if profile_orm:
            profile_orm.interface_preferences = default.to_interface_preferences().model_dump()
            profile_orm.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(profile_orm)
        
        # Clear extended settings
        user_key = str(user_id)
        if user_key in self._extended_settings:
            del self._extended_settings[user_key]
        
        return default
    
    async def apply_preset(self, user_id: UUID, preset_name: str) -> InterfaceCustomization:
        """Apply a predefined accessibility preset.
        
        Available presets:
        - "default": Standard settings
        - "high_visibility": High contrast, large font
        - "calm": Dark mode, reduced motion, muted colors
        - "focus": Simplified layout, enhanced focus indicators
        
        Args:
            user_id: The user's ID
            preset_name: Name of the preset to apply
            
        Returns:
            Updated InterfaceCustomization
            
        Requirements: 8.4 - Interface customization
        """
        presets = {
            "default": InterfacePreferencesUpdate(
                dark_mode=False,
                font_size=FontSize.MEDIUM,
                high_contrast=False,
                reduced_motion=False,
                spacing=SpacingSettings(),
                focus_indicators=True,
                simplified_layout=False,
            ),
            "high_visibility": InterfacePreferencesUpdate(
                dark_mode=False,
                font_size=FontSize.LARGE,
                high_contrast=True,
                reduced_motion=False,
                spacing=SpacingSettings(line_height=1.8, paragraph_spacing=1.5),
                focus_indicators=True,
                simplified_layout=False,
            ),
            "calm": InterfacePreferencesUpdate(
                dark_mode=True,
                font_size=FontSize.MEDIUM,
                high_contrast=False,
                reduced_motion=True,
                spacing=SpacingSettings(line_height=1.6, element_spacing=1.2),
                focus_indicators=True,
                simplified_layout=False,
            ),
            "focus": InterfacePreferencesUpdate(
                dark_mode=False,
                font_size=FontSize.MEDIUM,
                high_contrast=False,
                reduced_motion=True,
                spacing=SpacingSettings(line_height=1.5, element_spacing=1.3),
                focus_indicators=True,
                simplified_layout=True,
            ),
        }
        
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(presets.keys())}")
        
        return await self.update_interface_preferences(user_id, presets[preset_name])
