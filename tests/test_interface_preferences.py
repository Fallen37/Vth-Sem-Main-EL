"""Unit tests for InterfacePreferencesService."""

import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.user import UserORM
from src.models.learning_profile import LearningProfileORM, InterfacePreferences
from src.models.enums import UserRole, Syllabus, FontSize
from src.services.interface_preferences import (
    InterfacePreferencesService,
    InterfaceCustomization,
    InterfacePreferencesUpdate,
    SpacingSettings,
)


@pytest.fixture
async def async_session():
    """Create an async session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user with a learning profile."""
    user_id = str(uuid4())
    user = UserORM(
        id=user_id,
        email="test@example.com",
        name="Test User",
        role=UserRole.STUDENT.value,
        grade=8,
        syllabus=Syllabus.CBSE.value,
    )
    async_session.add(user)
    
    profile = LearningProfileORM(
        id=str(uuid4()),
        user_id=user_id,
        interface_preferences=InterfacePreferences().model_dump(),
    )
    async_session.add(profile)
    
    await async_session.commit()
    return user


class TestInterfacePreferencesService:
    """Tests for InterfacePreferencesService."""
    
    @pytest.mark.asyncio
    async def test_get_interface_preferences_default(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test getting default interface preferences."""
        service = InterfacePreferencesService(async_session)
        prefs = await service.get_interface_preferences(uuid4())
        
        # Should return defaults for non-existent user
        assert prefs.dark_mode is False
        assert prefs.font_size == FontSize.MEDIUM
        assert prefs.high_contrast is False
        assert prefs.reduced_motion is False
    
    @pytest.mark.asyncio
    async def test_get_interface_preferences_existing_user(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test getting interface preferences for existing user."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        prefs = await service.get_interface_preferences(UUID(test_user.id))
        
        assert isinstance(prefs, InterfaceCustomization)
        assert prefs.dark_mode is False
        assert prefs.font_size == FontSize.MEDIUM
    
    @pytest.mark.asyncio
    async def test_toggle_dark_mode(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test toggling dark mode."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        # Initially dark mode is off
        prefs = await service.get_interface_preferences(user_id)
        assert prefs.dark_mode is False
        
        # Toggle on
        prefs = await service.toggle_dark_mode(user_id)
        assert prefs.dark_mode is True
        
        # Toggle off
        prefs = await service.toggle_dark_mode(user_id)
        assert prefs.dark_mode is False
    
    @pytest.mark.asyncio
    async def test_set_dark_mode(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test setting dark mode explicitly."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        prefs = await service.set_dark_mode(user_id, True)
        assert prefs.dark_mode is True
        
        prefs = await service.set_dark_mode(user_id, False)
        assert prefs.dark_mode is False
    
    @pytest.mark.asyncio
    async def test_set_font_size(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test setting font size."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        prefs = await service.set_font_size(user_id, FontSize.LARGE)
        assert prefs.font_size == FontSize.LARGE
        
        prefs = await service.set_font_size(user_id, FontSize.SMALL)
        assert prefs.font_size == FontSize.SMALL
    
    @pytest.mark.asyncio
    async def test_increase_font_size(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test increasing font size step by step."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        # Start at medium
        prefs = await service.get_interface_preferences(user_id)
        assert prefs.font_size == FontSize.MEDIUM
        
        # Increase to large
        prefs = await service.increase_font_size(user_id)
        assert prefs.font_size == FontSize.LARGE
        
        # Try to increase beyond max - should stay at large
        prefs = await service.increase_font_size(user_id)
        assert prefs.font_size == FontSize.LARGE
    
    @pytest.mark.asyncio
    async def test_decrease_font_size(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test decreasing font size step by step."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        # Start at medium
        prefs = await service.get_interface_preferences(user_id)
        assert prefs.font_size == FontSize.MEDIUM
        
        # Decrease to small
        prefs = await service.decrease_font_size(user_id)
        assert prefs.font_size == FontSize.SMALL
        
        # Try to decrease beyond min - should stay at small
        prefs = await service.decrease_font_size(user_id)
        assert prefs.font_size == FontSize.SMALL
    
    @pytest.mark.asyncio
    async def test_set_high_contrast(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test setting high contrast mode."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        prefs = await service.set_high_contrast(user_id, True)
        assert prefs.high_contrast is True
        
        prefs = await service.set_high_contrast(user_id, False)
        assert prefs.high_contrast is False
    
    @pytest.mark.asyncio
    async def test_set_spacing(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test setting spacing preferences."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        spacing = SpacingSettings(
            line_height=2.0,
            paragraph_spacing=1.5,
            element_spacing=1.5,
        )
        
        prefs = await service.set_spacing(user_id, spacing)
        assert prefs.spacing.line_height == 2.0
        assert prefs.spacing.paragraph_spacing == 1.5
        assert prefs.spacing.element_spacing == 1.5
    
    @pytest.mark.asyncio
    async def test_set_reduced_motion(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test setting reduced motion preference."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        prefs = await service.set_reduced_motion(user_id, True)
        assert prefs.reduced_motion is True
        
        prefs = await service.set_reduced_motion(user_id, False)
        assert prefs.reduced_motion is False
    
    @pytest.mark.asyncio
    async def test_get_interface_state(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test getting complete interface state with CSS variables."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        state = await service.get_interface_state(user_id)
        
        assert state.user_id == user_id
        assert isinstance(state.customization, InterfaceCustomization)
        assert "--font-size-base" in state.css_variables
        assert "--bg-color" in state.css_variables
        assert "--text-color" in state.css_variables
    
    @pytest.mark.asyncio
    async def test_css_variables_dark_mode(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test CSS variables change with dark mode."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        # Light mode
        state = await service.get_interface_state(user_id)
        light_bg = state.css_variables["--bg-color"]
        
        # Enable dark mode
        await service.set_dark_mode(user_id, True)
        state = await service.get_interface_state(user_id)
        dark_bg = state.css_variables["--bg-color"]
        
        assert light_bg != dark_bg
    
    @pytest.mark.asyncio
    async def test_reset_to_defaults(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test resetting preferences to defaults."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        # Change some settings
        await service.set_dark_mode(user_id, True)
        await service.set_font_size(user_id, FontSize.LARGE)
        await service.set_high_contrast(user_id, True)
        
        # Reset
        prefs = await service.reset_to_defaults(user_id)
        
        assert prefs.dark_mode is False
        assert prefs.font_size == FontSize.MEDIUM
        assert prefs.high_contrast is False
    
    @pytest.mark.asyncio
    async def test_apply_preset_calm(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test applying the 'calm' preset."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        prefs = await service.apply_preset(user_id, "calm")
        
        assert prefs.dark_mode is True
        assert prefs.reduced_motion is True
    
    @pytest.mark.asyncio
    async def test_apply_preset_high_visibility(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test applying the 'high_visibility' preset."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        prefs = await service.apply_preset(user_id, "high_visibility")
        
        assert prefs.font_size == FontSize.LARGE
        assert prefs.high_contrast is True
    
    @pytest.mark.asyncio
    async def test_apply_preset_invalid(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test applying an invalid preset raises error."""
        service = InterfacePreferencesService(async_session)
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        with pytest.raises(ValueError, match="Unknown preset"):
            await service.apply_preset(user_id, "invalid_preset")
    
    @pytest.mark.asyncio
    async def test_persistence_across_sessions(
        self, async_session: AsyncSession, test_user: UserORM
    ):
        """Test that preferences persist to the database."""
        from uuid import UUID
        user_id = UUID(test_user.id)
        
        # First service instance
        service1 = InterfacePreferencesService(async_session)
        await service1.set_dark_mode(user_id, True)
        await service1.set_font_size(user_id, FontSize.LARGE)
        
        # Second service instance (simulating new request)
        service2 = InterfacePreferencesService(async_session)
        prefs = await service2.get_interface_preferences(user_id)
        
        assert prefs.dark_mode is True
        assert prefs.font_size == FontSize.LARGE
