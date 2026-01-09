"""Generate visual stats images for users.

Creates beautiful, shareable stat cards showing user progress, points, and achievements.
"""

from typing import Dict, Optional, Tuple
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os
import platform


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def draw_gradient_rectangle(draw: ImageDraw.Draw, coords: Tuple[int, int, int, int], 
                           start_color: str, end_color: str, steps: int = 20):
    """Draw a gradient rectangle."""
    x1, y1, x2, y2 = coords
    rect_width = x2 - x1
    rect_height = y2 - y1
    
    start_rgb = hex_to_rgb(start_color)
    end_rgb = hex_to_rgb(end_color)
    
    for i in range(steps):
        ratio = i / (steps - 1) if steps > 1 else 0
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        
        y_start = y1 + int(rect_height * i / steps)
        y_end = y1 + int(rect_height * (i + 1) / steps)
        if y_end > y_start:
            draw.rectangle([x1, y_start, x2, y_end], fill=(r, g, b))


def get_fullness_color(fullness: float) -> str:
    """Get color for fullness level."""
    if fullness <= 33:
        return "#FF5722"  # Red/Orange (empty/hungry)
    elif fullness <= 66:
        return "#FFC107"  # Yellow (partially full)
    else:
        return "#4CAF50"  # Green (full)


# Color schemes for different titles
TITLE_COLORS = {
    "Novice": {
        "primary": "#4A90E2",  # Blue
        "secondary": "#E3F2FD",
        "accent": "#1976D2"
    },
    "Apprentice": {
        "primary": "#9C27B0",  # Purple
        "secondary": "#F3E5F5",
        "accent": "#7B1FA2"
    },
    "Master": {
        "primary": "#FF9800",  # Orange/Gold
        "secondary": "#FFF3E0",
        "accent": "#F57C00"
    }
}

# Character-specific color schemes
CHARACTER_COLORS = {
    "00001": {  # Cherry
        "primary": "#E91E63",      # Pink/Red
        "secondary": "#F8BBD0",   # Light pink
        "accent": "#C2185B",       # Dark pink
        "background": "#FFF0F5"    # Very light pink
    },
    "00002": {  # Pompon
        "primary": "#4CAF50",      # Green
        "secondary": "#C8E6C9",    # Light green
        "accent": "#2E7D32",       # Dark green
        "background": "#F1F8F4"    # Very light green
    }
}

# Title thresholds for progress calculation
TITLE_THRESHOLDS = {
    "Novice": 0,
    "Apprentice": 500,
    "Master": 2000,
}


def get_next_title_threshold(current_title: str) -> int:
    """Get the points threshold for the next title level."""
    if current_title == "Novice":
        return TITLE_THRESHOLDS["Apprentice"]
    elif current_title == "Apprentice":
        return TITLE_THRESHOLDS["Master"]
    else:
        return TITLE_THRESHOLDS["Master"] * 2  # Beyond Master


def _load_fonts():
    """Load fonts with cross-platform fallbacks. Returns tuple of fonts.
    
    Tries platform-specific font paths in order:
    1. Linux: DejaVu fonts
    2. macOS: System fonts
    3. Windows: System fonts
    4. Fallback: Default font (works on all platforms)
    """
    
    # Platform-specific font paths
    font_paths = []
    
    system = platform.system().lower()
    if system == "linux":
        # Linux font paths
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
    elif system == "darwin":  # macOS
        # macOS font paths
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    elif system == "windows":
        # Windows font paths
        windows_font_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        font_paths = [
            os.path.join(windows_font_dir, "arialbd.ttf"),  # Arial Bold
            os.path.join(windows_font_dir, "calibrib.ttf"),  # Calibri Bold
            os.path.join(windows_font_dir, "segoeuib.ttf"),  # Segoe UI Bold
        ]
    
    # Try to load fonts from platform-specific paths
    fonts_loaded = False
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, 48)
                header_font = ImageFont.truetype(font_path, 32)
                points_font = ImageFont.truetype(font_path, 56)
                body_font = ImageFont.truetype(font_path, 24)
                small_font = ImageFont.truetype(font_path, 20)
                fonts_loaded = True
                break
        except (OSError, IOError):
            continue
    
    # Fallback to default font (cross-platform)
    if not fonts_loaded:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        points_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    return title_font, header_font, points_font, body_font, small_font


