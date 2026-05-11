from custom_io.excel_io import _map_header_to_row_values


def test_map_header_to_row_values_returns_name_value_mapping():
    header = ("model", "radius", "strain")
    row = ("BEAM188", 0.25, 0.01)

    row_values = _map_header_to_row_values(header, row)

    assert row_values == {
        "model": "BEAM188",
        "radius": 0.25,
        "strain": 0.01,
    }


def test_map_header_to_row_values_rejects_length_mismatch():
    header = ("model", "radius")
    row = ("BEAM188",)

    try:
        _map_header_to_row_values(header, row)
    except ValueError as exc:
        assert "Header and row lengths do not match" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
