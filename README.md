# Inspirational Quotes Display App

A vibrant fullscreen app that displays inspirational quotes from your Google Doc every time you open your laptop. The quote takes over your entire screen with colorful animations and can only be dismissed after 30 seconds of reflection.

## Features

- Reads quotes from your personal Google Doc
- Fullscreen display with vibrant, randomly-selected color schemes
- Animated gradient backgrounds and floating decorations
- 30-second mandatory reflection period before dismissal
- Automatic startup when you log in
- Works on Linux and macOS

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Your Google Doc

1. Create a Google Doc with your favorite inspirational quotes
2. Put each quote on its own line
3. Format: `Quote text - Author` (the author is optional)
4. Share the doc: Click "Share" → "Anyone with the link" → "Viewer"
5. Copy the document URL

Example Google Doc content:
```
The only way to do great work is to love what you do. - Steve Jobs
Believe you can and you're halfway there. - Theodore Roosevelt
In the middle of difficulty lies opportunity. - Albert Einstein
The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt
```

### 3. Configure the App

Edit `config.py` and replace `YOUR_DOCUMENT_ID` with your Google Doc URL:

```python
GOOGLE_DOC_URL = "https://docs.google.com/document/d/YOUR_ACTUAL_DOC_ID/edit"
```

### 4. Test the App

```bash
python inspo_app.py
```

A fullscreen display will appear with a random quote. Wait 30 seconds, then press `ESC` or `Q` to exit.

### 5. Set Up Autostart

Run the setup script to configure automatic startup:

```bash
python setup_autostart.py
```

Now the app will run every time you log into your computer!

## Configuration Options

Edit `config.py` to customize:

| Option | Default | Description |
|--------|---------|-------------|
| `GOOGLE_DOC_URL` | - | Your Google Doc URL with quotes |
| `EXIT_DELAY_SECONDS` | 30 | Seconds before exit is allowed |
| `QUOTE_FONT_SIZE` | 48 | Base font size for quotes |
| `AUTHOR_FONT_SIZE` | 32 | Font size for author text |
| `COLOR_SCHEMES` | 12 schemes | List of color palettes |
| `FALLBACK_QUOTES` | 10 quotes | Used when Google Doc is unavailable |

## File Structure

```
inspo/
├── inspo_app.py          # Main application
├── quote_fetcher.py      # Google Docs fetching logic
├── config.py             # Configuration settings
├── setup_autostart.py    # Autostart setup script
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Removing Autostart

To stop the app from running at startup:

```bash
python setup_autostart.py --remove
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `ESC` | Exit (after 30 seconds) |
| `Q` | Exit (after 30 seconds) |

## Troubleshooting

### Quotes not loading from Google Doc

1. Ensure the document is shared publicly ("Anyone with the link")
2. Check the URL in `config.py` is correct
3. The app will fall back to built-in quotes if the doc is inaccessible

### App not starting at login

1. Check that the autostart setup completed successfully
2. On Linux, verify `~/.config/autostart/inspo-quotes.desktop` exists
3. On macOS, verify `~/Library/LaunchAgents/com.inspo.quotes.plist` exists

### Display issues

1. Ensure you have a graphical environment running
2. On Linux, the `DISPLAY` environment variable must be set
3. Try running `python inspo_app.py` manually to test

## Adding Custom Color Schemes

Add new color schemes to `COLOR_SCHEMES` in `config.py`:

```python
{"bg": "#YOUR_BG_COLOR", "fg": "#TEXT_COLOR", "accent": "#ACCENT_COLOR"}
```

## License

MIT License - Feel free to modify and share!
