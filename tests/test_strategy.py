# tests/test_strategy.py
from analysis.strategies import PTModel
from tests.generators import generate_market_data


def test_strategy_process():

    market_data = generate_market_data()

    pt_model = PTModel(
        model_type="EVA",
        plot=False,
    )

    processed, clean_history = pt_model.process(market_data=market_data)

    assert processed is not None
    assert clean_history is not None

    assert processed.volume >= 0


def test_strategy_decide():

    market_data = generate_market_data()

    pt_model = PTModel(
        model_type="EVA",
        plot=False,
    )

    processed, _ = pt_model.process(market_data=market_data)

    result = pt_model.decide(
        processed=processed,
        market_data=market_data,
    )

    if result is not None:
        price, amount = result
        if price is not None:
            assert price > 0
        if amount is not None:
            assert amount > 0


def test_strategy_randomized():

    pt_model = PTModel(
        model_type="EVA",
        plot=False,
    )

    for _ in range(100):
        market_data = generate_market_data()

        processed, _ = pt_model.process(market_data=market_data)

        _ = pt_model.decide(processed=processed, market_data=market_data)

        assert processed is not None
