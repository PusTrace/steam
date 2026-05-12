# tests/test_randomized.py
from analysis.strategies import PTModel
from tests.generators import generate_market_data


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
