#!/usr/bin/env python3
"""
Inspirational Quotes Display App

A fullscreen app that displays inspirational quotes from a Google Doc
with vibrant colors. Can only be exited after 30 seconds.
"""

import random
import tkinter as tk
from tkinter import font as tkfont
import math
import sys

from config import (
    COLOR_SCHEMES,
    EXIT_DELAY_SECONDS,
    QUOTE_FONT_SIZE,
    AUTHOR_FONT_SIZE,
)
from quote_fetcher import fetch_quotes_from_google_doc


class InspirationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Daily Inspiration")

        # Get screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Make fullscreen and always on top
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)

        # Disable window close button initially
        self.root.protocol("WM_DELETE_WINDOW", self.try_exit)

        # Block escape key initially
        self.root.bind('<Escape>', self.try_exit)
        self.root.bind('<q>', self.try_exit)
        self.root.bind('<Q>', self.try_exit)

        # Timer state
        self.time_remaining = EXIT_DELAY_SECONDS
        self.can_exit = False

        # Animation state
        self.animation_offset = 0
        self.pulse_phase = 0

        # Select random color scheme
        self.colors = random.choice(COLOR_SCHEMES)

        # Fetch and select a quote
        self.quotes = fetch_quotes_from_google_doc()
        self.current_quote = random.choice(self.quotes)

        # Parse quote and author
        self.quote_text, self.author = self.parse_quote(self.current_quote)

        # Setup UI
        self.setup_ui()

        # Start animations and timer
        self.animate_background()
        self.update_timer()
        self.pulse_quote()

    def parse_quote(self, quote: str) -> tuple:
        """Parse quote text and author from a quote string."""
        # Common patterns: "Quote - Author", "Quote — Author", '"Quote" - Author'
        separators = [' - ', ' — ', ' – ', ' ~ ']

        for sep in separators:
            if sep in quote:
                parts = quote.rsplit(sep, 1)
                if len(parts) == 2:
                    quote_text = parts[0].strip().strip('"').strip("'")
                    author = parts[1].strip()
                    return quote_text, author

        # No author found
        return quote.strip().strip('"').strip("'"), ""

    def setup_ui(self):
        """Create the UI elements."""
        # Main canvas for animated background
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Draw initial background
        self.draw_background()

        # Create fonts
        self.quote_font = tkfont.Font(
            family="Helvetica",
            size=self.calculate_font_size(),
            weight="bold"
        )
        self.author_font = tkfont.Font(
            family="Helvetica",
            size=AUTHOR_FONT_SIZE,
            slant="italic"
        )
        self.timer_font = tkfont.Font(
            family="Helvetica",
            size=24,
            weight="bold"
        )
        self.hint_font = tkfont.Font(
            family="Helvetica",
            size=16
        )

        # Quote text (centered)
        wrapped_quote = self.wrap_text(self.quote_text, 50)
        self.quote_label = self.canvas.create_text(
            self.screen_width // 2,
            self.screen_height // 2 - 50,
            text=f'"{wrapped_quote}"',
            font=self.quote_font,
            fill=self.colors["fg"],
            justify=tk.CENTER,
            width=self.screen_width - 200
        )

        # Author text
        if self.author:
            self.author_label = self.canvas.create_text(
                self.screen_width // 2,
                self.screen_height // 2 + 150,
                text=f"— {self.author}",
                font=self.author_font,
                fill=self.colors["accent"],
                justify=tk.CENTER
            )

        # Timer display at bottom
        self.timer_label = self.canvas.create_text(
            self.screen_width // 2,
            self.screen_height - 80,
            text=f"Take a moment to reflect... ({self.time_remaining}s)",
            font=self.timer_font,
            fill=self.colors["fg"],
            justify=tk.CENTER
        )

        # Decorative elements
        self.draw_decorations()

    def calculate_font_size(self) -> int:
        """Calculate appropriate font size based on quote length."""
        length = len(self.quote_text)
        if length > 200:
            return QUOTE_FONT_SIZE - 16
        elif length > 150:
            return QUOTE_FONT_SIZE - 12
        elif length > 100:
            return QUOTE_FONT_SIZE - 8
        elif length > 50:
            return QUOTE_FONT_SIZE - 4
        return QUOTE_FONT_SIZE

    def wrap_text(self, text: str, max_chars: int) -> str:
        """Wrap text to specified character width."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def draw_background(self):
        """Draw the animated gradient background."""
        self.canvas.delete("bg")

        # Create gradient effect with animated offset
        for i in range(0, self.screen_height, 4):
            ratio = (i + self.animation_offset) % self.screen_height / self.screen_height
            color = self.interpolate_color(
                self.colors["bg"],
                self.darken_color(self.colors["bg"], 0.3),
                ratio
            )
            self.canvas.create_line(
                0, i, self.screen_width, i,
                fill=color, width=4, tags="bg"
            )

        self.canvas.tag_lower("bg")

    def draw_decorations(self):
        """Draw decorative geometric shapes."""
        self.decorations = []

        # Draw floating circles
        for _ in range(15):
            x = random.randint(0, self.screen_width)
            y = random.randint(0, self.screen_height)
            size = random.randint(20, 100)
            alpha_color = self.adjust_alpha(self.colors["accent"], 0.2)

            circle = self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                outline=alpha_color, width=2, tags="decor"
            )
            self.decorations.append({
                'id': circle,
                'x': x,
                'y': y,
                'size': size,
                'speed_x': random.uniform(-0.5, 0.5),
                'speed_y': random.uniform(-0.5, 0.5)
            })

        # Draw corner accents
        corner_size = 150
        accent_color = self.colors["accent"]

        # Top-left
        self.canvas.create_polygon(
            0, 0, corner_size, 0, 0, corner_size,
            fill=accent_color, outline="", tags="decor"
        )

        # Top-right
        self.canvas.create_polygon(
            self.screen_width, 0,
            self.screen_width - corner_size, 0,
            self.screen_width, corner_size,
            fill=accent_color, outline="", tags="decor"
        )

        # Bottom-left
        self.canvas.create_polygon(
            0, self.screen_height,
            corner_size, self.screen_height,
            0, self.screen_height - corner_size,
            fill=accent_color, outline="", tags="decor"
        )

        # Bottom-right
        self.canvas.create_polygon(
            self.screen_width, self.screen_height,
            self.screen_width - corner_size, self.screen_height,
            self.screen_width, self.screen_height - corner_size,
            fill=accent_color, outline="", tags="decor"
        )

    def animate_background(self):
        """Animate the background gradient."""
        self.animation_offset = (self.animation_offset + 2) % self.screen_height
        self.draw_background()

        # Animate floating decorations
        for decor in self.decorations:
            decor['x'] += decor['speed_x']
            decor['y'] += decor['speed_y']

            # Bounce off edges
            if decor['x'] <= 0 or decor['x'] >= self.screen_width:
                decor['speed_x'] *= -1
            if decor['y'] <= 0 or decor['y'] >= self.screen_height:
                decor['speed_y'] *= -1

            self.canvas.coords(
                decor['id'],
                decor['x'] - decor['size'],
                decor['y'] - decor['size'],
                decor['x'] + decor['size'],
                decor['y'] + decor['size']
            )

        self.root.after(50, self.animate_background)

    def pulse_quote(self):
        """Create a subtle pulsing effect on the quote."""
        self.pulse_phase += 0.1
        scale = 1 + 0.02 * math.sin(self.pulse_phase)

        # Update font size for pulse effect
        new_size = int(self.calculate_font_size() * scale)
        self.quote_font.configure(size=new_size)

        self.root.after(100, self.pulse_quote)

    def update_timer(self):
        """Update the countdown timer."""
        if self.time_remaining > 0:
            self.time_remaining -= 1
            self.canvas.itemconfig(
                self.timer_label,
                text=f"Take a moment to reflect... ({self.time_remaining}s)"
            )
            self.root.after(1000, self.update_timer)
        else:
            self.can_exit = True
            self.canvas.itemconfig(
                self.timer_label,
                text="Press ESC or Q to close and start your day inspired!"
            )
            # Add a subtle glow effect to indicate ready
            self.canvas.itemconfig(self.timer_label, fill=self.colors["accent"])

    def try_exit(self, event=None):
        """Attempt to exit the application."""
        if self.can_exit:
            self.root.destroy()
            sys.exit(0)
        else:
            # Show a gentle reminder
            self.canvas.itemconfig(
                self.timer_label,
                text=f"Take a breath... ({self.time_remaining}s remaining)"
            )

    def interpolate_color(self, color1: str, color2: str, ratio: float) -> str:
        """Interpolate between two hex colors."""
        r1, g1, b1 = self.hex_to_rgb(color1)
        r2, g2, b2 = self.hex_to_rgb(color2)

        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)

        return f'#{r:02x}{g:02x}{b:02x}'

    def darken_color(self, color: str, amount: float) -> str:
        """Darken a hex color by a given amount."""
        r, g, b = self.hex_to_rgb(color)
        r = int(r * (1 - amount))
        g = int(g * (1 - amount))
        b = int(b * (1 - amount))
        return f'#{r:02x}{g:02x}{b:02x}'

    def adjust_alpha(self, color: str, alpha: float) -> str:
        """Simulate alpha by lightening/darkening toward background."""
        bg_r, bg_g, bg_b = self.hex_to_rgb(self.colors["bg"])
        fg_r, fg_g, fg_b = self.hex_to_rgb(color)

        r = int(bg_r + (fg_r - bg_r) * alpha)
        g = int(bg_g + (fg_g - bg_g) * alpha)
        b = int(bg_b + (fg_b - bg_b) * alpha)

        return f'#{r:02x}{g:02x}{b:02x}'

    def hex_to_rgb(self, color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        color = color.lstrip('#')
        return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    print("Starting Inspirational Quotes Display...")
    print("The display will remain for 30 seconds before you can close it.")
    print("Use this time to reflect on the quote and set your intention for the day!")

    app = InspirationApp()
    app.run()


if __name__ == "__main__":
    main()