def generate_base_template() -> Image.Image:
    """Generate a base template image with static design elements.
    
    This template is cached and reused. It contains:
    - Layout structure
    - Static labels and icons
    - Placeholder/default styling
    
    Returns:
        PIL Image object of the base template.
    """
    # Image dimensions optimized for WhatsApp
    width = 800
    height = 1200
    
    # Create image with white background
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    title_font, header_font, points_font, body_font, small_font = _load_fonts()
    
    # Use neutral colors for template (will be overlaid with title-specific colors)
    template_colors = {
        "primary": "#6C7A89",      # Neutral gray-blue
        "secondary": "#ECF0F1",    # Light gray
        "accent": "#95A5A6"        # Medium gray
    }
    
    y_position = 40
    
    # Header section with title badge area (placeholder)
    header_height = 120
    
    # Draw subtle shadow for header
    draw.rounded_rectangle([3, 3, width - 3, header_height + 3], radius=0, fill='#E0E0E0')
    
    # Draw header with gradient (neutral color - will be overlaid)
    draw_gradient_rectangle(draw, (0, 0, width, header_height), 
                           template_colors['primary'], template_colors['accent'])
    
    # Title placeholder area (centered)
    title_placeholder = "🏆 [TITLE]"
    title_bbox = draw.textbbox((0, 0), title_placeholder, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 30), title_placeholder, fill='white', font=title_font)
    
    y_position = header_height + 50
    
    # Points section - badge area (placeholder)
    points_badge_size = 120
    points_badge_x = 40
    points_badge_y = y_position
    
    badge_center_x = points_badge_x + points_badge_size // 2
    badge_center_y = points_badge_y + points_badge_size // 2
    badge_radius = points_badge_size // 2
    
    # Badge shadow
    shadow_offset = 3
    draw.ellipse([badge_center_x - badge_radius + shadow_offset, 
                  badge_center_y - badge_radius + shadow_offset,
                  badge_center_x + badge_radius + shadow_offset,
                  badge_center_y + badge_radius + shadow_offset],
                 fill='#CCCCCC')
    
    # Badge background (neutral - will be overlaid with title color)
    draw.ellipse([badge_center_x - badge_radius, 
                  badge_center_y - badge_radius,
                  badge_center_x + badge_radius,
                  badge_center_y + badge_radius],
                 fill=template_colors['primary'])
    
    # Inner highlight
    highlight_radius = badge_radius - 8
    highlight_rgb = hex_to_rgb(template_colors['primary'])
    highlight_color = tuple(min(255, c + 30) for c in highlight_rgb)
    draw.ellipse([badge_center_x - highlight_radius, 
                  badge_center_y - highlight_radius,
                  badge_center_x + highlight_radius,
                  badge_center_y + highlight_radius],
                 fill=highlight_color)
    
    # Points placeholder (will be overlaid)
    points_placeholder = "0"
    points_bbox = draw.textbbox((0, 0), points_placeholder, font=points_font)
    points_text_width = points_bbox[2] - points_bbox[0]
    points_text_x = badge_center_x - points_text_width // 2
    points_text_y = badge_center_y - points_bbox[3] // 2 - 5
    draw.text((points_text_x, points_text_y), points_placeholder, fill='white', font=points_font)
    
    # Points label (static)
    draw.text((points_badge_x + points_badge_size + 20, points_badge_y + 40), 
              "Points", fill='#666666', font=body_font)
    
    # Progress bar area (background only - fill will be overlaid)
    bar_x = 40
    bar_y = y_position + points_badge_size + 30
    bar_width = width - 80
    bar_height = 28
    bar_radius = 14
    
    # Shadow for progress bar
    draw.rounded_rectangle(
        [bar_x + 2, bar_y + 2, bar_x + bar_width + 2, bar_y + bar_height + 2],
        radius=bar_radius,
        fill='#D0D0D0'
    )
    
    # Background bar (empty - fill will be overlaid)
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
        radius=bar_radius,
        fill='#E0E0E0'
    )
    
    # Progress text area (placeholder - will be overlaid)
    progress_placeholder = "Prochain niveau: [NEXT] (0%)"
    draw.text((40, bar_y + bar_height + 10), progress_placeholder, fill='#666666', font=small_font)
    
    y_position = bar_y + bar_height + 50
    
    # Stats grid - Money and CO2 cards (structure only)
    stats_y = y_position
    card_width = (width - 60) // 2
    card_height = 100
    
    # Money card structure
    money_x = 20
    money_y = stats_y
    
    # Shadow
    draw.rounded_rectangle(
        [money_x + 2, money_y + 2, money_x + card_width + 2, money_y + card_height + 2],
        radius=15,
        fill='#D0D0D0'
    )
    
    # Card with gradient
    draw_gradient_rectangle(draw, (money_x, money_y, money_x + card_width, money_y + card_height),
                           template_colors['secondary'], '#FFFFFF')
    draw.rounded_rectangle(
        [money_x, money_y, money_x + card_width, money_y + card_height],
        radius=15,
        outline=template_colors['primary'],
        width=2
    )
    
    # Static label
    draw.text((money_x + 20, money_y + 15), "💰 Argent économisé", fill='#333333', font=small_font)
    # Value placeholder (will be overlaid)
    draw.text((money_x + 20, money_y + 45), "€0.00", fill=template_colors['primary'], font=body_font)
    
    # CO2 card structure
    co2_x = money_x + card_width + 20
    co2_y = stats_y
    
    # Shadow
    draw.rounded_rectangle(
        [co2_x + 2, co2_y + 2, co2_x + card_width + 2, co2_y + card_height + 2],
        radius=15,
        fill='#D0D0D0'
    )
    
    # Card with gradient
    draw_gradient_rectangle(draw, (co2_x, co2_y, co2_x + card_width, co2_y + card_height),
                           template_colors['secondary'], '#FFFFFF')
    draw.rounded_rectangle(
        [co2_x, co2_y, co2_x + card_width, co2_y + card_height],
        radius=15,
        outline=template_colors['primary'],
        width=2
    )
    
    # Static label
    draw.text((co2_x + 20, co2_y + 15), "🌱 CO2 économisé", fill='#333333', font=small_font)
    # Value placeholder (will be overlaid)
    draw.text((co2_x + 20, co2_y + 45), "0.00 kg", fill=template_colors['primary'], font=body_font)
    
    y_position = stats_y + card_height + 30
    
    # Characters section header (static)
    draw.text((40, y_position), "👥 Personnages", fill='#333333', font=header_font)
    y_position += 40
    
    # Character card placeholders (show 2 example cards)
    char_card_height = 90
    char_card_spacing = 15
    
    for i in range(2):  # Show 2 placeholder cards
        char_y = y_position + i * (char_card_height + char_card_spacing)
        
        # Character card shadow
        draw.rounded_rectangle(
            [42, char_y + 2, width - 38, char_y + char_card_height + 2],
            radius=12,
            fill='#D0D0D0'
        )
        
        # Character card (neutral background - will be overlaid with character colors)
        draw.rounded_rectangle(
            [40, char_y, width - 40, char_y + char_card_height],
            radius=12,
            fill='#F5F5F5',
            outline='#E0E0E0',
            width=2
        )
        
        # Character name placeholder
        char_name_placeholder = "[Character Name]"
        draw.text((60, char_y + 15), char_name_placeholder, fill='#333333', font=body_font)
        
        # Fullness bar area (background only - fill will be overlaid)
        fullness_bar_x = 60
        fullness_bar_y = char_y + 45
        fullness_bar_width = 120
        fullness_bar_height = 8
        
        # Fullness bar background
        draw.rounded_rectangle(
            [fullness_bar_x, fullness_bar_y, fullness_bar_x + fullness_bar_width, 
             fullness_bar_y + fullness_bar_height],
            radius=4,
            fill='#E0E0E0'
        )
        
        # Stats placeholder
        stats_placeholder = "0 pts • 0%"
        draw.text((fullness_bar_x + fullness_bar_width + 15, fullness_bar_y - 2), 
                 stats_placeholder, fill='#666666', font=small_font)
    
    # Footer (static)
    footer_y = height - 50
    footer_text = "Bot-Bottle • Vos statistiques"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
    footer_width = footer_bbox[2] - footer_bbox[0]
    footer_x = (width - footer_width) // 2
    
    # Footer background
    draw.rectangle([0, footer_y - 10, width, height], fill='#F5F5F5')
    draw.text((footer_x, footer_y), footer_text, fill='#999999', font=small_font)
    
    return img


