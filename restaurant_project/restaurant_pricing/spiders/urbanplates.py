import scrapy
import json
import re
import dateutil.parser as parser
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantScheduleItem,
)


class UrbanplatesSpider(scrapy.Spider):
    count = 1
    name = "urbanplates"
    headers = {
        "authority": "urbanplates.com",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36",
        "accept": "application/json, text/javascript, */*; q=0.01",
        "referer": "https://urbanplates.com/location/",
        "accept-language": "en-US,en;q=0.9",
    }


    def start_requests(self):
        url = "https://urbanplates.com/location/"
        yield scrapy.Request(url, headers=self.headers, callback=self.parse)

    def parse(self, response):
        api_key = re.findall(r"var\s*novadine_nonce\s\=\s*\'(.*?)\'", response.text)[0]
        url = f"https://urbanplates.com/wp-admin/admin-ajax.php?nonce={api_key}&action=novadine_api_call&method=GET&endpoint=stores%3Fall_stores%3Dtrue"

        yield scrapy.Request(
            url,
            headers=self.headers,
            callback=self.parse_details,
            cb_kwargs={"api_key": api_key},
        )

    def parse_details(self, response, api_key):
        json_data = json.loads(response.text)
        for data in json_data:
            restaurant_item = RestaurantItem()
            source_id = data["store_id"]
            if "900" not in source_id:
                restaurant_item["source_id"] = source_id
                restaurant_item["location_name"] = data["name"]
                restaurant_item["phone_number"] = data["phone"].strip()
                restaurant_item["city"] = data["city"]
                restaurant_item["street_address_1"] = data["address1"]
                restaurant_item["state"] = data["state"]
                restaurant_item["postal_code"] = data["postal_code"]
                restaurant_item["country"] = data["country"]
                restaurant_item["latitude"] = data["latitude"]
                restaurant_item["longitude"] = data["longitude"]

                schedule = []
                schedule_item = RestaurantScheduleItem()
                for weekly_schedule in data["hours"]:
                    day = weekly_schedule.get("display_name")
                    if day and day.lower() in [
                        "sunday",
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                    ]:
                        start = weekly_schedule.get("start_time")
                        start = parser.parse(start).strftime("%H:%M %p")
                        end = weekly_schedule.get("end_time")
                        end = parser.parse(end).strftime("%I:%M %p")
                        schedule_description = start + " - " + end
                        schedule_item[day.lower()] = schedule_description
                schedule.append(schedule_item)
                restaurant_item["schedules"] = schedule

                link = f"https://urbanplates.com/wp-admin/admin-ajax.php?nonce={api_key}&action=novadine_api_call&endpoint=stores%2F{source_id}%2Fmenus%3Fskip_pick_lists%3Dtrue%26service_type_id%3D2&method=GET"
                yield scrapy.Request(
                    url=link,
                    callback=self.parse_menus,
                    cb_kwargs={"restaurant_item": restaurant_item},
                )

    def parse_menus(self, response, restaurant_item):
        data = json.loads(response.text)
        for menu_data in data:
            menus = []
            for category in menu_data["categories"]:
                menu_item = RestaurantMenuItem()
                menu_item["source_category_id"] = category["category_id"]
                menu_item["category_name"] = category["name"]

                if menu_item["category_name"] == "no plastic utensils"or menu_item["category_name"] == "Nourishing Heroes Meal":
                    continue

                product_list = []
                for product in category["items"]:
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product["item_id"]
                    product_item["product_name"] = product["name"].strip()
                    product_item["description"] = product["long_desc"]
                    product_item["product_image"] = product["image_urls"].get("standard_mobile")
                    price = product["variants"][0].get("price")
                    product_item["price"] = float("{0:.2f}".format(price / 100.0))
                    try:
                        if "Tender" in product_item["product_name"]:
                            product_item["pc_count"] = int(re.findall(r"\d+", product_item["product_name"])[0])
                        else:
                            product_item["pc_count"] = 1
                    except:
                        product_item["pc_count"] = 1

                    if product_item["product_name"] == "Donate a nutritious meal to a healthcare worker. Urban Plates will match every meal donated.":
                        continue
                    
                    self.count += 1
                    product_list.append(product_item)

                menu_item["products"] = product_list
                menus.append(menu_item)
                restaurant_item["menus"] = menus

            yield restaurant_item

