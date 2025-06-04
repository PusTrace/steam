class BaseStrategy:
    def init(self, *args, **kwargs):
        raise NotImplementedError

    def predict(self, data):
        raise NotImplementedError


class EVA(BaseStrategy):
    def init(self, price, volume, approx_max, approx_min, skin_orders, linreg):
        self.price = price
        self.volume = volume
        self.approx_max = approx_max
        self.approx_min = approx_min
        self.orders = skin_orders
        self.linreg = linreg


    def predict(self):
        default_threshold_top = 86
        default_threshold_bottom = 70
        # linreg + or - (возможно не нужна так как предполагается что линейная регрессия уже заходит положительная)
        # fast check orders (для выкидывания мусорных предметов)
        # проверяем что разница в апроксимации больше чем 10 процентов и что цена на данный момент близка к approx_min а средняя цена выше чем данная и approx_min
        # Покупай, когда текущая цена близка или ниже approx_min — это “аномально дёшево”. (предмет на временном спаде)(спот)
        # добавляем в вес есть ли предмет в активном дропе или нет
        
        # ищем куда ставить предмет в стенку
        
        # timeless prediction logic
        y = self.price * 0.95  # Пример: просто уменьшаем цену на 5%
        
        # простенькое линейное предсказание
        predict_profit = self.linreg * y
        return y, predict_profit # чисто как пример



# в будущем можно будет попробовать создавать окна, тренировать на окнах модель и вычислять функцию потерь
# и на основе этого делать предсказания


# стратегии спотов и холдов можно сделать где в logs будет возращаться что это за предмет и если это спот то быстро убирать

class PTModel:
    def __init__(self, model_type: str):
        strategies = {
            "EVA": EVA
        }

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}")

        self.strategy = strategies[model_type]()

    def init(self, *args, **kwargs):
        self.strategy.init(*args, **kwargs)

    def predict(self, data):
        return self.strategy.predict(data)
