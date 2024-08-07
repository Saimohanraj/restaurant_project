from restaurant_pricing.spiders import OloBaseSpider


class OutbackSpider(OloBaseSpider):
    name = "outback"
    domain = "https://order.outback.com"
