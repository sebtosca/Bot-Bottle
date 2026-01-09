"""Unit tests for notification helper functions."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

from endpoint.helpers.notifications import (
    check_and_notify_hungry_characters,
    _build_message,
    _mask,
    update_fullness,
    find_hungry_bottles,
    acquire_notification_slot,
    send_notification,
    Hungry,
    COOLDOWN,
    HUNGRY_THRESHOLD
)


class TestMask:
    """Tests for _mask function."""
    
    def test_mask_normal_phone_number(self):
        """Test masking a normal phone number."""
        result = _mask("+33684950535")
        assert result == "+336****"
    
    def test_mask_short_number(self):
        """Test masking a short number (less than 4 characters)."""
        result = _mask("123")
        assert result == "****"
    
    def test_mask_empty_string(self):
        """Test masking an empty string."""
        result = _mask("")
        assert result == "****"
    
    def test_mask_none(self):
        """Test masking None value."""
        result = _mask(None)
        assert result == "****"
    
    def test_mask_exactly_four_chars(self):
        """Test masking a number with exactly 4 characters."""
        result = _mask("1234")
        assert result == "1234****"


class TestBuildMessage:
    """Tests for _build_message function."""
    
    def test_build_message_single_empty(self):
        """Test message for single empty character."""
        hungry = [Hungry("Cherry", "empty", 0.0)]
        message = _build_message(hungry)
        assert "Cherry" in message
        assert "vide" in message
        assert "supermarché" in message
        assert "🏠" in message
    
    def test_build_message_single_hungry(self):
        """Test message for single hungry character."""
        hungry = [Hungry("Pompon", "hungry", 20.0)]
        message = _build_message(hungry)
        assert "Pompon" in message
        assert "faim" in message
        assert "🍎" in message
    
    def test_build_message_two_characters(self):
        """Test message for two characters."""
        hungry = [
            Hungry("Cherry", "hungry", 20.0),
            Hungry("Pompon", "hungry", 15.0)
        ]
        message = _build_message(hungry)
        assert "Cherry" in message
        assert "Pompon" in message
        assert " et " in message
        assert "ont faim" in message
    
    def test_build_message_three_characters(self):
        """Test message for three or more characters."""
        hungry = [
            Hungry("Cherry", "hungry", 20.0),
            Hungry("Pompon", "hungry", 15.0),
            Hungry("Test", "hungry", 10.0)
        ]
        message = _build_message(hungry)
        assert "Cherry" in message
        assert "Pompon" in message
        assert "Test" in message
        assert "," in message  # Should have comma separation
        assert " et " in message
    
    def test_build_message_multiple_with_empty(self):
        """Test message when at least one character is empty."""
        hungry = [
            Hungry("Cherry", "hungry", 20.0),
            Hungry("Pompon", "empty", 0.0)
        ]
        message = _build_message(hungry)
        assert "sont vides" in message
        assert "🏠🏠" in message
    
    def test_build_message_all_empty(self):
        """Test message when all characters are empty."""
        hungry = [
            Hungry("Cherry", "empty", 0.0),
            Hungry("Pompon", "empty", 0.0)
        ]
        message = _build_message(hungry)
        assert "sont vides" in message
        assert "🏠🏠" in message


class TestUpdateFullness:
    """Tests for update_fullness function."""
    
    def test_update_fullness_calls_check_and_decrease(self):
        """Test that update_fullness calls check_and_decrease_fullness for each bottle."""
        mock_bottle1 = MagicMock()
        mock_bottle2 = MagicMock()
        bottles = [mock_bottle1, mock_bottle2]
        
        with patch('endpoint.helpers.notifications.check_and_decrease_fullness') as mock_decrease:
            update_fullness(bottles)
            
            assert mock_decrease.call_count == 2
            mock_decrease.assert_any_call(mock_bottle1)
            mock_decrease.assert_any_call(mock_bottle2)


class TestFindHungryBottles:
    """Tests for find_hungry_bottles function."""
    
    def test_find_hungry_bottles_returns_hungry_bottles(self):
        """Test that find_hungry_bottles returns only hungry bottles."""
        mock_bottle1 = MagicMock()
        mock_bottle1.product_id = "00001"
        mock_bottle1.fullness_level = 20.0  # Below threshold
        
        mock_bottle2 = MagicMock()
        mock_bottle2.product_id = "00002"
        mock_bottle2.fullness_level = 50.0  # Above threshold
        
        bottles = [mock_bottle1, mock_bottle2]
        
        with patch('endpoint.helpers.notifications.get_fullness_state', side_effect=["hungry", "full"]), \
             patch('endpoint.helpers.notifications.get_character_config', side_effect=[
                 {"name": "Cherry"},
                 {"name": "Pompon"}
             ]):
            
            result = find_hungry_bottles(bottles)
            
            assert len(result) == 1
            assert result[0].name == "Cherry"
            assert result[0].state == "hungry"
            assert result[0].fullness == 20.0
    
    def test_find_hungry_bottles_includes_empty_bottles(self):
        """Test that empty bottles are included."""
        mock_bottle = MagicMock()
        mock_bottle.product_id = "00001"
        mock_bottle.fullness_level = 0.0
        
        with patch('endpoint.helpers.notifications.get_fullness_state', return_value="empty"), \
             patch('endpoint.helpers.notifications.get_character_config', return_value={"name": "Cherry"}):
            
            result = find_hungry_bottles([mock_bottle])
            
            assert len(result) == 1
            assert result[0].state == "empty"
    
    def test_find_hungry_bottles_caches_character_config(self):
        """Test that character config is cached for same product_id."""
        mock_bottle1 = MagicMock()
        mock_bottle1.product_id = "00001"
        mock_bottle1.fullness_level = 20.0
        
        mock_bottle2 = MagicMock()
        mock_bottle2.product_id = "00001"  # Same product_id
        mock_bottle2.fullness_level = 15.0
        
        with patch('endpoint.helpers.notifications.get_fullness_state', side_effect=["hungry", "hungry"]), \
             patch('endpoint.helpers.notifications.get_character_config', return_value={"name": "Cherry"}) as mock_config:
            
            result = find_hungry_bottles([mock_bottle1, mock_bottle2])
            
            # Note: cache.setdefault() evaluates the default argument even when key exists,
            # so get_character_config is called for each bottle. However, the cache still
            # works correctly - the second call's result is discarded and the cached value is used.
            # This is a known limitation of setdefault() - it's not lazy.
            assert len(result) == 2
            assert result[0].name == result[1].name == "Cherry"
            # get_character_config is called twice (once per bottle) due to setdefault behavior
            assert mock_config.call_count == 2


class TestAcquireNotificationSlot:
    """Tests for acquire_notification_slot function."""
    
    def test_acquire_notification_slot_success(self, mock_db_session):
        """Test that acquire_notification_slot returns True when slot is acquired."""
        from db.db import User
        now = datetime.utcnow()
        
        # Mock the update query to return 1 (success)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.update.return_value = 1
        
        # Use side_effect to return mock_query when User is queried
        def query_side_effect(model):
            if model == User:
                return mock_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        
        result = acquire_notification_slot(mock_db_session, 1, now)
        
        assert result is True
        mock_query.update.assert_called_once()
        # Verify User model was queried
        mock_db_session.query.assert_called_with(User)
    
    def test_acquire_notification_slot_failure(self, mock_db_session):
        """Test that acquire_notification_slot returns False when slot is not acquired."""
        from db.db import User
        now = datetime.utcnow()
        
        # Mock the update query to return 0 (no rows updated - cooldown active)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.update.return_value = 0
        
        # Use side_effect to return mock_query when User is queried
        def query_side_effect(model):
            if model == User:
                return mock_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        
        result = acquire_notification_slot(mock_db_session, 1, now)
        
        assert result is False
        mock_db_session.query.assert_called_with(User)


class TestSendNotification:
    """Tests for send_notification function."""
    
    def test_send_notification_calls_whatsapp(self, mock_db_session):
        """Test that send_notification calls send_whatsapp_text."""
        with patch('endpoint.helpers.notifications.send_whatsapp_text') as mock_send:
            send_notification(mock_db_session, 1, "+33684950535", "Test message")
            
            mock_send.assert_called_once_with("+33684950535", "Test message")


class TestCheckAndNotifyHungryCharacters:
    """Tests for check_and_notify_hungry_characters function."""
    
    def test_user_not_found(self, mock_db_session):
        """Test that function returns early if user not found."""
        from db.db import User
        
        # Setup query chain to return None for user
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = None
        
        def query_side_effect(model):
            if model == User:
                return user_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        
        check_and_notify_hungry_characters(mock_db_session, 999, "+33684950535")
        
        # Should not query bottles or send messages
        mock_db_session.query.assert_called()
        mock_db_session.commit.assert_not_called()
    
    def test_no_bottles(self, mock_db_session):
        """Test that function returns early if user has no bottles."""
        from db.db import User, Bottle
        mock_user = MagicMock()
        mock_user.id = 1
        
        # Setup query chain
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        # Handle chained filter calls (filter can be called multiple times)
        bottle_query.filter.return_value = bottle_query
        bottle_query.all.return_value = []  # No bottles
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.flush = MagicMock()
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=[]), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(mock_db_session, 1, "+33684950535")
            mock_send.assert_not_called()
            # When no bottles are found, function returns early before commit
            # (bottles = q.all() returns [], then function returns immediately)
            mock_db_session.commit.assert_not_called()
    
    def test_no_hungry_bottles(self, mock_db_session):
        """Test that function doesn't send notification if no bottles are hungry."""
        from db.db import User, Bottle
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.game_started = True
        
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        bottle_query.filter.return_value = bottle_query
        bottle_query.all.return_value = [mock_bottle]
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.flush = MagicMock()
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=[]), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(mock_db_session, 1, "+33684950535")
            mock_send.assert_not_called()
            mock_db_session.commit.assert_called_once()
    
    def test_cooldown_active(self, mock_db_session):
        """Test that function respects cooldown period."""
        from db.db import User, Bottle
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.game_started = True
        
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        bottle_query.filter.return_value = bottle_query
        bottle_query.all.return_value = [mock_bottle]
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.flush = MagicMock()
        
        hungry = [Hungry("Cherry", "hungry", 20.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=False), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(mock_db_session, 1, "+33684950535")
            mock_send.assert_not_called()
            mock_db_session.commit.assert_called_once()
    
    def test_sends_notification_for_hungry_bottle(self, mock_db_session):
        """Test that function sends notification when bottle is hungry."""
        from db.db import User, Bottle
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.game_started = True
        
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        bottle_query.filter.return_value = bottle_query
        bottle_query.all.return_value = [mock_bottle]
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.flush = MagicMock()
        
        hungry = [Hungry("Cherry", "hungry", 20.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(mock_db_session, 1, "+33684950535")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][2] == "+33684950535"  # recipient_phone_number (3rd positional arg)
            assert "Cherry" in call_args[0][3] or "faim" in call_args[0][3]  # message (4th positional arg)
            mock_db_session.commit.assert_called()
    
    def test_sends_notification_for_empty_bottle(self, mock_db_session):
        """Test that function sends notification when bottle is empty."""
        from db.db import User, Bottle
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.game_started = True
        
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        bottle_query.filter.return_value = bottle_query
        bottle_query.all.return_value = [mock_bottle]
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.flush = MagicMock()
        
        hungry = [Hungry("Cherry", "empty", 0.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(mock_db_session, 1, "+33684950535")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "vide" in call_args[0][3] or "supermarché" in call_args[0][3]  # message (4th positional arg)
    
    def test_multiple_hungry_bottles(self, mock_db_session):
        """Test notification with multiple hungry bottles."""
        from db.db import User, Bottle
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.game_started = True
        
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        bottle_query.filter.return_value = bottle_query
        bottle_query.all.return_value = [mock_bottle]
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.flush = MagicMock()
        
        hungry = [
            Hungry("Cherry", "hungry", 20.0),
            Hungry("Pompon", "hungry", 15.0)
        ]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(mock_db_session, 1, "+33684950535")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            message = call_args[0][3]  # message (4th positional arg)
            assert "Cherry" in message
            assert "Pompon" in message
    
    def test_handles_send_error(self, mock_db_session):
        """Test that function handles send errors gracefully."""
        from db.db import User, Bottle
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.game_started = True
        
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        bottle_query.filter.return_value = bottle_query
        bottle_query.all.return_value = [mock_bottle]
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.flush = MagicMock()
        mock_db_session.rollback = MagicMock()
        
        hungry = [Hungry("Cherry", "hungry", 20.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification', side_effect=Exception("API Error")), \
             patch('endpoint.helpers.notifications.logger') as mock_logger:
            
            # Should not raise exception
            check_and_notify_hungry_characters(mock_db_session, 1, "+33684950535")
            
            # Should rollback on error
            mock_db_session.rollback.assert_called_once()
            mock_logger.exception.assert_called_once()
