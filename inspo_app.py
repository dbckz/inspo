#!/usr/bin/env python3
"""
Inspirational Quotes Display App

A fullscreen app that displays inspirational quotes from a Google Doc
with vibrant colors. Can only be exited after 30 seconds.

Uses PyObjC for native macOS support (no Tcl/Tk dependency).
"""

import random
import math
import sys
import platform
import argparse

from config import (
    COLOR_SCHEMES,
    EXIT_DELAY_SECONDS,
    QUOTE_FONT_SIZE,
    AUTHOR_FONT_SIZE,
)
from quote_fetcher import fetch_quotes_from_google_doc

# Global override for delay (set via command line)
_delay_override = None


def hex_to_rgba(hex_color: str, alpha: float = 1.0):
    """Convert hex color to RGBA tuple (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b, alpha)


# Check platform and use appropriate implementation
if platform.system() == "Darwin":
    # macOS: Use PyObjC
    try:
        import objc
        from Cocoa import (
            NSApplication, NSApp, NSWindow, NSView,
            NSBackingStoreBuffered, NSWindowStyleMaskBorderless,
            NSWindowCollectionBehaviorFullScreenPrimary,
            NSWindowCollectionBehaviorStationary,
            NSScreen, NSColor, NSFont, NSFontWeightBold,
            NSMutableParagraphStyle, NSTextAlignmentCenter,
            NSMakeRect, NSAttributedString, NSTimer,
            NSForegroundColorAttributeName, NSFontAttributeName,
            NSParagraphStyleAttributeName, NSRunLoop,
            NSDefaultRunLoopMode, NSApplicationActivationPolicyRegular,
            NSBezierPath,
        )
        from Quartz import CGMainDisplayID
        USE_PYOBJC = True
    except ImportError:
        USE_PYOBJC = False
        print("PyObjC not available, falling back to tkinter")
else:
    USE_PYOBJC = False


class QuoteView(NSView):
    """Custom NSView for displaying the quote with animations."""

    def initWithFrame_colors_quote_author_(self, frame, colors, quote, author):
        self = objc.super(QuoteView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.colors = colors
        self.quote_text = quote
        self.author = author
        self.time_remaining = _delay_override if _delay_override is not None else EXIT_DELAY_SECONDS
        self.can_exit = False
        self.animation_offset = 0
        self.pulse_phase = 0.0

        # Floating decoration positions
        self.decorations = []
        for _ in range(15):
            self.decorations.append({
                'x': random.uniform(0, frame.size.width),
                'y': random.uniform(0, frame.size.height),
                'size': random.uniform(20, 100),
                'speed_x': random.uniform(-0.5, 0.5),
                'speed_y': random.uniform(-0.5, 0.5),
            })

        return self

    def drawRect_(self, rect):
        """Draw the view content."""
        bounds = self.bounds()
        width = bounds.size.width
        height = bounds.size.height

        # Draw gradient background
        bg_color = hex_to_rgba(self.colors["bg"])
        dark_color = self._darken_color(bg_color, 0.3)

        for i in range(0, int(height), 4):
            ratio = ((i + self.animation_offset) % int(height)) / height
            r = bg_color[0] + (dark_color[0] - bg_color[0]) * ratio
            g = bg_color[1] + (dark_color[1] - bg_color[1]) * ratio
            b = bg_color[2] + (dark_color[2] - bg_color[2]) * ratio

            color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)
            color.setFill()
            NSBezierPath.fillRect_(NSMakeRect(0, height - i - 4, width, 4))

        # Draw corner accents
        accent = hex_to_rgba(self.colors["accent"])
        accent_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(*accent)
        accent_color.setFill()

        corner_size = 150

        # Top-left corner
        path = NSBezierPath.bezierPath()
        path.moveToPoint_((0, height))
        path.lineToPoint_((corner_size, height))
        path.lineToPoint_((0, height - corner_size))
        path.closePath()
        path.fill()

        # Top-right corner
        path = NSBezierPath.bezierPath()
        path.moveToPoint_((width, height))
        path.lineToPoint_((width - corner_size, height))
        path.lineToPoint_((width, height - corner_size))
        path.closePath()
        path.fill()

        # Bottom-left corner
        path = NSBezierPath.bezierPath()
        path.moveToPoint_((0, 0))
        path.lineToPoint_((corner_size, 0))
        path.lineToPoint_((0, corner_size))
        path.closePath()
        path.fill()

        # Bottom-right corner
        path = NSBezierPath.bezierPath()
        path.moveToPoint_((width, 0))
        path.lineToPoint_((width - corner_size, 0))
        path.lineToPoint_((width, corner_size))
        path.closePath()
        path.fill()

        # Draw floating circles
        for decor in self.decorations:
            circle_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(
                accent[0], accent[1], accent[2], 0.2
            )
            circle_color.setStroke()

            circle = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(
                    decor['x'] - decor['size'],
                    decor['y'] - decor['size'],
                    decor['size'] * 2,
                    decor['size'] * 2
                )
            )
            circle.setLineWidth_(2)
            circle.stroke()

        # Draw quote text
        fg = hex_to_rgba(self.colors["fg"])
        fg_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(*fg)

        # Calculate font size based on quote length
        base_size = QUOTE_FONT_SIZE
        if len(self.quote_text) > 200:
            base_size -= 16
        elif len(self.quote_text) > 150:
            base_size -= 12
        elif len(self.quote_text) > 100:
            base_size -= 8
        elif len(self.quote_text) > 50:
            base_size -= 4

        # Apply pulse effect
        pulse_scale = 1 + 0.02 * math.sin(self.pulse_phase)
        font_size = int(base_size * pulse_scale)

        quote_font = NSFont.boldSystemFontOfSize_(font_size)

        paragraph = NSMutableParagraphStyle.alloc().init()
        paragraph.setAlignment_(NSTextAlignmentCenter)

        attrs = {
            NSForegroundColorAttributeName: fg_color,
            NSFontAttributeName: quote_font,
            NSParagraphStyleAttributeName: paragraph,
        }

        quote_str = NSAttributedString.alloc().initWithString_attributes_(
            f'"{self.quote_text}"', attrs
        )

        # Calculate text position
        text_size = quote_str.size()
        quote_rect = NSMakeRect(
            100,
            height / 2 - text_size.height / 2 + 50,
            width - 200,
            text_size.height + 100
        )
        quote_str.drawInRect_(quote_rect)

        # Draw author
        if self.author:
            author_font = NSFont.systemFontOfSize_(AUTHOR_FONT_SIZE)
            author_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(*accent)

            author_attrs = {
                NSForegroundColorAttributeName: author_color,
                NSFontAttributeName: author_font,
                NSParagraphStyleAttributeName: paragraph,
            }

            author_str = NSAttributedString.alloc().initWithString_attributes_(
                f"— {self.author}", author_attrs
            )

            author_size = author_str.size()
            author_rect = NSMakeRect(
                100,
                height / 2 - author_size.height - 100,
                width - 200,
                author_size.height + 20
            )
            author_str.drawInRect_(author_rect)

        # Draw timer text
        timer_font = NSFont.boldSystemFontOfSize_(24)

        if self.can_exit:
            timer_text = "Click anywhere or press any key to close"
            timer_color = author_color if self.author else fg_color
        else:
            timer_text = f"Take a moment to reflect... ({self.time_remaining}s)"
            timer_color = fg_color

        # Draw a close button hint when can exit
        if self.can_exit:
            # Draw a subtle "X" button in top-right corner
            close_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 0.6)
            close_color.setStroke()

            x_size = 20
            x_margin = 40
            path = NSBezierPath.bezierPath()
            path.moveToPoint_((width - x_margin - x_size, height - x_margin))
            path.lineToPoint_((width - x_margin, height - x_margin - x_size))
            path.moveToPoint_((width - x_margin, height - x_margin))
            path.lineToPoint_((width - x_margin - x_size, height - x_margin - x_size))
            path.setLineWidth_(3)
            path.stroke()

        timer_attrs = {
            NSForegroundColorAttributeName: timer_color,
            NSFontAttributeName: timer_font,
            NSParagraphStyleAttributeName: paragraph,
        }

        timer_str = NSAttributedString.alloc().initWithString_attributes_(
            timer_text, timer_attrs
        )

        timer_size = timer_str.size()
        timer_rect = NSMakeRect(
            100,
            60,
            width - 200,
            timer_size.height + 20
        )
        timer_str.drawInRect_(timer_rect)

    def _darken_color(self, color, amount):
        """Darken an RGBA color tuple."""
        return (
            color[0] * (1 - amount),
            color[1] * (1 - amount),
            color[2] * (1 - amount),
            color[3]
        )

    def animate_(self, timer):
        """Animation timer callback."""
        self.animation_offset = (self.animation_offset + 2) % int(self.bounds().size.height)
        self.pulse_phase += 0.1

        # Update decorations
        width = self.bounds().size.width
        height = self.bounds().size.height
        for decor in self.decorations:
            decor['x'] += decor['speed_x']
            decor['y'] += decor['speed_y']

            if decor['x'] <= 0 or decor['x'] >= width:
                decor['speed_x'] *= -1
            if decor['y'] <= 0 or decor['y'] >= height:
                decor['speed_y'] *= -1

        self.setNeedsDisplay_(True)

    def updateTimer_(self, timer):
        """Timer countdown callback."""
        if self.time_remaining > 0:
            self.time_remaining -= 1
            self.setNeedsDisplay_(True)
        else:
            self.can_exit = True
            self.setNeedsDisplay_(True)
            timer.invalidate()

    def acceptsFirstResponder(self):
        return True

    def keyDown_(self, event):
        """Handle key events."""
        if self.can_exit:
            # Any key closes after timer
            NSApp.terminate_(None)
        else:
            # Show reminder
            self.setNeedsDisplay_(True)

    def mouseDown_(self, event):
        """Handle mouse clicks."""
        if self.can_exit:
            NSApp.terminate_(None)


class InspirationAppMacOS:
    """Native macOS implementation using PyObjC."""

    def __init__(self):
        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

        # Select random color scheme
        self.colors = random.choice(COLOR_SCHEMES)

        # Fetch and select a quote
        quotes = fetch_quotes_from_google_doc()
        current_quote = random.choice(quotes)
        self.quote_text, self.author = self.parse_quote(current_quote)

        # Get screen size
        screen = NSScreen.mainScreen()
        frame = screen.frame()

        # Create fullscreen window
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )

        # Use a high but not extreme window level (floating window level + some)
        # This keeps it above normal windows but allows system UI to work
        self.window.setLevel_(8)  # NSModalPanelWindowLevel - above normal but not extreme
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorFullScreenPrimary
        )

        # Create custom view
        self.view = QuoteView.alloc().initWithFrame_colors_quote_author_(
            frame, self.colors, self.quote_text, self.author
        )

        self.window.setContentView_(self.view)
        self.window.makeFirstResponder_(self.view)

        # Start animation timer (20fps)
        self.anim_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self.view, objc.selector(QuoteView.animate_, signature=b'v@:@'), None, True
        )

        # Start countdown timer (1 second)
        self.countdown_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self.view, objc.selector(QuoteView.updateTimer_, signature=b'v@:@'), None, True
        )

    def parse_quote(self, quote: str) -> tuple:
        """Parse quote text and author from a quote string."""
        separators = [' - ', ' — ', ' – ', ' ~ ']

        for sep in separators:
            if sep in quote:
                parts = quote.rsplit(sep, 1)
                if len(parts) == 2:
                    quote_text = parts[0].strip().strip('"').strip("'")
                    author = parts[1].strip()
                    return quote_text, author

        return quote.strip().strip('"').strip("'"), ""

    def run(self):
        """Run the application."""
        self.window.makeKeyAndOrderFront_(None)
        self.app.activateIgnoringOtherApps_(True)
        self.app.run()


# Fallback to tkinter for non-macOS or if PyObjC unavailable
if not USE_PYOBJC:
    import tkinter as tk
    from tkinter import font as tkfont

    class InspirationAppTkinter:
        """Tkinter fallback implementation."""

        def __init__(self):
            self.root = tk.Tk()
            self.root.title("Daily Inspiration")

            self.colors = random.choice(COLOR_SCHEMES)
            self.screen_width = self.root.winfo_screenwidth()
            self.screen_height = self.root.winfo_screenheight()

            self.root.configure(bg=self.colors["bg"])
            self.root.attributes('-fullscreen', True)
            self.root.attributes('-topmost', True)

            self.root.protocol("WM_DELETE_WINDOW", self.try_exit)
            self.root.bind('<Escape>', self.try_exit)
            self.root.bind('<q>', self.try_exit)
            self.root.bind('<Q>', self.try_exit)

            self.time_remaining = _delay_override if _delay_override is not None else EXIT_DELAY_SECONDS
            self.can_exit = False
            self.animation_offset = 0
            self.pulse_phase = 0

            self.quotes = fetch_quotes_from_google_doc()
            self.current_quote = random.choice(self.quotes)
            self.quote_text, self.author = self.parse_quote(self.current_quote)

            self.setup_ui()
            self.animate_background()
            self.update_timer()
            self.pulse_quote()

        def parse_quote(self, quote: str) -> tuple:
            separators = [' - ', ' — ', ' – ', ' ~ ']
            for sep in separators:
                if sep in quote:
                    parts = quote.rsplit(sep, 1)
                    if len(parts) == 2:
                        return parts[0].strip().strip('"').strip("'"), parts[1].strip()
            return quote.strip().strip('"').strip("'"), ""

        def setup_ui(self):
            self.canvas = tk.Canvas(
                self.root, width=self.screen_width, height=self.screen_height,
                highlightthickness=0, bg=self.colors["bg"]
            )
            self.canvas.pack(fill=tk.BOTH, expand=True)

            self.quote_font = tkfont.Font(family="Helvetica", size=QUOTE_FONT_SIZE, weight="bold")
            self.author_font = tkfont.Font(family="Helvetica", size=AUTHOR_FONT_SIZE, slant="italic")
            self.timer_font = tkfont.Font(family="Helvetica", size=24, weight="bold")

            self.quote_label = self.canvas.create_text(
                self.screen_width // 2, self.screen_height // 2 - 50,
                text=f'"{self.quote_text}"', font=self.quote_font,
                fill=self.colors["fg"], justify=tk.CENTER, width=self.screen_width - 200
            )

            if self.author:
                self.author_label = self.canvas.create_text(
                    self.screen_width // 2, self.screen_height // 2 + 150,
                    text=f"— {self.author}", font=self.author_font,
                    fill=self.colors["accent"], justify=tk.CENTER
                )

            self.timer_label = self.canvas.create_text(
                self.screen_width // 2, self.screen_height - 80,
                text=f"Take a moment to reflect... ({self.time_remaining}s)",
                font=self.timer_font, fill=self.colors["fg"], justify=tk.CENTER
            )

        def animate_background(self):
            self.animation_offset = (self.animation_offset + 2) % self.screen_height
            self.root.after(50, self.animate_background)

        def pulse_quote(self):
            self.pulse_phase += 0.1
            scale = 1 + 0.02 * math.sin(self.pulse_phase)
            new_size = int(QUOTE_FONT_SIZE * scale)
            self.quote_font.configure(size=new_size)
            self.root.after(100, self.pulse_quote)

        def update_timer(self):
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
                self.canvas.itemconfig(self.timer_label, fill=self.colors["accent"])

        def try_exit(self, event=None):
            if self.can_exit:
                self.root.destroy()
                sys.exit(0)

        def run(self):
            self.root.mainloop()


def main():
    """Main entry point."""
    global _delay_override

    parser = argparse.ArgumentParser(description="Inspirational Quotes Display")
    parser.add_argument(
        "--delay", "-d",
        type=int,
        default=None,
        help=f"Override exit delay in seconds (default: {EXIT_DELAY_SECONDS})"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test mode with 5 second delay"
    )
    args = parser.parse_args()

    # Set delay override
    if args.test:
        _delay_override = 5
    elif args.delay is not None:
        _delay_override = args.delay

    delay = _delay_override if _delay_override is not None else EXIT_DELAY_SECONDS

    print("Starting Inspirational Quotes Display...")
    print(f"The display will remain for {delay} seconds before you can close it.")
    print("Use this time to reflect on the quote and set your intention for the day!")

    if USE_PYOBJC:
        print("Using native macOS (PyObjC) implementation...")
        app = InspirationAppMacOS()
    else:
        print("Using tkinter implementation...")
        app = InspirationAppTkinter()

    app.run()


if __name__ == "__main__":
    main()
