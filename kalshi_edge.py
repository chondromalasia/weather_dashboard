def calculate_kalshi_edge(forecast, error_histogram, kalshi_markets):
    """
    For each Kalshi bucket, compute the model's implied probability and edge vs the market.

    forecast: float - today's forecast high
    error_histogram: list of dicts with 'Error (°F)' and 'Percentage' (bias = forecast - actual)
    kalshi_markets: list of dicts with floor_strike, cap_strike, yes_bid, yes_ask, subtitle
    """
    # Build {actual_temp: probability} from bias distribution (bias = forecast - actual)
    forecast_probs = {}
    for row in error_histogram:
        bias = row['Error (°F)']
        if bias is None:
            continue
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

        market_yes = market.get('yes_bid') or 0
        market_no = 100 - (market.get('yes_ask') or 100)
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
