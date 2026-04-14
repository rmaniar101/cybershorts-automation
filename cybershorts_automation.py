"""
CyberShorts Automation - Complete Production Version
Receives JSON from Make.com, generates carousel images, sends to Telegram
Handles white text, DD-MMM-YYYY date format, and single unified caption
"""

from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import requests
import json
import re
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
WIDTH, HEIGHT = 1080, 1350
BG_COLOR = '#0F172A'  # Deep Navy
ACCENT_COLOR = '#3B82F6'  # Bright Blue
TEXT_PRIMARY = '#FFFFFF'  # Pure White (updated from grey)
TEXT_SECONDARY = '#FFFFFF'  # Pure White (updated from grey)
CARD_BG = '#1E293B'  # Dark Slate
MARGIN_X = int(WIDTH * 0.10)
CARD_PADDING = 30

# Environment variables (set in WSGI config)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    try:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError) as e:
        logger.error(f"Invalid hex color: {hex_color}, error: {e}")
        return (255, 255, 255)  # Default to white

def load_fonts():
    """Load fonts with fallback"""
    try:
        return {
            'hero': ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 72),
            'heading': ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 50),
            'subhead': ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 38),
            'body': ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 26),
            'small': ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22),
            'tiny': ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18),
            'tagline': ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
        }
    except Exception as e:
        logger.warning(f"Failed to load custom fonts: {e}, using default")
        default_font = ImageFont.load_default()
        return {
            'hero': default_font,
            'heading': default_font,
            'subhead': default_font,
            'body': default_font,
            'small': default_font,
            'tiny': default_font,
            'tagline': default_font
        }

def sanitize_text(text):
    """Sanitize text input to prevent injection attacks"""
    if not isinstance(text, str):
        return str(text)
    # Remove any potential control characters
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    return sanitized[:5000]  # Limit length to prevent memory issues

def validate_date_format(date_str):
    """Validate and parse date string to DD-MMM-YYYY format"""
    try:
        # Try DD-MMM-YYYY format
        parsed_date = datetime.strptime(date_str, "%d-%b-%Y")
        return parsed_date.strftime("%d-%b-%Y")
    except ValueError:
        # If it fails, try other common formats
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"]:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime("%d-%b-%Y")
            except ValueError:
                continue
        # If all fail, use today's date
        logger.warning(f"Invalid date format: {date_str}, using today's date")
        return datetime.now().strftime("%d-%b-%Y")

