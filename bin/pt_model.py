class BaseStrategy:
    def predict(self, *args, **kwargs):
        raise NotImplementedError


class EVA(BaseStrategy):
    def predict(self, price, volume, approx_max, approx_min, skin_orders, linreg):
        default_threshold_top = 86
        default_threshold_bottom = 70

        # TODO: сюда можно вставить реальную логику предсказания

        y = price * 0.95  # Пример: просто уменьшаем цену на 5%
        predict_profit = linreg * y
        amount = 1

        return y, amount, predict_profit
    
    
class PTModel:
    def __init__(self, model_type: str):
        strategies = {
            "EVA": EVA
        }

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}")

        self.strategy = strategies[model_type]()

    def predict(self, price, volume, approx_max, approx_min, skin_orders, linreg):
        return self.strategy.predict(price, volume, approx_max, approx_min, skin_orders, linreg)
