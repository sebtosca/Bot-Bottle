"""Receipt verification system using OCR for bottle returns.

Handles receipt image processing, OCR text extraction, and verification logic.
"""

import re
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import requests
from sqlalchemy.orm import Session

from db.db import Bottle, User, ReceiptVerification
from config import MISTRAL_API_KEY, MISTRAL_MODEL_NAME


# Keywords to look for in receipts (French)
RECEIPT_KEYWORDS = [
    "bouteille", "consigne", "retour", "reprise", "recyclage",
    "verre", "plastique", "canette", "emballage", "déchet",
    "cherry", "cerise", "cidre", "pompon", "marasquin"
]


def download_image_from_url(image_url: str, access_token: Optional[str] = None, save_path: Optional[Path] = None) -> Optional[bytes]:
    """Download image from URL.
    
    Args:
        image_url: URL of the image to download.
        access_token: Optional access token for authenticated requests (WhatsApp media).
        save_path: Optional path to save the image locally.
    
    Returns:
        Image bytes, or None if download failed.
    """
    try:
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        image_data = response.content
        
        if save_path:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(image_data)
        
        return image_data
    except Exception as e:
        print(f"⚠️  Error downloading image from {image_url}: {e}")
        return None


def extract_text_with_mistral_vision(image_data: bytes) -> Optional[str]:
    """Extract text from image using Mistral AI vision API.
    
    Args:
        image_data: Image bytes.
    
    Returns:
        Extracted text, or None if extraction failed.
    """
    if not MISTRAL_API_KEY:
        print("⚠️  MISTRAL_API_KEY not set, cannot use OCR")
        return None
    
    try:
        from mistralai import Mistral
        import base64
        
        client = Mistral(api_key=MISTRAL_API_KEY)
        
        # Encode image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Use Mistral vision API to extract text
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_base64}"
                    },
                    {
                        "type": "text",
                        "text": "Extract all text from this receipt image. Return only the text content, no explanations."
                    }
                ]
            }
        ]
        
        response = client.chat.complete(
            model=MISTRAL_MODEL_NAME,
            messages=messages,
            max_tokens=500,
        )
        
        if response.choices and len(response.choices) > 0:
            extracted_text = response.choices[0].message.content.strip()
            return extracted_text
        else:
            print("⚠️  No text extracted from image")
            return None
            
    except Exception as e:
        print(f"⚠️  Error extracting text with Mistral: {e}")
        return None


def verify_receipt_content(ocr_text: str, bottle: Bottle) -> bool:
    """Verify if receipt content matches bottle return criteria.
    
    Args:
        ocr_text: Extracted text from receipt.
        bottle: Bottle object to verify.
    
    Returns:
        True if receipt appears valid, False otherwise.
    """
    if not ocr_text:
        return False
    
    text_lower = ocr_text.lower()
    
    # Check for receipt keywords
    keyword_matches = sum(1 for keyword in RECEIPT_KEYWORDS if keyword.lower() in text_lower)
    
    # Need at least 2 keyword matches to consider valid
    if keyword_matches < 2:
        print(f"   ⚠️  Only {keyword_matches} receipt keywords found (need at least 2)")
        return False
    
    # Check for character-specific keywords
    from models.characters import get_character_config
    char_config = get_character_config(bottle.product_id)
    character_name = char_config.get("name", "").lower()
    
    # Look for price/amount indicators (consigne is usually shown as a credit)
    has_amount = bool(re.search(r'\d+[.,]\d{2}', text_lower)) or bool(re.search(r'consigne', text_lower))
    
    # Valid if has keywords and amount/consigne mention
    is_valid = keyword_matches >= 2 and has_amount
    
    print(f"   📄 Receipt verification:")
    print(f"      Keywords found: {keyword_matches}")
    print(f"      Has amount/consigne: {has_amount}")
    print(f"      Valid: {is_valid}")
    
    return is_valid


def verify_receipt(
    session: Session,
    user_id: int,
    bottle_id: int,
    image_url: str,
    access_token: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[ReceiptVerification]]:
    """Verify a receipt image for bottle return.
    
    Args:
        session: Database session.
        user_id: User ID.
        bottle_id: Bottle ID being returned.
        image_url: URL of the receipt image.
        access_token: Optional access token for downloading WhatsApp media.
    
    Returns:
        Tuple of (is_verified, error_message, receipt_verification_object)
    """
    bottle = session.query(Bottle).filter_by(id=bottle_id, user_id=user_id).first()
    if not bottle:
        return False, "Bottle not found", None
    
    if bottle.returned:
        return False, "Bottle already returned", None
    
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return False, "User not found", None
    
    print(f"🔍 Verifying receipt for bottle {bottle_id} (user {user_id})")
    print(f"   Image URL: {image_url}")
    
    # Download image (with access token if provided for WhatsApp media)
    image_data = download_image_from_url(image_url, access_token=access_token)
    if not image_data:
        return False, "Failed to download image", None
    
    # Extract text using OCR
    ocr_text = extract_text_with_mistral_vision(image_data)
    if not ocr_text:
        # Create pending verification record even if OCR fails
        # Admin can review manually
        verification = ReceiptVerification(
            bottle_id=bottle_id,
            user_id=user_id,
            receipt_image_url=image_url,
            ocr_text=None,
            verification_status="pending",
            points_awarded=0
        )
        session.add(verification)
        session.commit()
        return False, "Could not extract text from image. Verification pending manual review.", verification
    
    print(f"   📝 Extracted text (first 200 chars): {ocr_text[:200]}...")
    
    # Verify receipt content
    is_valid = verify_receipt_content(ocr_text, bottle)
    
    # Create verification record
    verification = ReceiptVerification(
        bottle_id=bottle_id,
        user_id=user_id,
        receipt_image_url=image_url,
        ocr_text=ocr_text,
        verification_status="verified" if is_valid else "rejected",
        points_awarded=0
    )
    
    if is_valid:
        # Mark bottle as returned
        from datetime import datetime
        bottle.returned = True
        bottle.return_verified = True
        bottle.return_receipt_url = image_url
        bottle.returned_at = datetime.utcnow()
        session.add(bottle)
        
        # Calculate and record savings
        from core.game.feeding_game import calculate_and_record_savings
        savings = calculate_and_record_savings(session, bottle_id)
        
        # Award points
        from core.points import award_points
        points, title_update = award_points(session, user_id, "bottle_return", bottle_id=bottle_id)
        verification.points_awarded = points
        
        verification.verified_at = datetime.utcnow()
        
        print(f"   ✅ Receipt verified! Points awarded: {points}")
        print(f"   💰 Money saved: €{savings['money_saved']:.2f}")
        print(f"   🌱 CO2 saved: {savings['co2_saved']:.2f} kg")
    else:
        print(f"   ❌ Receipt verification failed")
    
    session.add(verification)
    session.commit()
    
    return is_valid, None, verification
