from restaurant_pricing.spiders import OloBaseSpider


class TheCheeseCakeFactorySpider(OloBaseSpider):
    name = "cheesecakefactory"
    domain = "https://order.thecheesecakefactory.com"