def overlay_dynamic_data(template: Image.Image, stats: Dict) -> Image.Image:
    """Overlay dynamic data on the base template.
    
    Args:
        template: Base template image (from generate_base_template).
        stats: Dictionary from get_user_stats() containing user statistics.
    
    Returns:
        PIL Image with dynamic data overlaid.
    """
    # Create a copy to avoid modifying the original template
    img = template.copy()
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    title_font, header_font, points_font, body_font, small_font = _load_fonts()
    
    width, height = img.size
    
    current_title = stats.get('current_title', 'Novice')
    total_points = stats.get('total_points', 0)
    money_saved = stats.get('total_money_saved', 0.0)
    co2_saved = stats.get('total_co2_saved', 0.0)
    
    # Get color scheme for current title
    colors = TITLE_COLORS.get(current_title, TITLE_COLORS["Novice"])
    
    # Overlay title-specific header color
    header_height = 120
    # Draw header with title-specific gradient
    draw_gradient_rectangle(draw, (0, 0, width, header_height), 
                           colors['primary'], colors['accent'])
    
    # Overlay title text
    title_text = f"🏆 {current_title}"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    # Clear area and redraw
    draw.rectangle([title_x - 10, 25, title_x + title_width + 10, 75], fill=colors['primary'])
    draw.text((title_x, 30), title_text, fill='white', font=title_font)
    
    y_position = header_height + 50
    
    # Overlay points badge with title color
    points_badge_size = 120
    points_badge_x = 40
    points_badge_y = y_position
    badge_center_x = points_badge_x + points_badge_size // 2
    badge_center_y = points_badge_y + points_badge_size // 2
    badge_radius = points_badge_size // 2
    
    # Redraw badge with title color
    draw.ellipse([badge_center_x - badge_radius, 
                  badge_center_y - badge_radius,
                  badge_center_x + badge_radius,
                  badge_center_y + badge_radius],
                 fill=colors['primary'])
    
    # Inner highlight
    highlight_radius = badge_radius - 8
    highlight_rgb = hex_to_rgb(colors['primary'])
    highlight_color = tuple(min(255, c + 30) for c in highlight_rgb)
    draw.ellipse([badge_center_x - highlight_radius, 
                  badge_center_y - highlight_radius,
                  badge_center_x + highlight_radius,
                  badge_center_y + highlight_radius],
                 fill=highlight_color)
    
    # Overlay points number
    points_text = f"{total_points:,}"
    points_bbox = draw.textbbox((0, 0), points_text, font=points_font)
    points_text_width = points_bbox[2] - points_bbox[0]
    points_text_height = points_bbox[3] - points_bbox[1]
    points_text_x = badge_center_x - points_text_width // 2
    points_text_y = badge_center_y - points_text_height // 2 - 5
    # Clear area
    draw.ellipse([badge_center_x - points_text_width // 2 - 5,
                  badge_center_y - points_text_height // 2 - 5,
                  badge_center_x + points_text_width // 2 + 5,
                  badge_center_y + points_text_height // 2 + 5],
                 fill=highlight_color)
    draw.text((points_text_x, points_text_y), points_text, fill='white', font=points_font)
    
    # Overlay progress bar fill
    bar_x = 40
    bar_y = y_position + points_badge_size + 30
    bar_width = width - 80
    bar_height = 28
    bar_radius = 14
    
    # Calculate progress
    next_threshold = get_next_title_threshold(current_title)
    current_threshold = TITLE_THRESHOLDS.get(current_title, 0)
    progress_points = total_points - current_threshold
    progress_max = next_threshold - current_threshold
    
    if progress_max > 0:
        progress_percent = min(progress_points / progress_max, 1.0)
    else:
        progress_percent = 1.0
    
    fill_width = int(bar_width * progress_percent)
    if fill_width > 0:
        # Draw gradient fill
        fill_steps = min(20, max(5, fill_width // 3))
        for i in range(fill_steps):
            ratio = i / (fill_steps - 1) if fill_steps > 1 else 0
            start_rgb = hex_to_rgb(colors['accent'])
            end_rgb = hex_to_rgb(colors['primary'])
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
            
            x_start = bar_x + int(fill_width * i / fill_steps)
            x_end = bar_x + int(fill_width * (i + 1) / fill_steps)
            if x_end > x_start:
                draw.rectangle([x_start, bar_y, x_end, bar_y + bar_height], fill=(r, g, b))
        
        # Apply rounded corners
        if fill_width >= bar_radius:
            left_color = hex_to_rgb(colors['accent'])
            draw.rounded_rectangle(
                [bar_x, bar_y, bar_x + min(bar_radius, fill_width), bar_y + bar_height],
                radius=bar_radius,
                fill=left_color
            )
        
        if fill_width >= bar_radius * 2:
            right_color = hex_to_rgb(colors['primary'])
            draw.rounded_rectangle(
                [bar_x + fill_width - bar_radius, bar_y, bar_x + fill_width, bar_y + bar_height],
                radius=bar_radius,
                fill=right_color
            )
        
        # Glow effect
        if fill_width > bar_radius * 2:
            glow_rgb = hex_to_rgb(colors['primary'])
            glow_color = tuple(min(255, c + 20) for c in glow_rgb)
            try:
                draw.rounded_rectangle(
                    [bar_x + 1, bar_y + 1, bar_x + fill_width - 1, bar_y + bar_height - 1],
                    radius=bar_radius - 1,
                    outline=glow_color,
                    width=1
                )
            except:
                pass
    
    # Overlay progress text
    if current_title != "Master" or progress_max > 0:
        next_title = "Apprentice" if current_title == "Novice" else "Master"
        progress_percent_text = f"{int(progress_percent * 100)}%"
        progress_text = f"Prochain niveau: {next_title}"
        
        # Clear and redraw percentage
        percent_bbox = draw.textbbox((0, 0), progress_percent_text, font=header_font)
        percent_width = percent_bbox[2] - percent_bbox[0]
        draw.rectangle([bar_x + bar_width - percent_width - 5, bar_y - 40,
                       bar_x + bar_width + 5, bar_y - 10], fill='white')
        draw.text((bar_x + bar_width - percent_width, bar_y - 35), 
                  progress_percent_text, fill=colors['primary'], font=header_font)
        
        # Clear and redraw progress text
        text_bbox = draw.textbbox((0, 0), progress_text, font=small_font)
        draw.rectangle([40, bar_y + bar_height + 5, 40 + text_bbox[2] + 10, bar_y + bar_height + 25], fill='white')
        draw.text((40, bar_y + bar_height + 10), progress_text, fill='#666666', font=small_font)
    else:
        progress_text = "Niveau maximum atteint !"
        text_bbox = draw.textbbox((0, 0), progress_text, font=small_font)
        draw.rectangle([40, bar_y + bar_height + 5, 40 + text_bbox[2] + 10, bar_y + bar_height + 25], fill='white')
        draw.text((40, bar_y + bar_height + 10), progress_text, fill='#666666', font=small_font)
    
    # Overlay money and CO2 values
    stats_y = bar_y + bar_height + 50
    card_width = (width - 60) // 2
    card_height = 100
    money_x = 20
    money_y = stats_y
    
    # Clear and redraw money value
    money_text = f"€{money_saved:.2f}"
    money_bbox = draw.textbbox((0, 0), money_text, font=body_font)
    draw.rectangle([money_x + 20, money_y + 40, money_x + 20 + money_bbox[2] + 10, money_y + 70], 
                   fill='white')
    draw.text((money_x + 20, money_y + 45), money_text, fill=colors['primary'], font=body_font)
    
    # Overlay card borders with title color
    draw.rounded_rectangle(
        [money_x, money_y, money_x + card_width, money_y + card_height],
        radius=15,
        outline=colors['primary'],
        width=2
    )
    
    co2_x = money_x + card_width + 20
    co2_y = stats_y
    
    # Clear and redraw CO2 value
    co2_text = f"{co2_saved:.2f} kg"
    co2_bbox = draw.textbbox((0, 0), co2_text, font=body_font)
    draw.rectangle([co2_x + 20, co2_y + 40, co2_x + 20 + co2_bbox[2] + 10, co2_y + 70], 
                   fill='white')
    draw.text((co2_x + 20, co2_y + 45), co2_text, fill=colors['primary'], font=body_font)
    
    # Overlay card border with title color
    draw.rounded_rectangle(
        [co2_x, co2_y, co2_x + card_width, co2_y + card_height],
        radius=15,
        outline=colors['primary'],
        width=2
    )
    
    # Overlay character cards
    y_position = stats_y + card_height + 30 + 40  # After "Personnages" header
    characters = stats.get('characters', [])
    
    if characters:
        char_card_height = 90
        char_card_spacing = 15
        
        for i, char in enumerate(characters[:3]):
            char_y = y_position + i * (char_card_height + char_card_spacing)
            
            if char_y + char_card_height > height - 100:
                break
            
            # Get character-specific colors
            char_product_id = char.get('product_id', '00001')
            char_colors = CHARACTER_COLORS.get(char_product_id, CHARACTER_COLORS['00001'])
            
            # Overlay character card background
            draw.rounded_rectangle(
                [40, char_y, width - 40, char_y + char_card_height],
                radius=12,
                fill=char_colors['background'],
                outline=char_colors['primary'],
                width=2
            )
            
            # Overlay character name
            char_name = char.get('name', 'Inconnu')
            name_bbox = draw.textbbox((0, 0), char_name, font=body_font)
            draw.rectangle([60, char_y + 10, 60 + name_bbox[2] + 10, char_y + 35], 
                          fill=char_colors['background'])
            draw.text((60, char_y + 15), char_name, fill=char_colors['primary'], font=body_font)
            
            # Overlay fullness bar
            char_fullness = char.get('fullness', 0)
            fullness_bar_x = 60
            fullness_bar_y = char_y + 45
            fullness_bar_width = 120
            fullness_bar_height = 8
            fullness_color = get_fullness_color(char_fullness)
            
            # Clear fullness bar area
            draw.rounded_rectangle(
                [fullness_bar_x, fullness_bar_y, fullness_bar_x + fullness_bar_width, 
                 fullness_bar_y + fullness_bar_height],
                radius=4,
                fill='#E0E0E0'
            )
            
            # Draw fullness fill
            fullness_fill_width = int(fullness_bar_width * (char_fullness / 100))
            if fullness_fill_width > 0:
                draw.rounded_rectangle(
                    [fullness_bar_x, fullness_bar_y, 
                     fullness_bar_x + fullness_fill_width, 
                     fullness_bar_y + fullness_bar_height],
                    radius=4,
                    fill=fullness_color
                )
            
            # Overlay character stats
            char_points = char.get('points_earned', 0)
            stats_text = f"{char_points} pts • {char_fullness:.0f}%"
            stats_bbox = draw.textbbox((0, 0), stats_text, font=small_font)
            draw.rectangle([fullness_bar_x + fullness_bar_width + 15, fullness_bar_y - 5,
                           fullness_bar_x + fullness_bar_width + 15 + stats_bbox[2] + 10, fullness_bar_y + 15],
                          fill=char_colors['background'])
            draw.text((fullness_bar_x + fullness_bar_width + 15, fullness_bar_y - 2), 
                     stats_text, fill='#666666', font=small_font)
    
    return img


def generate_stats_image(stats: Dict, base_url: str = "http://localhost:5000") -> bytes:
    """Generate a beautiful stats image card using cached template.
    
    This function uses a cached base template and overlays dynamic data.
    The template is generated once and reused for performance.
    
    Args:
        stats: Dictionary from get_user_stats() containing user statistics.
        base_url: Base URL for serving the image (used in URL generation).
    
    Returns:
        PNG image as bytes.
    """
    # Get or generate cached template
    template = _get_cached_template()
    
    # Overlay dynamic data
    final_image = overlay_dynamic_data(template, stats)
    
    # Convert to bytes
    img_bytes = BytesIO()
    final_image.save(img_bytes, format='PNG', optimize=True)
    img_bytes.seek(0)
    
    return img_bytes.getvalue()


# Template cache
_template_cache = None


def _get_cached_template() -> Image.Image:
    """Get cached template or generate if not cached."""
    global _template_cache
    if _template_cache is None:
        _template_cache = generate_base_template()
    return _template_cache.copy()  # Return copy to avoid modifying cache