def create_title_slide(date_str):
    """Generate title slide with white text and DD-MMM-YYYY date"""
    try:
        img = Image.new('RGB', (WIDTH, HEIGHT), hex_to_rgb(BG_COLOR))
        draw = ImageDraw.Draw(img)
        fonts = load_fonts()
        
        # Validate and format date
        formatted_date = validate_date_format(sanitize_text(date_str))
        
        y = int(HEIGHT * 0.22)
        
        # Badge
        badge_text = "CYBERSHORTS"
        bbox = draw.textbbox((0, 0), badge_text, font=fonts['subhead'])
        badge_width = (bbox[2] - bbox[0]) + 60
        badge_height = 60
        badge_x = (WIDTH - badge_width) // 2
        
        draw.rounded_rectangle(
            [(badge_x, y), (badge_x + badge_width, y + badge_height)],
            radius=30,
            fill=hex_to_rgb(ACCENT_COLOR)
        )
        draw.text((badge_x + 30, y + 12), badge_text, fill='#FFFFFF', font=fonts['subhead'])
        
        y += 100
        
        # Subtitle - WHITE
        subtitle_text = "by St. FOX"
        bbox = draw.textbbox((0, 0), subtitle_text, font=fonts['body'])
        subtitle_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - subtitle_width) // 2, y), subtitle_text, fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['body'])
        
        y += 80
        
        # Main heading - WHITE
        heading_text = "Today's Top 5"
        bbox = draw.textbbox((0, 0), heading_text, font=fonts['hero'])
        heading_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - heading_width) // 2, y), heading_text, fill=hex_to_rgb(TEXT_PRIMARY), font=fonts['hero'])
        
        y += 90
        
        # Subheading - BRIGHT BLUE
        subheading_text = "AI & Cybersecurity Alerts"
        bbox = draw.textbbox((0, 0), subheading_text, font=fonts['subhead'])
        subheading_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - subheading_width) // 2, y), subheading_text, fill=hex_to_rgb(ACCENT_COLOR), font=fonts['subhead'])
        
        y += 60
        
        # Tagline 1 - WHITE
        tagline1_text = "You may or may not know"
        bbox = draw.textbbox((0, 0), tagline1_text, font=fonts['tagline'])
        tagline1_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - tagline1_width) // 2, y), tagline1_text, fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['tagline'])
        
        y += 80
        
        # Accent line
        line_width = 200
        line_x = (WIDTH - line_width) // 2
        draw.rectangle([(line_x, y), (line_x + line_width, y + 4)], fill=hex_to_rgb(ACCENT_COLOR))
        
        y += 50
        
        # Tagline 2 - WHITE
        tagline2_text = "Share it, with who may need it."
        bbox = draw.textbbox((0, 0), tagline2_text, font=fonts['tagline'])
        tagline2_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - tagline2_width) // 2, y), tagline2_text, fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['tagline'])
        
        # Date - DD-MMM-YYYY format - WHITE
        bbox = draw.textbbox((0, 0), formatted_date, font=fonts['body'])
        date_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - date_width) // 2, HEIGHT - 180), formatted_date, fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['body'])
        
        # Bottom line
        bottom_line_y = HEIGHT - 35
        draw.rectangle([(MARGIN_X, bottom_line_y), (WIDTH - MARGIN_X, bottom_line_y + 2)], fill=hex_to_rgb(ACCENT_COLOR))
        
        # Hashtags - WHITE
        hashtag_text = "#CyberSecurity #AISecurity #StFox #saintfox"
        bbox = draw.textbbox((0, 0), hashtag_text, font=fonts['small'])
        hashtag_width = bbox[2] - bbox[0]
        draw.text(((WIDTH - hashtag_width) // 2, bottom_line_y - 35), hashtag_text, fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['small'])
        
        return img
        
    except Exception as e:
        logger.error(f"Error creating title slide: {e}")
        raise

def create_news_slide(item):
    """Generate news slide with white text"""
    try:
        img = Image.new('RGB', (WIDTH, HEIGHT), hex_to_rgb(BG_COLOR))
        draw = ImageDraw.Draw(img)
        fonts = load_fonts()
        
        # Sanitize inputs
        number = int(item.get('number', 1))
        title = sanitize_text(item.get('title', 'Untitled'))
        news = sanitize_text(item.get('news', ''))
        take = sanitize_text(item.get('take', ''))
        source = sanitize_text(item.get('source', 'Unknown'))
        date_str = sanitize_text(item.get('date', datetime.now().strftime("%d-%b-%Y")))
        
        # Validate date
        formatted_date = validate_date_format(date_str)
        
        y = int(HEIGHT * 0.06)
        
        # Badge
        badge_text = f"CYBERSHORT #{number}"
        bbox = draw.textbbox((0, 0), badge_text, font=fonts['small'])
        badge_width = (bbox[2] - bbox[0]) + 40
        badge_height = 45
        
        draw.rounded_rectangle(
            [(MARGIN_X, y), (MARGIN_X + badge_width, y + badge_height)],
            radius=23,
            fill=hex_to_rgb(ACCENT_COLOR)
        )
        draw.text((MARGIN_X + 20, y + 10), badge_text, fill='#FFFFFF', font=fonts['small'])
        
        y += 55
        
        # Subtitle - WHITE
        subtitle_x = MARGIN_X + 20
        draw.text((subtitle_x, y), "by St. FOX", fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['tiny'])
        
        y += 40
        
        # Accent line
        draw.rectangle([(subtitle_x, y), (subtitle_x + 80, y + 4)], fill=hex_to_rgb(ACCENT_COLOR))
        
        y += 30
        
        # Title - WHITE
        wrapped_title = textwrap.fill(title, width=26)
        draw.text((MARGIN_X, y), wrapped_title, fill=hex_to_rgb(TEXT_PRIMARY), font=fonts['heading'])
        
        title_lines = wrapped_title.count('\n') + 1
        y += (title_lines * 58) + 35
        
        # News card
        wrapped_news = textwrap.fill(news, width=42)
        news_lines = wrapped_news.count('\n') + 1
        news_card_height = CARD_PADDING + 25 + 30 + (news_lines * 32) + CARD_PADDING
        news_card_y = y
        
        draw.rounded_rectangle(
            [(MARGIN_X, news_card_y), (WIDTH - MARGIN_X, news_card_y + news_card_height)],
            radius=12,
            fill=hex_to_rgb(CARD_BG),
            outline=hex_to_rgb(ACCENT_COLOR),
            width=2
        )
        
        draw.text((MARGIN_X + CARD_PADDING, news_card_y + CARD_PADDING), "THE NEWS", fill=hex_to_rgb(ACCENT_COLOR), font=fonts['tiny'])
        draw.text((MARGIN_X + CARD_PADDING, news_card_y + CARD_PADDING + 30), wrapped_news, fill=hex_to_rgb(TEXT_PRIMARY), font=fonts['body'], spacing=6)
        
        y = news_card_y + news_card_height + 20
        
        # Take card
        wrapped_take = textwrap.fill(take, width=44)
        take_lines = wrapped_take.count('\n') + 1
        take_card_height = CARD_PADDING + 25 + 30 + (take_lines * 28) + CARD_PADDING
        take_card_y = y
        
        draw.rounded_rectangle(
            [(MARGIN_X, take_card_y), (WIDTH - MARGIN_X, take_card_y + take_card_height)],
            radius=12,
            fill=hex_to_rgb(CARD_BG),
            outline=hex_to_rgb(ACCENT_COLOR),
            width=2
        )
        
        draw.text((MARGIN_X + CARD_PADDING, take_card_y + CARD_PADDING), "St. FOX TAKE", fill=hex_to_rgb(ACCENT_COLOR), font=fonts['tiny'])
        # Take text WHITE
        draw.text((MARGIN_X + CARD_PADDING, take_card_y + CARD_PADDING + 30), wrapped_take, fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['small'], spacing=5)
        
        y = take_card_y + take_card_height + 25
        
        # Footer - WHITE with DD-MMM-YYYY date
        draw.text((MARGIN_X, y), f"{formatted_date} | Source: {source}", fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['small'])
        y += 30
        draw.text((MARGIN_X, y), "stfox.com", fill=hex_to_rgb(ACCENT_COLOR), font=fonts['small'])
        
        # Bottom
        bottom_line_y = HEIGHT - 35
        draw.rectangle([(MARGIN_X, bottom_line_y), (WIDTH - MARGIN_X, bottom_line_y + 2)], fill=hex_to_rgb(ACCENT_COLOR))
        # Hashtags WHITE
        draw.text((MARGIN_X, bottom_line_y - 30), "#CyberSecurity #AISecurity #StFox #saintfox", fill=hex_to_rgb(TEXT_SECONDARY), font=fonts['tiny'])
        
        return img
        
    except Exception as e:
        logger.error(f"Error creating news slide: {e}")
        raise

def send_to_telegram(images, caption):
    """Send images as media group to Telegram with single caption"""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            raise ValueError("Telegram credentials not configured")
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup"
        
        # Sanitize caption
        clean_caption = sanitize_text(caption)
        
        # Prepare media group
        media = []
        files = {}
        
        for i, img in enumerate(images):
            # Save image to bytes
            import io
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=95)
            img_bytes.seek(0)
            
            file_key = f"photo{i}"
            files[file_key] = (f"slide_{i}.jpg", img_bytes, 'image/jpeg')
            
            media_item = {
                "type": "photo",
                "media": f"attach://{file_key}"
            }
            
            # Add caption only to the first image
            if i == 0:
                media_item["caption"] = clean_caption
                media_item["parse_mode"] = "HTML"
            
            media.append(media_item)
        
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "media": json.dumps(media)
        }
        
        response = requests.post(url, data=data, files=files, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Successfully sent {len(images)} images to Telegram")
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")
        raise

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Receives text from Make.com containing JSON
    Extracts JSON even if surrounded by extra text
    Expected format:
    {
        "date": "13-Apr-2026",
        "news_items": [{number, title, news, take, source}, ...],
        "caption": "single unified caption"
    }
    """
    try:
        # Get raw text from request
        raw_data = request.get_data(as_text=True)
        
        if not raw_data:
            return jsonify({
                "status": "error",
                "message": "Empty request body"
            }), 400
        
        logger.info(f"Received webhook request, length: {len(raw_data)}")
        
        # Try to parse as JSON first (if it's already clean)
        data = None
        try:
            data = json.loads(raw_data)
            logger.info("Parsed JSON directly")
        except json.JSONDecodeError:
            # If that fails, extract JSON from text using regex
            logger.info("Direct JSON parse failed, attempting extraction")
            
            # Find the first { and last } to extract JSON object
            match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', raw_data, re.DOTALL)
            if not match:
                # Try a more greedy approach
                start = raw_data.find('{')
                end = raw_data.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = raw_data[start:end+1]
                    try:
                        data = json.loads(json_str)
                        logger.info("Extracted JSON using fallback method")
                    except json.JSONDecodeError:
                        pass
            else:
                json_str = match.group(0)
                try:
                    data = json.loads(json_str)
                    logger.info("Extracted JSON using regex")
                except json.JSONDecodeError:
                    pass
        
        if data is None:
            return jsonify({
                "status": "error",
                "message": "No valid JSON found in request body"
            }), 400
        
        # Validate required fields
        if 'date' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: date"
            }), 400
        
        if 'news_items' not in data or not isinstance(data['news_items'], list):
            return jsonify({
                "status": "error",
                "message": "Missing or invalid field: news_items (must be array)"
            }), 400
        
        if 'caption' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: caption"
            }), 400
        
        if len(data['news_items']) != 5:
            return jsonify({
                "status": "error",
                "message": f"Expected 5 news items, got {len(data['news_items'])}"
            }), 400
        
        # Validate each news item
        for i, item in enumerate(data['news_items']):
            required_fields = ['number', 'title', 'news', 'take', 'source']
            for field in required_fields:
                if field not in item:
                    return jsonify({
                        "status": "error",
                        "message": f"News item {i+1} missing required field: {field}"
                    }), 400
        
        logger.info(f"Validated data: {len(data['news_items'])} news items, date: {data['date']}")
        
        # Generate images
        images = []
        
        # Title slide
        logger.info("Generating title slide")
        title_img = create_title_slide(data['date'])
        images.append(title_img)
        
        # News slides
        for i, item in enumerate(data['news_items']):
            logger.info(f"Generating news slide {i+1}")
            item['date'] = data['date']
            news_img = create_news_slide(item)
            images.append(news_img)
        
        logger.info(f"Generated {len(images)} images successfully")
        
        # Send to Telegram with single caption
        logger.info("Sending to Telegram")
        telegram_response = send_to_telegram(images, data['caption'])
        
        logger.info("Workflow completed successfully")
        return jsonify({
            "status": "success",
            "message": f"Successfully sent {len(images)} images to Telegram",
            "images_count": len(images),
            "telegram_response": telegram_response
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return jsonify({
            "status": "error",
            "message": f"JSON parsing error: {str(e)}"
        }), 400
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "CyberShorts Automation",
        "version": "2.0"
    })

@app.route('/', methods=['GET'])
def home():
    """Home page"""
    return jsonify({
        "service": "CyberShorts Automation",
        "version": "2.0",
        "status": "running",
        "endpoints": {
            "/": "GET - Service info",
            "/health": "GET - Health check",
            "/webhook": "POST - Receive carousel data from Make.com"
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
