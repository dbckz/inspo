#!/usr/bin/env python3
"""
Inspirational Quotes Display App

A fullscreen app that displays inspirational quotes from a Google Doc
with vibrant colors. Can only be exited after 30 seconds.

Also includes 20-20-20 eye break mode for eye health reminders.

Uses PyObjC for native macOS support (no Tcl/Tk dependency).
"""

import random
import re
import math
import sys
import platform
import argparse
import os
import tempfile
import time

from config import (
    COLOR_SCHEMES,
    EXIT_DELAY_SECONDS,
    QUOTE_FONT_SIZE,
    AUTHOR_FONT_SIZE,
)
from quote_fetcher import fetch_quotes_from_google_doc

# Global override for delay (set via command line)
_delay_override = None

# Lock file for coordination between quote and eye break displays
LOCK_FILE = os.path.join(tempfile.gettempdir(), "inspo_display.lock")


def acquire_lock(mode: str) -> bool:
    """Try to acquire the display lock. Returns True if successful."""
    try:
        # Check if lock file exists and is recent (within 2 minutes)
        if os.path.exists(LOCK_FILE):
            mtime = os.path.getmtime(LOCK_FILE)
            if time.time() - mtime < 120:  # Lock is still valid
                return False
        # Create lock file
        with open(LOCK_FILE, 'w') as f:
            f.write(f"{mode}:{os.getpid()}")
        return True
    except Exception:
        return False


