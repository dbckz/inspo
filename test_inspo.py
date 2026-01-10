#!/usr/bin/env python3
"""Tests for the Inspirational Quotes app."""

import pytest
from unittest.mock import patch, Mock

# Test quote_fetcher.py
from quote_fetcher import extract_doc_id, fetch_quotes_from_google_doc


class TestExtractDocId:
    """Tests for extract_doc_id function."""

    def test_standard_google_doc_url(self):
        url = "https://docs.google.com/document/d/1F2FAQaLeFcxIUGjhoszkBUqPajICy_99JBMhlgfJ_vM/edit"
        assert extract_doc_id(url) == "1F2FAQaLeFcxIUGjhoszkBUqPajICy_99JBMhlgfJ_vM"

    def test_google_doc_url_with_usp(self):
        url = "https://docs.google.com/document/d/abc123-_XYZ/edit?usp=sharing"
        assert extract_doc_id(url) == "abc123-_XYZ"

    def test_google_doc_url_with_id_param(self):
        url = "https://docs.google.com/document?id=abc123"
        assert extract_doc_id(url) == "abc123"

    def test_invalid_url_returns_none(self):
        url = "https://example.com/not-a-doc"
        assert extract_doc_id(url) is None

    def test_empty_url_returns_none(self):
        assert extract_doc_id("") is None


