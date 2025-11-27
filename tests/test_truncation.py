"""Tests for response truncation functionality."""

import pytest

from ai_palindromikisa.benchmark import truncate_long_response


class TestTruncateLongResponse:
    """Tests for truncate_long_response function."""

    def test_short_response_not_truncated(self):
        """Short responses under threshold should not be truncated."""
        response = "short response"
        reference = "ref"
        result = truncate_long_response(response, reference)
        assert result == response

    def test_response_at_1000_chars_not_truncated(self):
        """Response exactly at 1000 chars with short reference is not truncated."""
        response = "a" * 1000
        reference = "short"  # 5 * 5 = 25, so threshold is max(1000, 25) = 1000
        result = truncate_long_response(response, reference)
        assert result == response

    def test_response_over_1000_chars_truncated(self):
        """Response over 1000 chars with short reference is truncated."""
        response = "a" * 1001
        reference = "short"  # threshold = 1000
        result = truncate_long_response(response, reference)

        assert len(result) < len(response)
        assert "...[" in result
        assert "chars truncated]..." in result
        assert result.startswith("a" * 200)
        assert result.endswith("a" * 200)

    def test_response_over_5x_reference_truncated(self):
        """Response over 5x reference length is truncated."""
        reference = "x" * 300  # threshold = max(1000, 5*300) = 1500
        response = "b" * 1501
        result = truncate_long_response(response, reference)

        assert len(result) < len(response)
        assert "...[" in result
        assert "chars truncated]..." in result

    def test_response_under_5x_reference_not_truncated(self):
        """Response under 5x reference length is not truncated."""
        reference = "x" * 300  # threshold = 1500
        response = "b" * 1500
        result = truncate_long_response(response, reference)
        assert result == response

    def test_truncation_format(self):
        """Verify exact truncation format."""
        response = "START" + "x" * 1000 + "END"
        reference = "short"  # threshold = 1000

        result = truncate_long_response(response, reference)

        # Response is 1008 chars, threshold is 1000
        # Truncated count should be 1008 - 200 - 200 = 608
        assert "[608 chars truncated]" in result

    def test_truncation_preserves_start_and_end(self):
        """Verify that 200 chars from start and end are preserved."""
        start_text = "S" * 200
        middle_text = "M" * 700
        end_text = "E" * 200
        response = start_text + middle_text + end_text  # 1100 chars
        reference = "short"  # threshold = 1000

        result = truncate_long_response(response, reference)

        assert result.startswith(start_text)
        assert result.endswith(end_text)
        assert "[700 chars truncated]" in result

    def test_truncation_with_long_reference(self):
        """Threshold should be 5x reference when reference > 200 chars."""
        reference = "r" * 250  # threshold = max(1000, 5*250) = 1250
        response = "a" * 1200  # under threshold
        result = truncate_long_response(response, reference)
        assert result == response  # not truncated

        response = "a" * 1251  # over threshold
        result = truncate_long_response(response, reference)
        assert "[851 chars truncated]" in result  # 1251 - 200 - 200 = 851

    def test_empty_response(self):
        """Empty response should not be truncated."""
        result = truncate_long_response("", "reference")
        assert result == ""

    def test_empty_reference(self):
        """Empty reference should use 1000 char threshold."""
        response = "a" * 1001
        result = truncate_long_response(response, "")
        assert "[601 chars truncated]" in result  # 1001 - 200 - 200 = 601

    @pytest.mark.parametrize(
        "response_len,reference_len,should_truncate",
        [
            (999, 10, False),  # under 1000
            (1000, 10, False),  # exactly 1000
            (1001, 10, True),  # over 1000
            (1499, 300, False),  # under 5*300=1500
            (1500, 300, False),  # exactly 5*300=1500
            (1501, 300, True),  # over 5*300=1500
        ],
    )
    def test_threshold_boundary_cases(
        self, response_len, reference_len, should_truncate
    ):
        """Test boundary cases around truncation threshold."""
        response = "x" * response_len
        reference = "r" * reference_len
        result = truncate_long_response(response, reference)

        if should_truncate:
            assert "chars truncated]" in result
        else:
            assert result == response
