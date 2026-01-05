### Cloudflare tunnel

- Cloudflare tunnel: `cloudflared tunnel --url http://localhost:5000`

### Flask server

- Start server: `python -m endpoint.endpoint`

### Test script

- Run webhook tests: `bash test_webhooks.sh`

---

### Emojis used for recycling colors

GREEN = 
🍷 Wine glass
🍸 Cocktail glass
🍺 Beer mug
🍻 Clinking beer mugs
🍾 Bottle with popping cork
🍶 Sake bottle and cup
🥃 Tumbler glass
🏺 Amphora
🫙 Jar

YELLOW = 
🍼 Baby bottle
🛍️ Shopping bags
🥤 Cup with straw
🧃 Beverage box
🧴 Bottle with lotion

BLUE = 
📦 Package/box
📄 Document
📝 Memo/note
📚 Books
📰 Newspaper
📧 Email
✉️ Envelope
📁 Folder
📋 Clipboard
🧻 Toilet paper

BLACK =
❤️ Heart
💔 Broken heart
🎉 Party/celebration
🔥 Fire
⭐ Star
💎 Gem/diamond
🎁 Gift
😀 Smiling face
🎈 Balloon
🎂 Cake
🍕 Pizza
🍔 Hamburger
🍰 Cake slice
🎨 Artist palette
🎭 Theater masks
❤️‍🔥 Heart on fire

---

### Emotional stickers, hat colors, and feeding hints

- Emotional stickers for each character live in:
  - Cherry: `stickers/` (e.g. `happy_cherry_green.webp`)
  - Pompon: `Pompom_normand_emotional_sticker/` (e.g. `angry_cider_yellow.webp`)
- Filenames follow the pattern: `emotion_character_color.ext`, for example:
  - `happy_cherry_green.webp`, `angry_cherry_yellow.webp`
  - `happy_cider_blue.webp`, `scared_cider_black.webp`
- Loader scripts:
  - `python scripts/load_cherry_emotional_stickers.py`
  - `python scripts/load_pompon_emotional_stickers.py`
- Each loader:
  - Parses the **emotion** (happy/angry/scared/shocked/neutral).
  - Parses the **hat/bin color** from the suffix (`green`, `yellow`, `blue`, `black`).
  - Stores both in `Sticker.mood_tags` (e.g. `happy,green`).
- At runtime:
  - The bottle’s `accessory_color` (GREEN/YELLOW/BLUE/BLACK) is the required bin color.
  - `select_sticker_by_mood` is called with both the current emotion and the required color.
  - It prefers stickers whose `mood_tags` match **both** emotion and color, so:
    - The hat color in the emotional sticker always matches the bin color the user should feed.