class TestFetchQuotes:
    """Tests for fetch_quotes_from_google_doc function."""

    @patch('quote_fetcher.requests.get')
    def test_successful_fetch(self, mock_get):
        mock_response = Mock()
        mock_response.text = "Quote one - Author\nQuote two - Author\n\nQuote three - Author"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        quotes = fetch_quotes_from_google_doc("https://docs.google.com/document/d/test123/edit")

        assert len(quotes) == 3
        assert "Quote one - Author" in quotes
        assert "Quote two - Author" in quotes
        assert "Quote three - Author" in quotes

    @patch('quote_fetcher.requests.get')
    def test_filters_short_lines(self, mock_get):
        mock_response = Mock()
        mock_response.text = "Short\nThis is a valid quote - Author\nNo"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        quotes = fetch_quotes_from_google_doc("https://docs.google.com/document/d/test123/edit")

        # Only the longer quote should be included (>5 chars)
        assert len(quotes) == 1
        assert "This is a valid quote - Author" in quotes

    @patch('quote_fetcher.requests.get')
    def test_network_error_returns_fallback(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        quotes = fetch_quotes_from_google_doc("https://docs.google.com/document/d/test123/edit")

        # Should return fallback quotes
        assert len(quotes) > 0
        assert "Steve Jobs" in quotes[0]  # First fallback quote mentions Steve Jobs

    def test_invalid_doc_id_returns_fallback(self):
        quotes = fetch_quotes_from_google_doc("https://example.com/not-a-doc")

        # Should return fallback quotes
        assert len(quotes) > 0


# Test inspo_app.py utility functions
class TestHexToRgba:
    """Tests for hex_to_rgba function."""

    def test_white(self):
        from inspo_app import hex_to_rgba
        result = hex_to_rgba("#FFFFFF")
        assert result == (1.0, 1.0, 1.0, 1.0)

    def test_black(self):
        from inspo_app import hex_to_rgba
        result = hex_to_rgba("#000000")
        assert result == (0.0, 0.0, 0.0, 1.0)

    def test_red(self):
        from inspo_app import hex_to_rgba
        result = hex_to_rgba("#FF0000")
        assert result == (1.0, 0.0, 0.0, 1.0)

    def test_with_alpha(self):
        from inspo_app import hex_to_rgba
        result = hex_to_rgba("#FF0000", alpha=0.5)
        assert result == (1.0, 0.0, 0.0, 0.5)

    def test_without_hash(self):
        from inspo_app import hex_to_rgba
        result = hex_to_rgba("FF6B6B")
        assert result[0] == 1.0
        assert 0.4 < result[1] < 0.5  # 6B/255 ≈ 0.42


class TestParseQuote:
    """Tests for quote parsing in InspirationAppMacOS."""

    def test_parse_quote_with_dash(self):
        # Import the class and test parse_quote method
        from inspo_app import InspirationAppMacOS
        # Create a mock instance to test the method
        app = object.__new__(InspirationAppMacOS)

        quote_text, author = app.parse_quote("The only way to do great work is to love what you do. - Steve Jobs")
        assert quote_text == "The only way to do great work is to love what you do."
        assert author == "Steve Jobs"

    def test_parse_quote_with_em_dash(self):
        from inspo_app import InspirationAppMacOS
        app = object.__new__(InspirationAppMacOS)

        quote_text, author = app.parse_quote("Be the change — Gandhi")
        assert quote_text == "Be the change"
        assert author == "Gandhi"

    def test_parse_quote_with_en_dash(self):
        from inspo_app import InspirationAppMacOS
        app = object.__new__(InspirationAppMacOS)

        quote_text, author = app.parse_quote("Stay hungry, stay foolish – Steve Jobs")
        assert quote_text == "Stay hungry, stay foolish"
        assert author == "Steve Jobs"

    def test_parse_quote_with_tilde(self):
        from inspo_app import InspirationAppMacOS
        app = object.__new__(InspirationAppMacOS)

        quote_text, author = app.parse_quote("Just do it ~ Nike")
        assert quote_text == "Just do it"
        assert author == "Nike"

    def test_parse_quote_without_author(self):
        from inspo_app import InspirationAppMacOS
        app = object.__new__(InspirationAppMacOS)

        quote_text, author = app.parse_quote("This is just a quote without attribution")
        assert quote_text == "This is just a quote without attribution"
        assert author == ""

    def test_parse_quote_strips_quotes(self):
        from inspo_app import InspirationAppMacOS
        app = object.__new__(InspirationAppMacOS)

        quote_text, author = app.parse_quote('"Quoted text" - Author')
        assert quote_text == "Quoted text"
        assert author == "Author"


class TestVideoCallDetection:
    """Tests for video call detection in inspo_app.py."""

    def test_meeting_keywords_exist(self):
        """Verify meeting keywords are defined."""
        from inspo_app import is_in_video_call
        # Just verify the function exists and is callable
        assert callable(is_in_video_call)

    @patch('inspo_app.get_meeting_window_titles')
    def test_detects_google_meet(self, mock_titles):
        from inspo_app import is_in_video_call
        mock_titles.return_value = ["Chrome: Meet - abc-defg-hij"]

        in_call, reason = is_in_video_call()
        assert in_call is True
        assert "meeting window" in reason.lower()

    @patch('inspo_app.get_meeting_window_titles')
    def test_detects_zoom(self, mock_titles):
        from inspo_app import is_in_video_call
        mock_titles.return_value = ["Zoom Meeting"]

        in_call, reason = is_in_video_call()
        assert in_call is True

    @patch('inspo_app.get_meeting_window_titles')
    @patch('inspo_app.is_camera_in_use')
    def test_no_call_detected(self, mock_camera, mock_titles):
        from inspo_app import is_in_video_call
        mock_titles.return_value = ["Terminal", "VS Code"]
        mock_camera.return_value = False

        in_call, reason = is_in_video_call()
        assert in_call is False
        assert reason == ""


class TestLockFile:
    """Tests for lock file management."""

    def test_acquire_and_release_lock(self):
        from inspo_app import acquire_lock, release_lock, LOCK_FILE
        import os

        # Clean up any existing lock
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

        # Should be able to acquire lock
        assert acquire_lock("test") is True
        assert os.path.exists(LOCK_FILE)

        # Should not be able to acquire again
        assert acquire_lock("test") is False

        # Release and verify we can acquire again
        release_lock()
        assert acquire_lock("test") is True

        # Clean up
        release_lock()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
