"""Unit tests for response type and sticker/GIF selection."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.state.bottle_state import (
    select_response_type,
    select_sticker_by_mood,
    select_gif_by_mood,
)


@pytest.mark.unit
class TestSelectResponseType:
    """Tests for select_response_type function."""
    
    def test_select_response_type_text_sticker_default(self, mock_db_session):
        """Test default response type selection (80% text_sticker)."""
        # Mock no recent responses
        mock_query = MagicMock()
        mock_query.all.return_value = []
        mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value = mock_query
        
        with patch('random.random', return_value=0.5):  # 50% - should be text_sticker
            result = select_response_type(
                mock_db_session,
                bottle_id=1,
                mood="happy",
                has_sticker=True,
                has_gif=True
            )
            assert result == "text_sticker"
    
    def test_select_response_type_gif_only(self, mock_db_session):
        """Test selecting gif_only response type."""
        # Mock no recent responses
        mock_query = MagicMock()
        mock_query.all.return_value = []
        mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value = mock_query
        
        with patch('random.random', return_value=0.9):  # 90% - should be gif_only
            result = select_response_type(
                mock_db_session,
                bottle_id=1,
                mood="happy",
                has_sticker=True,
                has_gif=True
            )
            assert result == "gif_only"
    
    def test_select_response_type_no_sticker(self, mock_db_session):
        """Test selecting response type when no sticker available."""
        mock_query = MagicMock()
        mock_query.all.return_value = []
        mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value = mock_query
        
        result = select_response_type(
            mock_db_session,
            bottle_id=1,
            mood="happy",
            has_sticker=False,
            has_gif=True
        )
        assert result == "gif_only"
    
    def test_select_response_type_no_gif(self, mock_db_session):
        """Test selecting response type when no GIF available."""
        mock_query = MagicMock()
        mock_query.all.return_value = []
        mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value = mock_query
        
        result = select_response_type(
            mock_db_session,
            bottle_id=1,
            mood="happy",
            has_sticker=True,
            has_gif=False
        )
        assert result == "text_sticker"
    
    def test_select_response_type_prevent_consecutive_gifs(self, mock_db_session):
        """Test that consecutive GIF responses are prevented."""
        # Mock last response was gif_only
        mock_query = MagicMock()
        mock_query.all.return_value = ["gif_only"]
        mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value = mock_query
        
        result = select_response_type(
            mock_db_session,
            bottle_id=1,
            mood="happy",
            has_sticker=True,
            has_gif=True
        )
        assert result == "text_sticker"  # Should force text_sticker


@pytest.mark.unit
class TestSelectStickerByMood:
    """Tests for select_sticker_by_mood function."""
    
    def test_select_sticker_by_mood_success(self, mock_db_session, sample_sticker):
        """Test selecting sticker by mood successfully."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_sticker]
        mock_db_session.query.return_value = mock_query
        
        result = select_sticker_by_mood(
            mock_db_session,
            mood="happy",
            base_url="http://localhost:5000",
            character_id="00001"
        )
        
        assert result is not None
        assert "url" in result
        assert "filename" in result
        assert result["filename"] == sample_sticker.filename
    
    def test_select_sticker_by_mood_no_session(self):
        """Test selecting sticker with no session."""
        result = select_sticker_by_mood(None, mood="happy")
        assert result is None
    
    def test_select_sticker_by_mood_no_match(self, mock_db_session):
        """Test selecting sticker when no match found."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        result = select_sticker_by_mood(
            mock_db_session,
            mood="nonexistent",
            character_id="00001"
        )
        
        assert result is None
    
    def test_select_sticker_by_mood_with_color(self, mock_db_session, sample_sticker):
        """Test selecting sticker with required color."""
        sample_sticker.mood_tags = "happy,green"
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_sticker]
        mock_db_session.query.return_value = mock_query
        
        result = select_sticker_by_mood(
            mock_db_session,
            mood="happy",
            base_url="http://localhost:5000",
            character_id="00001",
            required_color="GREEN"
        )
        
        assert result is not None


@pytest.mark.unit
class TestSelectGifByMood:
    """Tests for select_gif_by_mood function."""
    
    def test_select_gif_by_mood_success(self, mock_db_session, sample_gif):
        """Test selecting GIF by mood successfully."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_gif]
        mock_db_session.query.return_value = mock_query
        
        result = select_gif_by_mood(
            mock_db_session,
            mood="happy",
            base_url="http://localhost:5000",
            character_id="00001"
        )
        
        assert result is not None
        assert "url" in result
        assert "filename" in result
        assert result["media_type"] == "gif"
    
    def test_select_gif_by_mood_no_session(self):
        """Test selecting GIF with no session."""
        result = select_gif_by_mood(None, mood="happy")
        assert result is None
    
    def test_select_gif_by_mood_no_match(self, mock_db_session):
        """Test selecting GIF when no match found."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        result = select_gif_by_mood(
            mock_db_session,
            mood="nonexistent",
            character_id="00001"
        )
        
        assert result is None
    
    def test_select_gif_by_mood_exclude_description(self, mock_db_session, sample_gif):
        """Test selecting GIF excluding previous description."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_gif]
        mock_db_session.query.return_value = mock_query
        
        result = select_gif_by_mood(
            mock_db_session,
            mood="happy",
            base_url="http://localhost:5000",
            exclude_description="Different description",
            character_id="00001"
        )
        
        assert result is not None
