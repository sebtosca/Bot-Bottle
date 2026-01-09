# Core Module Testing Plan

## Overview

This document outlines the testing strategy for the `core/` module, which contains:
- **core/game/**: Feeding game logic, emoji processing, sticker selection
- **core/points/**: Points system, rewards, milestones, user statistics
- **core/state/**: Bottle state management, mood updates, response type selection

## Test Pyramid

### 1. Unit Tests (70% of tests)
**Goal**: Fast, isolated tests with heavy mocking

**Scope**:
- Pure functions (no DB, no I/O)
- Business logic validation
- Edge cases and error handling
- Input validation

**Mocking Strategy**:
- Mock database sessions and queries
- Mock file system operations (emoji_segmentation.json)
- Mock external dependencies (emoji library where needed)
- Control randomness with fixed seeds

### 2. Integration Tests (25% of tests)
**Goal**: Test components working together

**Scope**:
- Database interactions (with test DB)
- Function chains (e.g., `process_emoji_feed` → `update_fullness_after_feed` → `award_points`)
- State transitions
- Cross-module interactions

**Requirements**:
- Use test database (isolated from production)
- Clean up after each test
- Use fixtures for common data setup

### 3. End-to-End Tests (5% of tests)
**Goal**: Validate critical user flows

**Scope**:
- Complete feeding game flow
- Points accumulation flow
- State evolution flow
- Multi-step interactions

## Folder Structure

```
core/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── game/
│   │   │   ├── __init__.py
│   │   │   ├── test_emoji_processing.py
│   │   │   ├── test_feeding_mechanics.py
│   │   │   ├── test_sticker_selection.py
│   │   │   └── test_game_flow.py
│   │   ├── points/
│   │   │   ├── __init__.py
│   │   │   ├── test_points_awarding.py
│   │   │   ├── test_titles.py
│   │   │   ├── test_milestones.py
│   │   │   └── test_user_stats.py
│   │   └── state/
│   │       ├── __init__.py
│   │       ├── test_message_classification.py
│   │       ├── test_state_updates.py
│   │       └── test_response_selection.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_game_integration.py
│   │   ├── test_points_integration.py
│   │   └── test_state_integration.py
│   └── e2e/
│       ├── __init__.py
│       ├── test_feeding_game_flow.py
│       └── test_points_flow.py
```

## Testing Priorities

### Critical Functions (Test First)

**core/game/feeding_game.py**:
1. `extract_emojis_from_message` - Core emoji extraction
2. `validate_emoji_for_color` - Color validation logic
3. `process_emoji_feed` - Main feeding logic
4. `update_fullness_after_feed` - Fullness updates
5. `get_emoji_category` - Emoji categorization
6. `get_stickers_for_state` - Sticker selection

**core/points/rewards.py**:
1. `award_points` - Points awarding logic
2. `update_user_title` - Title progression
3. `check_daily_engagement` - Daily engagement tracking
4. `calculate_milestone_bonus` - Milestone calculations

**core/state/bottle_state.py**:
1. `classify_message_type` - Message classification
2. `update_bottle_state` - State transitions
3. `select_response_type` - Response type selection
4. `select_gif_by_mood` - GIF selection logic

## Mocking & Fixture Strategy

### Shared Fixtures (conftest.py)

```python
# Database fixtures
- mock_db_session: Mock SQLAlchemy session
- sample_user: Sample User object
- sample_bottle: Sample Bottle object
- sample_interaction: Sample Interaction object

# Game fixtures
- sample_emoji_segmentation: Mock emoji segmentation data
- sample_fullness_levels: Test fullness values
- sample_accessory_colors: Test colors

# Points fixtures
- sample_points_config: Points constants
- sample_title_thresholds: Title thresholds

# State fixtures
- sample_moods: Test mood values
- sample_message_types: Test message types
```

### Mocking Patterns

1. **Database Operations**: Mock `session.query()` and return values
2. **File System**: Mock `Path.exists()` and `open()` for emoji_segmentation.json
3. **Randomness**: Use `random.seed()` for deterministic tests
4. **Time**: Mock `datetime.utcnow()` for time-dependent tests

## Edge Cases to Test

### Emoji Processing
- Empty messages
- Messages with no emojis
- Mixed emoji and text
- Invalid emoji characters
- Multiple emojis of same type
- Emojis not in segmentation file

### Feeding Game
- Fullness at boundaries (0, 1, 0.5)
- Invalid color/emoji combinations
- Missing stickers
- Empty sticker directories
- Character ID mismatches

### Points System
- Negative points (should not happen)
- Zero points
- Points exceeding thresholds
- Multiple rapid awards
- Missing user/bottle
- Title boundary conditions

### State Management
- Empty interaction lists
- State transitions at boundaries
- Invalid mood values
- Missing stickers/GIFs
- Response type rotation logic

## Coverage Goals

- **Unit Tests**: 85%+ coverage
- **Integration Tests**: 70%+ coverage
- **E2E Tests**: Critical paths only
- **Overall**: 80%+ coverage for core module

## Test Execution

### Running Tests

```bash
# All core tests
pytest core/tests/

# Unit tests only
pytest core/tests/unit/ -m unit

# Integration tests only
pytest core/tests/integration/ -m integration

# E2E tests only
pytest core/tests/e2e/ -m e2e

# With coverage
pytest core/tests/ --cov=core --cov-report=html
```

### CI Integration

- Run unit tests on every commit
- Run integration tests on PR
- Run E2E tests on merge to main
- Fail if coverage drops below 80%

## Notes

- Tests should be deterministic (no flakiness)
- Use pytest fixtures for setup/teardown
- Mock external dependencies heavily
- Test error paths and edge cases
- Keep tests fast (< 1 second per test)
- Use descriptive test names
- Follow Arrange-Act-Assert pattern
