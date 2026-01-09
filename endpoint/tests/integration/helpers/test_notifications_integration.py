"""Integration tests for notification helper functions."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

from endpoint.helpers.notifications import (
    check_and_notify_hungry_characters,
    update_fullness,
    find_hungry_bottles,
    acquire_notification_slot,
    send_notification,
    Hungry,
    COOLDOWN,
    HUNGRY_THRESHOLD
)
from db.db import User, Bottle


class TestNotificationsIntegration:
    """Integration tests for notification system."""
    
    @pytest.fixture
    def real_db_session(self):
        """Create a more realistic database session mock."""
        session = MagicMock()
        
        # Setup query chain for User
        user_query = MagicMock()
        user_filter = MagicMock()
        user_query.filter.return_value = user_filter
        user_filter.one_or_none.return_value = None
        
        # Setup query chain for Bottle
        bottle_query = MagicMock()
        bottle_filter = MagicMock()
        bottle_query.filter.return_value = bottle_filter
        bottle_filter.all.return_value = []
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        session.query.side_effect = query_side_effect
        session.commit = MagicMock()
        session.add = MagicMock()
        session.flush = MagicMock()
        session.rollback = MagicMock()
        
        return session
    
    def _setup_bottle_query_chain(self, bottle_query, bottles_list):
        """Helper to set up bottle query chain that supports chained filters.
        
        The code does: q.filter(...).filter(...).all(), so we need:
        - bottle_query.filter() returns a query object
        - That query object's .filter() returns itself (for chaining)
        - That query object's .all() returns the bottles list
        """
        filtered_query = MagicMock()
        filtered_query.filter.return_value = filtered_query  # Support chained filter
        filtered_query.all.return_value = bottles_list
        bottle_query.filter.return_value = filtered_query
        return filtered_query
    
    def test_full_notification_flow_single_hungry_bottle(self, real_db_session):
        """Test complete notification flow with one hungry bottle."""
        # Setup user
        mock_user = MagicMock()
        mock_user.id = 1
        
        # Setup bottle
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.product_id = "00001"
        mock_bottle.game_started = True
        mock_bottle.returned = False
        mock_bottle.fullness_level = 25.0  # Below threshold
        
        # Mock acquire_notification_slot to return True (slot acquired)
        update_query = MagicMock()
        update_query.filter.return_value = update_query
        update_query.update.return_value = 1
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        # Setup bottle query chain: query -> filter -> filter -> all()
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [mock_bottle])
        
        call_count = {'user': 0}
        def query_side_effect(model):
            if model == User:
                call_count['user'] += 1
                # First call is for user lookup, second is for acquire_notification_slot
                if call_count['user'] == 2:
                    return update_query
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        hungry = [Hungry("Cherry", "hungry", 25.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness') as mock_update, \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Verify fullness was updated with the actual list of bottles
            mock_update.assert_called_once()
            # The call should be with the list returned by q.all()
            call_args = mock_update.call_args
            assert len(call_args[0]) == 1  # One positional argument
            assert call_args[0][0] == [mock_bottle]  # The argument is the list
            
            # Verify notification was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][1] == 1  # user_id (2nd positional arg)
            assert call_args[0][2] == "+33684950535"  # recipient_phone_number (3rd positional arg)
            assert "Cherry" in call_args[0][3]  # message (4th positional arg)
            
            # Verify database was committed
            real_db_session.commit.assert_called()
            real_db_session.flush.assert_called_once()
    
    def test_full_notification_flow_multiple_bottles(self, real_db_session):
        """Test complete notification flow with multiple hungry bottles."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle1 = MagicMock()
        mock_bottle1.user_id = 1
        mock_bottle1.product_id = "00001"
        mock_bottle1.game_started = True
        mock_bottle1.returned = False
        mock_bottle1.fullness_level = 20.0
        
        mock_bottle2 = MagicMock()
        mock_bottle2.user_id = 1
        mock_bottle2.product_id = "00002"
        mock_bottle2.game_started = True
        mock_bottle2.returned = False
        mock_bottle2.fullness_level = 15.0
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [mock_bottle1, mock_bottle2])
        
        update_query = MagicMock()
        update_query.filter.return_value = update_query
        update_query.update.return_value = 1
        
        call_count = {'user': 0}
        def query_side_effect(model):
            if model == User:
                call_count['user'] += 1
                if call_count['user'] == 2:
                    return update_query
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        hungry = [
            Hungry("Cherry", "hungry", 20.0),
            Hungry("Pompon", "hungry", 15.0)
        ]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Verify notification includes both characters
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            message = call_args[0][3]  # message (4th positional arg)
            assert "Cherry" in message
            assert "Pompon" in message
            assert " et " in message or "," in message
    
    def test_notification_cooldown_integration(self, real_db_session):
        """Test that cooldown mechanism works in full flow."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.product_id = "00001"
        mock_bottle.game_started = True
        mock_bottle.returned = False
        mock_bottle.fullness_level = 20.0
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [mock_bottle])
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        hungry = [Hungry("Cherry", "hungry", 20.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=False), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Should not send notification due to cooldown
            mock_send.assert_not_called()
            real_db_session.commit.assert_called_once()  # Should commit after flush
    
    def test_notification_after_cooldown_expires(self, real_db_session):
        """Test that notification is sent after cooldown expires."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.product_id = "00001"
        mock_bottle.game_started = True
        mock_bottle.returned = False
        mock_bottle.fullness_level = 20.0
        
        user_query = real_db_session.query(User)
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = real_db_session.query(Bottle)
        self._setup_bottle_query_chain(bottle_query, [mock_bottle])
        
        hungry = [Hungry("Cherry", "hungry", 20.0)]
        
        update_query = MagicMock()
        update_query.filter.return_value = update_query
        update_query.update.return_value = 1
        
        call_count = {'user': 0}
        def query_side_effect(model):
            if model == User:
                call_count['user'] += 1
                if call_count['user'] == 2:
                    return update_query
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Should send notification after cooldown expired
            mock_send.assert_called_once()
            real_db_session.commit.assert_called()
    
    def test_mixed_bottle_states(self, real_db_session):
        """Test notification with mix of hungry and full bottles."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        # Hungry bottle
        mock_bottle1 = MagicMock()
        mock_bottle1.user_id = 1
        mock_bottle1.product_id = "00001"
        mock_bottle1.game_started = True
        mock_bottle1.returned = False
        mock_bottle1.fullness_level = 20.0
        
        # Full bottle (should be filtered out by find_hungry_bottles)
        mock_bottle2 = MagicMock()
        mock_bottle2.user_id = 1
        mock_bottle2.product_id = "00002"
        mock_bottle2.game_started = True
        mock_bottle2.returned = False
        mock_bottle2.fullness_level = 50.0
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [mock_bottle1, mock_bottle2])
        
        update_query = MagicMock()
        update_query.filter.return_value = update_query
        update_query.update.return_value = 1
        
        call_count = {'user': 0}
        def query_side_effect(model):
            if model == User:
                call_count['user'] += 1
                if call_count['user'] == 2:
                    return update_query
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        # Only hungry bottle should be in the result
        hungry = [Hungry("Cherry", "hungry", 20.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Should only send notification for hungry bottle
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            message = call_args[0][3]  # message (4th positional arg)
            assert "Cherry" in message
    
    def test_empty_bottle_notification(self, real_db_session):
        """Test notification for empty bottle."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.product_id = "00001"
        mock_bottle.game_started = True
        mock_bottle.returned = False
        mock_bottle.fullness_level = 0.0
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [mock_bottle])
        
        update_query = MagicMock()
        update_query.filter.return_value = update_query
        update_query.update.return_value = 1
        
        call_count = {'user': 0}
        def query_side_effect(model):
            if model == User:
                call_count['user'] += 1
                if call_count['user'] == 2:
                    return update_query
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        hungry = [Hungry("Cherry", "empty", 0.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            message = call_args[0][3]  # message (4th positional arg)
            assert "vide" in message
            assert "supermarché" in message
    
    def test_returned_bottles_excluded(self, real_db_session):
        """Test that returned bottles are excluded from notifications."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        # Query should filter out returned bottles
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [])  # No bottles after filtering
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=[]), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Should not send notification for returned bottles
            mock_send.assert_not_called()
    
    def test_whatsapp_error_handling(self, real_db_session):
        """Test that WhatsApp errors are handled gracefully."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_bottle = MagicMock()
        mock_bottle.user_id = 1
        mock_bottle.product_id = "00001"
        mock_bottle.game_started = True
        mock_bottle.returned = False
        mock_bottle.fullness_level = 20.0
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [mock_bottle])
        
        update_query = MagicMock()
        update_query.filter.return_value = update_query
        update_query.update.return_value = 1
        
        call_count = {'user': 0}
        def query_side_effect(model):
            if model == User:
                call_count['user'] += 1
                if call_count['user'] == 2:
                    return update_query
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        hungry = [Hungry("Cherry", "hungry", 20.0)]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry), \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification', side_effect=Exception("API Error")), \
             patch('endpoint.helpers.notifications.logger') as mock_logger:
            
            # Should not raise exception
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Should log the error
            mock_logger.exception.assert_called_once()
            
            # Should rollback on error
            real_db_session.rollback.assert_called_once()
    
    def test_character_config_caching_integration(self, real_db_session):
        """Test that character config caching works correctly."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        # Two bottles with same product_id
        mock_bottle1 = MagicMock()
        mock_bottle1.user_id = 1
        mock_bottle1.product_id = "00001"
        mock_bottle1.game_started = True
        mock_bottle1.returned = False
        mock_bottle1.fullness_level = 20.0
        
        mock_bottle2 = MagicMock()
        mock_bottle2.user_id = 1
        mock_bottle2.product_id = "00001"  # Same product_id
        mock_bottle2.game_started = True
        mock_bottle2.returned = False
        mock_bottle2.fullness_level = 15.0
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        # Setup bottle query chain: query -> filter -> filter -> all()
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [mock_bottle1, mock_bottle2])
        
        update_query = MagicMock()
        update_query.filter.return_value = update_query
        update_query.update.return_value = 1
        
        call_count = {'user': 0}
        def query_side_effect(model):
            if model == User:
                call_count['user'] += 1
                if call_count['user'] == 2:
                    return update_query
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        hungry = [
            Hungry("Cherry", "hungry", 20.0),
            Hungry("Cherry", "hungry", 15.0)
        ]
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=hungry) as mock_find, \
             patch('endpoint.helpers.notifications.acquire_notification_slot', return_value=True), \
             patch('endpoint.helpers.notifications.send_notification'):
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Verify find_hungry_bottles was called with both bottles
            mock_find.assert_called_once()
            call_args = mock_find.call_args
            # call_args[0] is the tuple of positional arguments
            # call_args[0][0] is the first argument (the bottles list)
            assert len(call_args[0]) == 1  # One positional argument
            bottles_arg = call_args[0][0]  # The actual bottles list
            assert len(bottles_arg) == 2
            assert bottles_arg == [mock_bottle1, mock_bottle2]
    
    def test_no_game_started_bottles(self, real_db_session):
        """Test that bottles without game_started are excluded."""
        mock_user = MagicMock()
        mock_user.id = 1
        
        # Setup query objects
        user_query = MagicMock()
        user_query.filter.return_value.one_or_none.return_value = mock_user
        
        # Query filters for game_started=True, so should return empty
        bottle_query = MagicMock()
        self._setup_bottle_query_chain(bottle_query, [])
        
        def query_side_effect(model):
            if model == User:
                return user_query
            elif model == Bottle:
                return bottle_query
            return MagicMock()
        
        real_db_session.query.side_effect = query_side_effect
        
        with patch('endpoint.helpers.notifications.update_fullness'), \
             patch('endpoint.helpers.notifications.find_hungry_bottles', return_value=[]), \
             patch('endpoint.helpers.notifications.send_notification') as mock_send:
            
            check_and_notify_hungry_characters(real_db_session, 1, "+33684950535")
            
            # Should not send notification
            mock_send.assert_not_called()
