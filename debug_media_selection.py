#!/usr/bin/env python3
"""Debug script to test media selection logic."""

from db.db import init_db, get_session
from state_logic import select_sticker_by_mood, select_gif_by_mood, select_response_type
from db.db import User, Bottle

init_db()
session = get_session()

# Test with neutral mood (default)
mood = "neutral"
base_url = "http://localhost:5000"

print("=" * 60)
print("Testing Media Selection")
print("=" * 60)
print(f"Mood: {mood}")
print(f"Base URL: {base_url}")
print()

# Test sticker selection
print("Testing sticker selection...")
sticker_info = select_sticker_by_mood(session, mood, base_url)
if sticker_info:
    print(f"✅ Sticker found:")
    print(f"   Filename: {sticker_info.get('filename')}")
    print(f"   URL: {sticker_info.get('url')}")
    print(f"   Has 'url' key: {'url' in sticker_info}")
else:
    print("❌ No sticker found")

print()

# Test GIF selection
print("Testing GIF selection...")
gif_info = select_gif_by_mood(session, mood, base_url)
if gif_info:
    print(f"✅ GIF found:")
    print(f"   Filename: {gif_info.get('filename')}")
    print(f"   URL: {gif_info.get('url')}")
    print(f"   Has 'url' key: {'url' in gif_info}")
else:
    print("❌ No GIF found")

print()

# Test response type selection
print("Testing response type selection...")
# Get or create a test user and bottle
test_number = "33684950535"
user = session.query(User).filter_by(whatsapp_number=test_number).first()
if not user:
    print(f"Creating test user for {test_number}...")
    from db.db import get_or_create_user, get_or_create_bottle
    user = get_or_create_user(session, test_number)
    session.commit()

bottle = session.query(Bottle).filter_by(user_id=user.id).first()
if not bottle:
    from db.db import get_or_create_bottle
    bottle = get_or_create_bottle(session, user.id)
    session.commit()

bottle_id = bottle.id
print(f"Using bottle ID: {bottle_id}")

has_sticker = sticker_info is not None
has_gif = gif_info is not None

print(f"has_sticker: {has_sticker}")
print(f"has_gif: {has_gif}")

response_type = select_response_type(
    session=session,
    bottle_id=bottle_id,
    mood=mood,
    has_sticker=has_sticker,
    has_gif=has_gif
)

print(f"✅ Selected response type: {response_type}")
print()

print("=" * 60)
print("Summary")
print("=" * 60)
print(f"Sticker available: {'Yes' if sticker_info else 'No'}")
print(f"GIF available: {'Yes' if gif_info else 'No'}")
print(f"Response type: {response_type}")

if not sticker_info and not gif_info:
    print("\n⚠️  WARNING: No media available! This is why you're only getting text.")
elif not sticker_info:
    print("\n⚠️  WARNING: No stickers available for mood '{mood}'")
elif not gif_info:
    print("\n⚠️  WARNING: No GIFs available for mood '{mood}'")

session.close()

