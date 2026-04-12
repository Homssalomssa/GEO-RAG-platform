"""
Tests for the Vision Service.
Verifies JSON parsing and fallback extraction.
"""

import pytest
from services.vision_service import _parse_vision_output, _extract_field


class TestParseVisionOutput:
    """Test the vision output parser."""

    def test_valid_json(self):
        """Standard JSON output from model."""
        raw = '''{
            "vegetation_density": "low, approximately 10%",
            "building_density": "high, tightly packed",
            "road_density": "medium, mostly paved",
            "urban_pattern": "irregular layout",
            "expansion_signs": "new construction at edges",
            "illegal_settlement_indicators": "informal structures detected"
        }'''
        result = _parse_vision_output(raw)
        assert result["vegetation_density"] == "low, approximately 10%"
        assert result["building_density"] == "high, tightly packed"
        assert len(result) == 6

    def test_json_with_markdown_fences(self):
        """Model wraps JSON in ```json ... ```."""
        raw = '''```json
{
    "vegetation_density": "medium",
    "building_density": "low",
    "road_density": "high",
    "urban_pattern": "grid",
    "expansion_signs": "none",
    "illegal_settlement_indicators": "none"
}
```'''
        result = _parse_vision_output(raw)
        assert result["vegetation_density"] == "medium"
        assert result["urban_pattern"] == "grid"

    def test_missing_keys_default_to_not_detected(self):
        """Partial JSON still returns all 6 keys."""
        raw = '{"vegetation_density": "high", "building_density": "low"}'
        result = _parse_vision_output(raw)
        assert result["vegetation_density"] == "high"
        assert result["road_density"] == "not detected"
        assert len(result) == 6

    def test_invalid_json_fallback_extraction(self):
        """Unstructured text triggers regex fallback."""
        raw = '''
        vegetation_density: low coverage about 15%
        building_density: very high, informal
        road_density: mostly unpaved tracks
        urban_pattern: irregular sprawl
        expansion_signs: new buildings at south edge
        illegal_settlement_indicators: no grid, informal structures
        '''
        result = _parse_vision_output(raw)
        assert "15%" in result["vegetation_density"]
        assert "informal" in result["building_density"]


class TestExtractField:
    """Test individual field extraction from unstructured text."""

    def test_json_style_extraction(self):
        text = '"vegetation_density": "about 30% coverage"'
        assert "30%" in _extract_field(text, "vegetation_density")

    def test_plain_text_style(self):
        text = "building_density: high density with many structures"
        result = _extract_field(text, "building_density")
        assert "high density" in result

    def test_field_not_found(self):
        result = _extract_field("some random text", "vegetation_density")
        assert result == "extraction failed"
