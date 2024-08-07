import scrapy
import json
import dateutil.parser as parser
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantScheduleItem,
    RestaurantMenuItem,
    RestaurantProductItem,
)

class SweetgreenSpider(scrapy.Spider):
    name = 'sweetgreen'
    count=1

    def start_requests(self):
        for i in range(1,2571):
            start_url = f"https://order.sweetgreen.com/api/restaurants/{i}"
            yield scrapy.Request(start_url, callback=self.parse_restaurants)

    def parse_restaurants(self, response):
        json_data = json.loads(response.text)
        if 'sg' not in json_data.get("restaurant","").get("name").lower():
            restaurant_item = RestaurantItem()
            restaurant_item["source_id"] = json_data.get("restaurant","").get("id","")
            restaurant_item["location_name"] = json_data.get("restaurant","").get("name")
            restaurant_item["url"] = f"https://order.sweetgreen.com/{json_data.get('restaurant').get('restaurant_slug')}/menu"
            restaurant_item["phone_number"] = json_data.get("restaurant","").get("phone", "")
            restaurant_item["street_address_1"] = json_data.get("restaurant","").get("address","")
            restaurant_item["street_address_2"] = json_data.get("restaurant","").get("cross_street","")
            restaurant_item["city"] = json_data.get("restaurant","").get("city")
            restaurant_item["postal_code"] = json_data.get("restaurant","").get("zip_code")
            restaurant_item["state"] = json_data.get("restaurant","").get("state")
            restaurant_item["country"] = "US"
            restaurant_item["latitude"] = json_data.get("restaurant","").get("latitude")
            restaurant_item["longitude"] = json_data.get("restaurant","").get("longitude")

            schedule = []
            schedule_item = RestaurantScheduleItem()
            for day_schedule in json_data['restaurant']['hours']:
                if day_schedule!=None:
                    day = day_schedule.get('wday','')
                    weekday = parser.parse(day).strftime('%A')
                    if weekday and weekday.lower() in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
                        start = day_schedule.get('start')
                        start = parser.parse(start).strftime('%H:%M %p')
                        end = day_schedule.get('end')
                        end = parser.parse(end).strftime('%I:%M %p')
                        schedule_description = start+" - "+end
                        schedule_item[weekday.lower()] = schedule_description
            schedule.append(schedule_item)
            restaurant_item["schedules"] = schedule

            url = f"https://order.sweetgreen.com/api/menus/{json_data.get('restaurant','').get('menu_id','')}?filters%5Bcollection_exclusive%5D=false&crossDomain=true&xhrFields%5BwithCredentials%5D=true"

            restaurant_slug=json_data.get('restaurant').get('restaurant_slug')

            yield scrapy.Request(url, callback=self.parse_products, cb_kwargs={"restaurant_item": restaurant_item,"restaurant_slug":restaurant_slug})

    def parse_products(self, response, restaurant_item, restaurant_slug):
        menu_data = json.loads(response.text)

        menus = []
        for category in menu_data.get("categories", []):
            menu_item = RestaurantMenuItem()
            menu_item["source_category_id"] = category.get("id")
            menu_item["category_name"] = "featured" if category.get("name")=="plates" else "custom" if category.get("name")=="miscellaneous" else category.get("name")

            product_list = []
            for product in menu_data.get("products", []):
                product_item = RestaurantProductItem()
                if (menu_item["category_name"] =="custom") and (product.get('name')=="create your own"):
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('display_name') if product.get('display_name')!=None and product.get('display_name')!="" else product.get('name')
                    product_item["description"] = product.get('description')
                    product_item["url"] = f"https://order.sweetgreen.com/{restaurant_slug}/{product.get('product_slug')}"
                    asset_id=product.get('asset_ids')[0]
                    for asset in menu_data.get("assets"):
                        if asset_id==asset.get("parent_asset_id"):
                            product_item["product_image"] = asset.get('url')
                    product_item["price"] = float("{0:.2f}".format(product.get('cost')/ 100.))
                    product_item["min_calories"] = int(product.get('calories'))
                    product_list.append(product_item)
                    self.count += 1

                elif (menu_item["category_name"] =="featured") and (product.get('name') in ["chicken + goat cheese + pesto","mushroom chimichurri","chicken chimichurri"]):
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('display_name') if product.get('display_name')!=None and product.get('display_name')!="" else product.get('name')
                    product_item["description"] = product.get('description')
                    product_item["url"] = f"https://order.sweetgreen.com/{restaurant_slug}/{product.get('product_slug')}"
                    asset_id=product.get('asset_ids')[0]
                    for asset in menu_data.get("assets"):
                        if asset_id==asset.get("parent_asset_id"):
                            product_item["product_image"] = asset.get('url')
                    product_item["price"] = float("{0:.2f}".format(product.get('cost')/ 100.))
                    product_item["min_calories"] = int(product.get('calories'))
                    product_list.append(product_item)
                    self.count += 1
                    
                else:
                    if (menu_item["source_category_id"] == product.get("category_id")) and (product.get('name') not in ["chicken + goat cheese + pesto","mushroom chimichurri","chicken chimichurri","create your own"]):
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product.get('id')
                        product_item["product_name"] = product.get('display_name') if product.get('display_name')!=None and product.get('display_name')!="" else product.get('name')
                        product_item["description"] = product.get('description')
                        product_item["url"] = f"https://order.sweetgreen.com/{restaurant_slug}/{product.get('product_slug')}"
                        asset_id=product.get('asset_ids')[0]
                        for asset in menu_data.get("assets"):
                            if asset_id==asset.get("parent_asset_id"):
                                product_item["product_image"] = asset.get('url')
                        product_item["price"] = float("{0:.2f}".format(product.get('cost')/ 100.))
                        product_item["min_calories"] = int(product.get('calories'))
                        product_list.append(product_item)
                        self.count += 1      

            menu_item["products"] = product_list
            menus.append(menu_item)
            
        restaurant_item["menus"] = menus
        self.count = 1
        yield restaurant_item
