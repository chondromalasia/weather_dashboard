"""
Simple test to verify forecast comparison functionality is working.
Run with: python test_forecast_comparison.py
"""

from forecast_comparison import create_forecast_comparison_df, error_histogram, get_comparison_summary


def test_forecast_comparison():
    """Test that the forecast comparison functions work correctly."""

    # Mock forecast data
    forecast_data = {
        "forecasted_highs": [
            {"date": "2025-09-06", "forecasted_high": 85.0},
            {"date": "2025-09-07", "forecasted_high": 87.0},
            {"date": "2025-09-08", "forecasted_high": 83.0},
            {"date": "2025-09-09", "forecasted_high": 86.0},
            {"date": "2025-09-10", "forecasted_high": 88.0}
        ]
    }

    # Mock observation data
    observation_data = {
        "observations": [
            {"timestamp": 1757174160, "value": "84.0"},
            {"timestamp": 1757261700, "value": "86.0"},
            {"timestamp": 1757341800, "value": "82.0"},
            {"timestamp": 1757432700, "value": "87.0"},
            {"timestamp": 1757520000, "value": "89.0"}
        ]
    }

    print("Testing create_forecast_comparison_df...")
    df = create_forecast_comparison_df(forecast_data, observation_data)

    print(f"✓ DataFrame created successfully with {len(df)} rows")
    print(f"  Columns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())

    # Verify columns exist
    assert 'date' in df.columns, "Missing 'date' column"
    assert 'forecasted_high' in df.columns, "Missing 'forecasted_high' column"
    assert 'observed_high' in df.columns, "Missing 'observed_high' column"
    assert 'difference' in df.columns, "Missing 'difference' column"
    assert 'abs_difference' in df.columns, "Missing 'abs_difference' column"
    print("\n✓ All required columns present")

    # Verify row count
    assert len(df) == 5, f"Expected 5 rows, got {len(df)}"
    print("✓ Correct number of rows")

    print("\nTesting get_comparison_summary...")
    summary = get_comparison_summary(df)

    print(f"✓ Summary calculated successfully:")
    print(f"  Count: {summary['count']}")
    print(f"  Mean Error: {summary['mean_error']:.2f}°F")
    print(f"  MAE: {summary['mean_absolute_error']:.2f}°F")
    print(f"  RMSE: {summary['rmse']:.2f}°F")
    print(f"  Max Error: {summary['max_error']:.2f}°F")
    print(f"  Min Error: {summary['min_error']:.2f}°F")

    # Verify summary has required keys
    assert 'count' in summary, "Missing 'count' in summary"
    assert 'mean_error' in summary, "Missing 'mean_error' in summary"
    assert 'mean_absolute_error' in summary, "Missing 'mean_absolute_error' in summary"
    assert 'rmse' in summary, "Missing 'rmse' in summary"
    print("\n✓ All summary statistics present")

    print("\nTesting error_histogram...")
    histogram = error_histogram(df, bias=True)

    print(f"✓ Error histogram created successfully with {len(histogram)} unique error values")
    print(f"\nError Distribution:")
    print(histogram.to_string(index=False))

    # Verify histogram structure
    assert 'Error (°F)' in histogram.columns, "Missing 'Error (°F)' column in histogram"
    assert 'Count' in histogram.columns, "Missing 'Count' column in histogram"
    assert 'Percentage' in histogram.columns, "Missing 'Percentage' column in histogram"
    print("\n✓ Histogram has correct structure")

    print("\n" + "="*50)
    print("ALL TESTS PASSED! ✓")
    print("="*50)


if __name__ == "__main__":
    try:
        test_forecast_comparison()
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
