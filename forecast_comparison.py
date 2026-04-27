import pandas as pd
from datetime import datetime


def create_forecast_comparison_df(forecast_data, observation_data):
    """
    Create a pandas DataFrame comparing forecasted highs with observed highs.

    Args:
        forecast_data: Dict containing forecasted_highs array
        observation_data: Dict containing observations array

    Returns:
        pandas.DataFrame with columns: date, forecasted_high, observed_high, difference, abs_difference
    """

    # Parse forecast data
    forecast_records = []
    if forecast_data.get('forecasted_highs'):
        for item in forecast_data['forecasted_highs']:
            date_str = datetime.utcfromtimestamp(item['date']).strftime('%Y-%m-%d')
            forecast_records.append({
                'date': date_str,
                'forecasted_high': round(float(item['forecasted_high']))
            })

    forecast_df = pd.DataFrame(forecast_records)

    # Parse observation data
    observation_records = []
    if observation_data.get('observations'):
        for item in observation_data['observations']:
            date_str = datetime.utcfromtimestamp(item['timestamp']).strftime('%Y-%m-%d')
            observation_records.append({
                'date': date_str,
                'observed_high': round(float(item['value']))
            })

    observation_df = pd.DataFrame(observation_records)

    # Merge on date
    comparison_df = pd.merge(
        forecast_df,
        observation_df,
        on='date',
        how='inner'  # Only keep dates that have both forecast and observation
    )

    # Calculate difference (forecasted - observed) and absolute difference
    comparison_df['difference'] = comparison_df['forecasted_high'] - comparison_df['observed_high']
    comparison_df['abs_difference'] = comparison_df['difference'].abs()

    # Sort by date
    comparison_df = comparison_df.sort_values('date').reset_index(drop=True)

    return comparison_df


def error_histogram(df, bias=True):
    """Get a summary of the errors in a table of forecasts

    Parameters:
    df: Dataframe
        Data frame with fields "difference" or "abs_difference"
    bias: bool
        bias = use the actual real error, false = absolute difference
    """

    if bias:
        error_type = "difference"
    else:
        error_type = "abs_difference"

    error_summary = df[error_type].value_counts().sort_index()
    error_summary_pct = (error_summary / len(df) * 100).round(1)
    error_table = pd.DataFrame({
        'Error (°F)': error_summary.index,
        'Count': error_summary.values,
        'Percentage': error_summary_pct.values
    })
    return error_table


def calculate_kalshi_edge(forecast, error_df, kalshi_markets):
    """
    For each Kalshi bucket, compute the model's implied probability and edge vs the market.

    forecast: float - today's forecast high
    error_df: list of dicts with 'Error (°F)' and 'Percentage' (bias = forecast - actual)
    kalshi_markets: list of dicts with floor_strike, cap_strike, yes_bid, yes_ask, subtitle
    """
    # Build {actual_temp: probability} from bias distribution
    forecast_probs = {}
    for row in error_df:
        bias = row['Error (°F)']
        prob = row['Percentage'] / 100
        actual_temp = forecast - bias
        forecast_probs[actual_temp] = forecast_probs.get(actual_temp, 0) + prob

    results = []
    for market in kalshi_markets:
        floor = market.get('floor_strike')
        cap = market.get('cap_strike')

        model_prob = 0
        if floor is None:
            for temp, prob in forecast_probs.items():
                if temp < cap:
                    model_prob += prob
        elif cap is None:
            for temp, prob in forecast_probs.items():
                if temp > floor:
                    model_prob += prob
        else:
            for temp, prob in forecast_probs.items():
                if floor <= temp <= cap:
                    model_prob += prob

        market_yes = market.get('yes_bid', 0)
        market_no = 100 - market.get('yes_ask', 100)
        yes_edge = round(model_prob * 100 - market_yes, 1)
        no_edge = round((1 - model_prob) * 100 - market_no, 1)

        results.append({
            'subtitle': market.get('subtitle', ''),
            'floor': floor,
            'cap': cap,
            'model_prob': round(model_prob * 100, 1),
            'market_yes': market_yes,
            'market_no': market_no,
            'yes_edge': yes_edge,
            'no_edge': no_edge,
            'best_bet': 'YES' if yes_edge > no_edge else 'NO',
            'best_edge': round(max(yes_edge, no_edge), 1),
        })

    return results


def get_comparison_summary(comparison_df):
    """
    Get summary statistics for the forecast comparison.

    Args:
        comparison_df: DataFrame from create_forecast_comparison_df

    Returns:
        Dict with summary statistics including RMSE, mean error, MAE, etc.
    """
    if len(comparison_df) == 0:
        return {
            'count': 0,
            'message': 'No overlapping data between forecasts and observations'
        }

    # Calculate error metrics
    return {
        'count': len(comparison_df),
        'mean_error': float(comparison_df['difference'].mean()),
        'mean_absolute_error': float(comparison_df['abs_difference'].mean()),
        'rmse': float((comparison_df['difference'] ** 2).mean() ** 0.5),
        'max_error': float(comparison_df['difference'].max()),
        'min_error': float(comparison_df['difference'].min())
    }
