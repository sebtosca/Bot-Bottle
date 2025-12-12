#!/usr/bin/env python3
"""Segment WhatsApp emojis into recycling bin categories using Mistral AI.

This script loads emojis from emoji-datasource-facebook, categorizes each emoji
into recycling bin colors (GREEN/glass, BLACK/non-recyclable, YELLOW/packaging-plastics, 
BLUE/paper), and outputs a JSON mapping file.

Usage:
    python emojies_segment.py
"""

import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import MISTRAL_API_KEY, MISTRAL_MODEL_NAME


def load_emoji_data(emoji_json_path: Optional[Path] = None) -> list[Dict[str, Any]]:
    """Load emoji data from emoji-datasource-facebook package.
    
    Args:
        emoji_json_path: Optional path to emoji.json file. If None, searches in node_modules.
    
    Returns:
        List of emoji objects with unified, short_name, name, category fields.
    
    Raises:
        FileNotFoundError: If emoji.json cannot be found.
        json.JSONDecodeError: If JSON parsing fails.
    """
    if emoji_json_path is None:
        # Try to find emoji.json in node_modules
        project_root = Path(__file__).parent
        emoji_json_path = project_root / "node_modules" / "emoji-datasource-facebook" / "emoji.json"
    
    if not emoji_json_path.exists():
        raise FileNotFoundError(
            f"emoji.json not found at {emoji_json_path}. "
            "Make sure emoji-datasource-facebook is installed: npm install emoji-datasource-facebook"
        )
    
    print(f"Loading emoji data from: {emoji_json_path}")
    with open(emoji_json_path, "r", encoding="utf-8") as f:
        emoji_data = json.load(f)
    
    print(f"✅ Loaded {len(emoji_data)} emojis")
    return emoji_data


def convert_unified_to_emoji(unified: str) -> Optional[str]:
    """Convert unified codepoint string to actual emoji character.
    
    Handles both single codepoints (e.g., "1F600") and multi-codepoint emojis
    (e.g., "1F600-200D-1F4BB" for emoji sequences).
    
    Args:
        unified: Unicode codepoint string, may contain hyphens for sequences.
    
    Returns:
        Emoji character string, or None if conversion fails.
    """
    try:
        # Split by hyphens to handle multi-codepoint emojis
        codepoints = unified.split("-")
        chars = []
        
        for codepoint in codepoints:
            # Convert hex string to integer, then to character
            char_code = int(codepoint, 16)
            chars.append(chr(char_code))
        
        # Join characters to form the emoji (handles sequences like ZWJ)
        return "".join(chars)
    
    except (ValueError, OverflowError) as e:
        print(f"⚠️  Failed to convert codepoint {unified}: {e}")
        return None


