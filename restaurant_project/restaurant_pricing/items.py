# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from urllib.parse import urldefrag
import scrapy
from scrapy.http.request.form import _urlencode


class RestaurantPricingItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class RestaurantItem(scrapy.Item):
    source_id = scrapy.Field()
    location_name = scrapy.Field()
    url = scrapy.Field()
    phone_number = scrapy.Field()
    street_address_1 = scrapy.Field()
    street_address_2 = scrapy.Field()
    street_address_3 = scrapy.Field()
    city = scrapy.Field()
    postal_code = scrapy.Field()
    state = scrapy.Field()
    country = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()
    type = scrapy.Field()
    schedules: list = scrapy.Field()
    menus: list = scrapy.Field()
    schedules_chickfila = scrapy.Field()
    

class RestaurantScheduleItem(scrapy.Item):
    type = scrapy.Field()
    monday = scrapy.Field()
    tuesday = scrapy.Field()
    wednesday = scrapy.Field()
    thursday = scrapy.Field()
    friday = scrapy.Field()
    saturday = scrapy.Field()
    sunday = scrapy.Field()


class RestaurantMenuItem(scrapy.Item):
    source_category_id = scrapy.Field()
    category_name = scrapy.Field()
    products: list = scrapy.Field()
    url = scrapy.Field()


class RestaurantProductItem(scrapy.Item):
    category_name = scrapy.Field()
    sequence_number = scrapy.Field()
    source_product_id = scrapy.Field()
    options_group_id = scrapy.Field()
    product_name = scrapy.Field()
    description = scrapy.Field()
    price = scrapy.Field()
    pc_count = scrapy.Field()
    min_calories = scrapy.Field()
    max_calories = scrapy.Field()
    product_image = scrapy.Field()
    base_options: list = scrapy.Field()
    size = scrapy.Field()
    url = scrapy.Field()
    size: list = scrapy.Field()
    size_flavour_list: list = scrapy.Field()


class RestaurantBaseItem(scrapy.Item):
    description = scrapy.Field()
    base = scrapy.Field()
    base_price = scrapy.Field()
    add_ons: list = scrapy.Field()


class RestaurantAddOnItem(scrapy.Item):
    add_on_name = scrapy.Field()
    sub_name = scrapy.Field()
    price = scrapy.Field()


class RestaurantChilisItem(scrapy.Item):
    source_id = scrapy.Field()
    url = scrapy.Field()
    location_name = scrapy.Field()
    phone_number = scrapy.Field()
    street_address = scrapy.Field()
    locality = scrapy.Field()
    city = scrapy.Field()
    postal_code = scrapy.Field()
    state = scrapy.Field()
    country = scrapy.Field()
    menus: list = scrapy.Field()


class RestaurantChilisMenuItem(scrapy.Item):
    category_name = scrapy.Field()
    products: list = scrapy.Field()
    menu_address = scrapy.Field()


class RestaurantChilisProductItem(scrapy.Item):
    sequence_number = scrapy.Field()
    product_name = scrapy.Field()
    description = scrapy.Field()
    price = scrapy.Field()
    min_calories = scrapy.Field()
    max_calories = scrapy.Field()
    product_image = scrapy.Field()
    url = scrapy.Field()
