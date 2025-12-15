#!/usr/bin/env python3
"""Quick script to check if stickers and GIFs exist in the database."""

from db.db import init_db, get_session, Sticker

init_db()
session = get_session()

stickers = session.query(Sticker).all()
print(f'Total stickers/GIFs in DB: {len(stickers)}')
print('Breakdown:')
for s_type in ['sticker', 'gif']:
    count = len([x for x in stickers if x.media_type == s_type])
    print(f'  {s_type}: {count}')

if len(stickers) == 0:
    print('\n⚠️  No stickers or GIFs found in database!')
    print('   This is why you\'re only getting text responses.')
else:
    print('\n✅ Media found in database')
    # Show a few examples
    print('\nSample entries:')
    for i, s in enumerate(stickers[:5]):
        print(f'  {i+1}. {s.filename} (type: {s.media_type}, mood_tags: {s.mood_tags})')

session.close()

