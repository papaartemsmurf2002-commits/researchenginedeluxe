import pandas as pd

from tradingbot.indicators import adx, cci, ema, gaussian, rational_quadratic, rsi, wt


def test_indicator_outputs_are_series():
    df = pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 103, 105, 106, 108, 109, 110, 111, 112, 113, 114, 115],
            "high": [101, 102, 103, 104, 105, 104, 106, 107, 109, 110, 111, 112, 113, 114, 115, 116],
            "low": [99, 100, 101, 102, 103, 102, 104, 105, 107, 108, 109, 110, 111, 112, 113, 114],
            "close": [100, 101, 102, 103, 104, 103, 105, 106, 108, 109, 110, 111, 112, 113, 114, 115],
            "volume": [10] * 16,
        }
    )
    assert len(ema(df["close"], 5)) == len(df)
    assert len(rsi(df["close"], 5)) == len(df)
    assert len(cci(df["close"], 5)) == len(df)
    assert len(adx(df, 5)) == len(df)
    assert len(wt(df["close"], 5, 7)) == len(df)
    assert len(rational_quadratic(df["close"], 5, 8.0, 2)) == len(df)
    assert len(gaussian(df["close"], 5, 2)) == len(df)