def release_lock():
    """Release the display lock."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


def is_camera_in_use() -> bool:
    """Check if the camera is currently in use on macOS."""
    import subprocess
    try:
        # On modern macOS (Monterey+), check if the camera indicator is on
        # by looking for apps that have camera entitlements active
        # Method 1: Check for camera-using processes via log stream
        result = subprocess.run(
            ["bash", "-c", "log show --predicate 'subsystem == \"com.apple.cmio\" AND eventMessage CONTAINS \"Start\"' --last 30s 2>/dev/null | grep -c Start"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            count = result.stdout.strip()
            if count and int(count) > 0:
                return True
    except Exception:
        pass

    return False


def get_meeting_window_titles() -> list:
    """Get window titles that might indicate a video call is in progress."""
    import subprocess
    try:
        # Use AppleScript to get all window titles with process names
        # Output each on a separate line to avoid comma-parsing issues
        script = '''
        tell application "System Events"
            set output to ""
            repeat with proc in (every process whose background only is false)
                try
                    set processName to name of proc
                    repeat with win in (every window of proc)
                        try
                            set windowName to name of win
                            set output to output & processName & ": " & windowName & linefeed
                        end try
                    end repeat
                end try
            end repeat
            return output
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except Exception:
        pass
    return []


def is_in_video_call() -> tuple[bool, str]:
    """
    Check if user is currently in a video call.
    Returns (is_in_call, reason) tuple.
    """
    # Check 1: Meeting window titles (most reliable)
    meeting_keywords = [
        # Google Meet - various dash characters and formats
        "meet.google.com", "Google Meet",
        # Zoom
        "Zoom Meeting", "zoom.us", "Zoom Webinar",
        # Microsoft Teams
        "Microsoft Teams", "Teams |", "| Teams",
        # Generic indicators
        "Screen Share", "Sharing your screen",
        # Camera/microphone recording indicator (shows in browser title)
        "Camera and microphone recording",
        "microphone recording",
        # Slack huddles
        "Huddle",
        # Discord (only when in voice)
        "Voice Connected",
        # FaceTime
        "FaceTime",
        # WebEx
        "Webex",
    ]

    # Also check for "Meet" followed by any dash variant and a meeting code
    # Meeting codes are typically like "xxx-xxxx-xxx"
    meet_pattern = re.compile(r"Meet\s*[-–—]\s*[a-z]{3}-[a-z]{4}-[a-z]{3}", re.IGNORECASE)

    window_titles = get_meeting_window_titles()
    for title in window_titles:
        # Check regex pattern for Google Meet
        if meet_pattern.search(title):
            return True, f"meeting window detected: '{title[:50]}'"
        # Check keywords
        for keyword in meeting_keywords:
            if keyword.lower() in title.lower():
                return True, f"meeting window detected: '{title[:50]}'"

    # Check 2: Camera in use (fallback, less reliable)
    if is_camera_in_use():
        return True, "camera is in use"

    return False, ""


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
            NSMakeRect, NSMakeSize, NSAttributedString, NSTimer,
            NSForegroundColorAttributeName, NSFontAttributeName,
            NSParagraphStyleAttributeName, NSRunLoop,
            NSDefaultRunLoopMode, NSApplicationActivationPolicyRegular,
            NSBezierPath, NSSound, NSStringDrawingUsesLineFragmentOrigin,
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
        self.initial_delay = self.time_remaining  # Store for animation sync
        self.can_exit = False
        self.animation_offset = 0

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

        # Draw gradient with animated sweep line
        for i in range(0, int(height), 4):
            # Calculate if this line is above or below the sweep position
            sweep_y = self.animation_offset
            if i < sweep_y:
                # Above sweep - use lighter color (already "swept")
                ratio = 0.3
            else:
                # Below sweep - use darker gradient
                ratio = 0.7 + 0.3 * (i - sweep_y) / max(height - sweep_y, 1)

            r = bg_color[0] * (1 - ratio * 0.3)
            g = bg_color[1] * (1 - ratio * 0.3)
            b = bg_color[2] * (1 - ratio * 0.3)

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

        # Calculate font size based on quote length (reduce for longer quotes)
        quote_length = len(self.quote_text)
        font_size_reductions = [(200, 16), (150, 12), (100, 8), (50, 4)]
        base_size = QUOTE_FONT_SIZE
        for threshold, reduction in font_size_reductions:
            if quote_length > threshold:
                base_size -= reduction
                break

        quote_font = NSFont.boldSystemFontOfSize_(base_size)

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

        # Calculate text position with proper wrapping support
        text_width = width - 200
        # Use boundingRectWithSize to get actual height when text wraps
        bounding_rect = quote_str.boundingRectWithSize_options_(
            NSMakeSize(text_width, height),  # Max size constraint
            NSStringDrawingUsesLineFragmentOrigin  # Enable multi-line layout
        )
        text_height = bounding_rect.size.height

        quote_rect = NSMakeRect(
            100,
            height / 2 - text_height / 2 + 50,
            text_width,
            text_height + 20
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
            # Position author below the quote (quote_rect.origin.y is the bottom of the quote)
            quote_bottom_y = height / 2 - text_height / 2 + 50
            author_rect = NSMakeRect(
                100,
                quote_bottom_y - author_size.height - 30,
                text_width,
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

    def animate_(self, timer):
        """Animation timer callback."""
        height = int(self.bounds().size.height)

        # Calculate animation speed so the line reaches top exactly when timer ends
        # Animation runs at 20fps (0.05s interval), so total frames = initial_delay * 20
        total_frames = self.initial_delay * 20
        if total_frames > 0:
            increment = height / total_frames
        else:
            increment = 2  # Fallback

        self.animation_offset = min(self.animation_offset + increment, height)

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

    # TODO: fix pressing key not working to exit quote screen
    def keyDown_(self, event):
        """Handle key events - consume all keys to prevent system beep."""
        if self.can_exit:
            # Any key closes after timer
            NSApp.terminate_(None)
        # Don't call super or interpretKeyEvents_ - just consume the event silently

    def performKeyEquivalent_(self, event):
        """Handle key equivalents to prevent system beep."""
        if self.can_exit:
            NSApp.terminate_(None)
            return True
        return True  # Return True to indicate we handled it (prevents beep)

    def mouseDown_(self, event):
        """Handle mouse clicks."""
        if self.can_exit:
            NSApp.terminate_(None)


class KeyableWindow(NSWindow):
    """Custom NSWindow subclass that can become key window even when borderless."""

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return True


# Classic BSOD color scheme for eye break
BSOD_COLORS = {
    "bg": "#0000AA",      # Classic DOS/Windows blue
    "fg": "#FFFFFF",       # White text
}


class EyeBreakView(NSView):
    """Custom NSView for displaying the 20-20-20 eye break screen."""

    def initWithFrame_(self, frame):
        self = objc.super(EyeBreakView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.colors = BSOD_COLORS

        # State machine: countdown -> timer -> done
        self.phase = "countdown"  # countdown, timer, done
        self.countdown_value = 5  # 5,4,3,2,1
        self.timer_value = 20     # 20 second timer

        return self

    def drawRect_(self, rect):
        """Draw the view content."""
        bounds = self.bounds()
        width = bounds.size.width
        height = bounds.size.height

        # Draw solid classic BSOD blue background
        bg_color = hex_to_rgba(self.colors["bg"])
        ns_bg = NSColor.colorWithCalibratedRed_green_blue_alpha_(*bg_color)
        ns_bg.setFill()
        NSBezierPath.fillRect_(bounds)

        # Draw text based on phase
        fg = hex_to_rgba(self.colors["fg"])
        fg_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(*fg)

        paragraph = NSMutableParagraphStyle.alloc().init()
        paragraph.setAlignment_(NSTextAlignmentCenter)

        if self.phase == "countdown":
            self._draw_countdown_phase(width, height, fg_color, paragraph)
        elif self.phase == "timer":
            self._draw_timer_phase(width, height, fg_color, paragraph)
        elif self.phase == "done":
            self._draw_done_phase(width, height, fg_color, paragraph)

    def _draw_title_bar(self, width, height, text):
        """Draw the classic Windows 9X style title bar with inverted colors."""
        fg = hex_to_rgba(self.colors["fg"])
        bg = hex_to_rgba(self.colors["bg"])

        # White background bar
        white_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(*fg)
        white_color.setFill()
        bar_height = 32
        bar_y = height - 180
        NSBezierPath.fillRect_(NSMakeRect(width/2 - 200, bar_y, 400, bar_height))

        # Blue text on white bar
        blue_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(*bg)
        title_font = NSFont.fontWithName_size_("Menlo", 18) or NSFont.monospacedSystemFontOfSize_weight_(18, 0.0)
        para = NSMutableParagraphStyle.alloc().init()
        para.setAlignment_(NSTextAlignmentCenter)
        title_attrs = {
            NSForegroundColorAttributeName: blue_color,
            NSFontAttributeName: title_font,
            NSParagraphStyleAttributeName: para,
        }
        title_str = NSAttributedString.alloc().initWithString_attributes_(text, title_attrs)
        title_rect = NSMakeRect(width/2 - 200, bar_y + 1, 400, bar_height)
        title_str.drawInRect_(title_rect)

    def _draw_phase_content(self, width, height, fg_color, paragraph, lines):
        """Draw phase content with BSOD-style layout."""
        self._draw_title_bar(width, height, "Eye Break")

        mono_font = NSFont.fontWithName_size_("Menlo", 20) or NSFont.monospacedSystemFontOfSize_weight_(20, 0.0)
        content_y = height / 2 + 100
        line_height = 36
        margin = width / 4

        attrs = {
            NSForegroundColorAttributeName: fg_color,
            NSFontAttributeName: mono_font,
            NSParagraphStyleAttributeName: paragraph,
        }

        for i, line in enumerate(lines):
            line_str = NSAttributedString.alloc().initWithString_attributes_(line, attrs)
            line_rect = NSMakeRect(margin, content_y - i * line_height, width - margin * 2, line_height)
            line_str.drawInRect_(line_rect)

    def _draw_countdown_phase(self, width, height, fg_color, paragraph):
        """Draw the countdown phase (5,4,3,2,1)."""
        lines = [
            "An eye strain condition has been detected.",
            "",
            "To protect your vision, look at something",
            "20 metres away for 20 seconds.",
            "",
            f"*  Starting in {self.countdown_value} seconds...",
            "",
            "",
            "Press any key to continue _"
        ]
        self._draw_phase_content(width, height, fg_color, paragraph, lines)

    def _draw_timer_phase(self, width, height, fg_color, paragraph):
        """Draw the timer phase (20 second countdown)."""
        lines = [
            "An eye strain condition has been detected.",
            "",
            "Look at something 20 metres away now.",
            "",
            f"*  Time remaining: {self.timer_value} seconds",
            "",
            "",
            "",
            "Please wait _"
        ]
        self._draw_phase_content(width, height, fg_color, paragraph, lines)

    def _draw_done_phase(self, width, height, fg_color, paragraph):
        """Draw the done phase."""
        lines = [
            "Eye strain prevention complete.",
            "",
            "Your eyes have been successfully rested.",
            "",
            "*  Operation completed successfully.",
            "",
            "",
            "",
            "Resuming normal operation..."
        ]
        self._draw_phase_content(width, height, fg_color, paragraph, lines)

    def updateCountdown_(self, timer):
        """Handle countdown phase (5,4,3,2,1)."""
        if self.phase != "countdown":
            return

        if self.countdown_value > 1:
            self.countdown_value -= 1
            self.setNeedsDisplay_(True)
        else:
            # Transition to timer phase
            self.phase = "timer"
            timer.invalidate()
            self.setNeedsDisplay_(True)
            # Play start ding
            self._play_ding()
            # Start the 20-second timer
            self._start_main_timer()

    def _start_main_timer(self):
        """Start the 20-second timer phase."""
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self, objc.selector(EyeBreakView.updateMainTimer_, signature=b'v@:@'), None, True
        )

    def updateMainTimer_(self, timer):
        """Handle main timer phase (20 seconds)."""
        if self.phase != "timer":
            return

        if self.timer_value > 1:
            self.timer_value -= 1
            self.setNeedsDisplay_(True)
        else:
            # Transition to done phase
            self.phase = "done"
            timer.invalidate()
            self.setNeedsDisplay_(True)
            # Play end ding
            self._play_ding()
            # Start close timer
            self._start_close_timer()

    def _start_close_timer(self):
        """Start the close timer (1 second pause)."""
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self, objc.selector(EyeBreakView.closeApp_, signature=b'v@:@'), None, False
        )

    def closeApp_(self, timer):
        """Close the application."""
        release_lock()
        NSApp.terminate_(None)

    def _play_ding(self):
        """Play a quiet ding sound."""
        sound = NSSound.soundNamed_("Glass")
        if sound:
            sound.setVolume_(0.3)
            sound.play()

    def acceptsFirstResponder(self):
        return True

    def keyDown_(self, event):
        """Consume key events to prevent beep."""
        pass

    def performKeyEquivalent_(self, event):
        """Handle key equivalents to prevent system beep."""
        return True

    def mouseDown_(self, event):
        """Consume mouse events."""
        pass


class EyeBreakAppMacOS:
    """Native macOS implementation for eye break screen."""

    def __init__(self):
        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

        # Get screen size
        screen = NSScreen.mainScreen()
        frame = screen.frame()

        # Create fullscreen window
        self.window = KeyableWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )

        # High window level (same as quote display)
        self.window.setLevel_(8)
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorFullScreenPrimary
        )

        # Create custom view
        self.view = EyeBreakView.alloc().initWithFrame_(frame)

        self.window.setContentView_(self.view)
        self.window.makeFirstResponder_(self.view)

        # Start countdown timer
        self.countdown_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self.view, objc.selector(EyeBreakView.updateCountdown_, signature=b'v@:@'), None, True
        )

    def run(self):
        """Run the application."""
        self.window.makeKeyAndOrderFront_(None)
        self.app.activateIgnoringOtherApps_(True)
        self.app.run()


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

        # Create fullscreen window (use custom class that accepts keyboard input)
        self.window = KeyableWindow.alloc().initWithContentRect_styleMask_backing_defer_(
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
    parser.add_argument(
        "--eye-break",
        action="store_true",
        help="Show 20-20-20 eye break screen instead of quote"
    )
    args = parser.parse_args()

    # Set delay override
    if args.test:
        _delay_override = 5
    elif args.delay is not None:
        _delay_override = args.delay

    # Determine mode
    mode = "eye_break" if args.eye_break else "quote"

    # Try to acquire lock (prevents clash between quote and eye break)
    if not acquire_lock(mode):
        print(f"Another display is currently showing, skipping {mode}")
        sys.exit(0)

    # Check if user is in a video call - skip if so
    in_call, reason = is_in_video_call()
    if in_call:
        print(f"Skipping {mode}: {reason}")
        release_lock()
        sys.exit(0)

    try:
        if args.eye_break:
            # Eye break mode
            print("Starting 20-20-20 Eye Break...")
            if USE_PYOBJC:
                app = EyeBreakAppMacOS()
            else:
                print("Eye break mode requires macOS with PyObjC")
                release_lock()
                sys.exit(1)
        else:
            # Quote display mode
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
    finally:
        release_lock()


if __name__ == "__main__":
    main()
