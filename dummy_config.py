"""Configuration for the Inspirational Quotes App."""

# Google Doc URL - Replace with your own Google Doc URL
# The doc should be publicly shared (Anyone with the link can view)
# Format: Each line in the document is treated as a separate quote
GOOGLE_DOC_URL = ""

# Alternative: Use a direct export URL if you know the document ID
# GOOGLE_DOC_ID = "YOUR_DOCUMENT_ID"

# Display settings
EXIT_DELAY_SECONDS = 30  # Time before exit is allowed
QUOTE_FONT_SIZE = 48  # Base font size for quotes
AUTHOR_FONT_SIZE = 32  # Font size for author attribution

# Color schemes - vibrant and inspiring
COLOR_SCHEMES = [
    {"bg": "#FF6B6B", "fg": "#FFFFFF", "accent": "#FFE66D"},  # Coral & Yellow
    {"bg": "#4ECDC4", "fg": "#FFFFFF", "accent": "#FF6B6B"},  # Teal & Coral
    {"bg": "#95E1D3", "fg": "#2C3E50", "accent": "#F38181"},  # Mint & Rose
    {"bg": "#A55EEA", "fg": "#FFFFFF", "accent": "#FFD93D"},  # Purple & Gold
    {"bg": "#FF9F43", "fg": "#FFFFFF", "accent": "#EE5A24"},  # Orange Burst
    {"bg": "#0ABDE3", "fg": "#FFFFFF", "accent": "#F8EFBA"},  # Ocean Blue
    {"bg": "#EE5A24", "fg": "#FFFFFF", "accent": "#F8EFBA"},  # Vibrant Red
    {"bg": "#10AC84", "fg": "#FFFFFF", "accent": "#FFD93D"},  # Emerald
    {"bg": "#5F27CD", "fg": "#FFFFFF", "accent": "#48DBFB"},  # Deep Purple
    {"bg": "#FF78C4", "fg": "#FFFFFF", "accent": "#7EFFF5"},  # Pink Dream
    {"bg": "#F368E0", "fg": "#FFFFFF", "accent": "#54E346"},  # Magenta Pop
    {"bg": "#00D2D3", "fg": "#1A1A2E", "accent": "#FF6B6B"},  # Cyan Fresh
]

# Fallback quotes if Google Doc is unavailable
FALLBACK_QUOTES = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Believe you can and you're halfway there. - Theodore Roosevelt",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "It is during our darkest moments that we must focus to see the light. - Aristotle",
    "The only impossible journey is the one you never begin. - Tony Robbins",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
    "What lies behind us and what lies before us are tiny matters compared to what lies within us. - Ralph Waldo Emerson",
    "The best time to plant a tree was 20 years ago. The second best time is now. - Chinese Proverb",
    "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
    "In the middle of difficulty lies opportunity. - Albert Einstein",
]