def categorize_emoji_with_mistral(
    emoji_char: str,
    emoji_name: str,
    emoji_short_name: str,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Dict[str, Any]:
    """Categorize a single emoji using Mistral AI.
    
    Args:
        emoji_char: The emoji character.
        emoji_name: Official Unicode name of the emoji.
        emoji_short_name: Short name/common name of the emoji.
        max_retries: Maximum number of retry attempts for API failures.
        retry_delay: Initial delay between retries (exponential backoff).
    
    Returns:
        Dictionary with category and reasoning, or {"category": "BLACK", "reasoning": "error"} on failure.
    """
    if not MISTRAL_API_KEY:
        print("⚠️  MISTRAL_API_KEY not set, skipping categorization")
        return {"category": "BLACK", "reasoning": "API key not configured"}
    
    try:
        from mistralai import Mistral
    except ImportError:
        print("⚠️  mistralai package not installed")
        return {"category": "BLACK", "reasoning": "Mistral package not installed"}
    
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as client_error:
        print(f"⚠️  Failed to create Mistral client: {client_error}")
        return {"category": "BLACK", "reasoning": f"Client error: {client_error}"}
    
    # Create categorization prompt
    categorization_prompt = f"""Categorize this emoji into a recycling bin category:

Emoji: {emoji_char}
Name: {emoji_name}
Short name: {emoji_short_name}

Categories:
- GREEN: Glass items (bottles, jars, glass containers, glassware)
- BLACK: Non-recyclable waste (general waste, items that can't be recycled, organic waste, mixed waste)
- YELLOW: Packaging and plastics (plastic containers, packaging materials, plastic bottles, plastic bags)
- BLUE: Paper products (paper, cardboard, books, newspapers, magazines, paper packaging)

For abstract emojis (emotions, symbols, faces, gestures), categorize based on what material they might represent if they were physical objects, or use BLACK for non-material concepts.

Respond with ONLY valid JSON in this exact format:
{{"category": "GREEN|BLACK|YELLOW|BLUE", "reasoning": "brief explanation"}}

Return ONLY the JSON, no other text."""
    
    messages = [
        {"role": "system", "content": "You are a recycling categorization assistant. Always return valid JSON."},
        {"role": "user", "content": categorization_prompt}
    ]
    
    for attempt in range(max_retries):
        try:
            chat_response = client.chat.complete(
                model=MISTRAL_MODEL_NAME,
                messages=messages,
                temperature=0.3,  # Lower temperature for consistent categorization
                max_tokens=150,
            )
            
            if not chat_response.choices or len(chat_response.choices) == 0:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                return {"category": "BLACK", "reasoning": "No response from API"}
            
            raw_content = chat_response.choices[0].message.content
            if not raw_content:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                return {"category": "BLACK", "reasoning": "Empty response from API"}
            
            # Extract JSON from response
            content = raw_content.strip()
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = content
            
            # Parse JSON
            try:
                category_data = json.loads(json_str)
                
                # Validate category
                category = category_data.get("category", "BLACK").upper()
                valid_categories = ["GREEN", "BLACK", "YELLOW", "BLUE"]
                if category not in valid_categories:
                    category = "BLACK"
                
                reasoning = category_data.get("reasoning", "No reasoning provided")
                
                return {
                    "category": category,
                    "reasoning": reasoning
                }
                
            except json.JSONDecodeError as json_error:
                if attempt < max_retries - 1:
                    print(f"⚠️  JSON parse error (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                print(f"⚠️  Failed to parse JSON: {json_error}")
                print(f"   Raw response: {content[:200]}")
                return {"category": "BLACK", "reasoning": f"JSON parse error: {json_error}"}
            
        except Exception as api_error:
            if attempt < max_retries - 1:
                print(f"⚠️  API error (attempt {attempt + 1}/{max_retries}), retrying...")
                time.sleep(retry_delay * (2 ** attempt))
                continue
            print(f"⚠️  API call failed: {api_error}")
            import traceback
            traceback.print_exc()
            return {"category": "BLACK", "reasoning": f"API error: {api_error}"}
    
    return {"category": "BLACK", "reasoning": "Max retries exceeded"}


def process_emojis(
    emoji_data: list[Dict[str, Any]],
    checkpoint_file: Optional[Path] = None,
    output_file: Path = Path("emoji_segmentation.json")
) -> Dict[str, str]:
    """Process all emojis and categorize them.
    
    Args:
        emoji_data: List of emoji objects from emoji.json.
        checkpoint_file: Optional path to save progress checkpoints.
        output_file: Path to output JSON file.
    
    Returns:
        Dictionary mapping emoji characters to categories.
    """
    # Load existing checkpoint if available
    segmentation = {}
    start_index = 0
    
    if checkpoint_file and checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
                segmentation = checkpoint_data.get("segmentation", {})
                start_index = checkpoint_data.get("last_index", 0)
                print(f"📂 Resuming from checkpoint: {len(segmentation)} emojis already processed")
        except Exception as e:
            print(f"⚠️  Failed to load checkpoint: {e}")
    
    total_emojis = len(emoji_data)
    processed_count = len(segmentation)
    skipped_count = 0
    error_count = 0
    
    print(f"\n{'=' * 60}")
    print(f"Processing {total_emojis} emojis")
    print(f"Starting from index {start_index}")
    print(f"{'=' * 60}\n")
    
    for i, emoji_obj in enumerate(emoji_data[start_index:], start=start_index):
        unified = emoji_obj.get("unified", "")
        short_name = emoji_obj.get("short_name", "")
        name = emoji_obj.get("name", "")
        
        if not unified:
            skipped_count += 1
            continue
        
        # Convert codepoint to emoji character
        emoji_char = convert_unified_to_emoji(unified)
        if not emoji_char:
            skipped_count += 1
            continue
        
        # Skip if already processed
        if emoji_char in segmentation:
            continue
        
        # Categorize with Mistral AI
        print(f"[{i + 1}/{total_emojis}] Processing: {emoji_char} ({short_name})")
        result = categorize_emoji_with_mistral(emoji_char, name, short_name)
        
        if result.get("category"):
            segmentation[emoji_char] = result["category"]
            print(f"  ✅ Category: {result['category']} - {result.get('reasoning', '')[:60]}")
        else:
            error_count += 1
            segmentation[emoji_char] = "BLACK"  # Default to BLACK on error
            print(f"  ❌ Error categorizing, defaulting to BLACK")
        
        # Save checkpoint every 10 emojis
        if checkpoint_file and (i + 1) % 10 == 0:
            checkpoint_data = {
                "last_index": i + 1,
                "segmentation": segmentation,
                "timestamp": datetime.now().isoformat()
            }
            try:
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
                print(f"  💾 Checkpoint saved")
            except Exception as e:
                print(f"  ⚠️  Failed to save checkpoint: {e}")
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Count categories
    category_counts = {
        "GREEN": sum(1 for cat in segmentation.values() if cat == "GREEN"),
        "BLACK": sum(1 for cat in segmentation.values() if cat == "BLACK"),
        "YELLOW": sum(1 for cat in segmentation.values() if cat == "YELLOW"),
        "BLUE": sum(1 for cat in segmentation.values() if cat == "BLUE"),
    }
    
    print(f"\n{'=' * 60}")
    print("Processing Complete")
    print(f"{'=' * 60}")
    print(f"Total processed: {len(segmentation)}")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"\nCategory distribution:")
    for category, count in category_counts.items():
        print(f"  {category}: {count}")
    
    return segmentation


def save_segmentation(
    segmentation: Dict[str, str],
    output_file: Path = Path("emoji_segmentation.json")
) -> None:
    """Save segmentation results to JSON file.
    
    Args:
        segmentation: Dictionary mapping emoji characters to categories.
        output_file: Path to output JSON file.
    """
    # Count categories
    category_counts = {
        "GREEN": sum(1 for cat in segmentation.values() if cat == "GREEN"),
        "BLACK": sum(1 for cat in segmentation.values() if cat == "BLACK"),
        "YELLOW": sum(1 for cat in segmentation.values() if cat == "YELLOW"),
        "BLUE": sum(1 for cat in segmentation.values() if cat == "BLUE"),
    }
    
    output_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_emojis": len(segmentation),
            "category_counts": category_counts
        },
        "segmentation": segmentation
    }
    
    print(f"\nSaving results to: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved {len(segmentation)} emoji categorizations")


def main():
    """Main function to run emoji segmentation."""
    print("=" * 60)
    print("WhatsApp Emoji Segmentation")
    print("=" * 60)
    print()
    
    # Check Mistral API key
    if not MISTRAL_API_KEY:
        print("❌ MISTRAL_API_KEY not set in .env file")
        print("   Please set MISTRAL_API_KEY in your .env file")
        return 1
    
    # Load emoji data
    try:
        emoji_data = load_emoji_data()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse emoji.json: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error loading emoji data: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Process emojis
    checkpoint_file = Path("emoji_segmentation_checkpoint.json")
    output_file = Path("emoji_segmentation.json")
    
    try:
        segmentation = process_emojis(emoji_data, checkpoint_file, output_file)
        
        # Save final results
        save_segmentation(segmentation, output_file)
        
        # Clean up checkpoint file
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            print(f"🗑️  Removed checkpoint file")
        
        print("\n✅ Emoji segmentation complete!")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print(f"Progress saved to checkpoint: {checkpoint_file}")
        print("Run the script again to resume from checkpoint")
        return 1
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
