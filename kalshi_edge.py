def _make_subtitle(floor, cap):
    if floor is None and cap is not None:
        return f"{int(cap)}° or below"
    if cap is None and floor is not None:
        return f"{int(floor)}° or above"
    if floor is not None and cap is not None:
        return f"{int(floor)}° to {int(cap)}°"
    return ""


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
        prob = float(row['Percentage']) / 100
        actual_temp = forecast - float(bias)
        forecast_probs[actual_temp] = forecast_probs.get(actual_temp, 0) + prob

    results = []
    for market in kalshi_markets:
        floor = float(market['floor_strike']) if market.get('floor_strike') is not None else None
        cap = float(market['cap_strike']) if market.get('cap_strike') is not None else None

        # Kalshi buckets: cap_strike and floor_strike are inclusive bounds.
        # e.g. "58° to 59°" has floor=58, cap=59; "57° or below" has cap=57; "66° or above" has floor=66.
        model_prob = 0
        if floor is None:
            for temp, prob in forecast_probs.items():
                if temp <= cap:
                    model_prob += prob
        elif cap is None:
            for temp, prob in forecast_probs.items():
                if temp >= floor:
                    model_prob += prob
        else:
            for temp, prob in forecast_probs.items():
                if floor <= temp <= cap:
                    model_prob += prob

        market_yes = round(float(market.get('yes_bid') or 0) * 100, 1)
        market_no = round(100 - float(market.get('yes_ask') or 1) * 100, 1)
        yes_edge = round(model_prob * 100 - market_yes, 1)
        no_edge = round((1 - model_prob) * 100 - market_no, 1)

        subtitle = market.get('subtitle') or _make_subtitle(floor, cap)
        results.append({
            'subtitle': subtitle,
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
