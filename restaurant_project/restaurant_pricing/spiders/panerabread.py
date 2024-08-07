import scrapy
import json
import dateutil.parser as parser
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantScheduleItem,
    RestaurantMenuItem,
    RestaurantProductItem,
)


class PaneraBreadSpider(scrapy.Spider):
    name = "panerabread"
    count=1
    
    def start_requests(self):
        restaurants = "https://www-api.panerabread.com/www-api/public/cafe/search?address=California,+USA&radius=768000&openCafes=true"
        headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'referer': 'https://www.panerabread.com/',
        }
        yield scrapy.Request(restaurants,headers=headers,callback=self.parse_details)

    def parse_details(self, response):
        json_data = json.loads(response.text)
        
        for data in json_data.get("cafeList",[]):
            restaurant_item = RestaurantItem()
            restaurant_item["source_id"] = data.get("cafeId","")
            restaurant_item["location_name"] = data.get("cafeName","")
            restaurant_item["url"] = "https://www.panerabread.com/en-us/app/menu.html"
            restaurant_item["phone_number"] = data.get("cafePhone","")
            restaurant_item["street_address_1"] = data.get("cafeLocation","").get("addressLine1","")
            restaurant_item["city"] = data.get("cafeLocation","").get("city","")
            restaurant_item["state"] = data.get("cafeLocation","").get("countryDivision","")
            restaurant_item["postal_code"] = data.get("cafeLocation","").get("postalCode","")
            restaurant_item["country"] = "US"
            restaurant_item["latitude"] = data.get("cafeLocation","").get("latitude","")
            restaurant_item["longitude"] = data.get("cafeLocation","").get("longitude","")

            schedule = []
            type = []
            for key,value in data.get('cafeFeatures').items():
                if key in ["hasCurbside","hasDelivery","hasDineIn","hasDriveThru","hasInCafePickup","hasPickup"] and value==True:
                    type.append(key)
            schedule_item = RestaurantScheduleItem()
            for day_key,day_schedule in data['cafeHours'].items():
                if day_schedule!=None:
                    day = day_key
                    weekday = parser.parse(day).strftime('%A')
                    if weekday and weekday.lower() in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
                        start = day_schedule[0].get('open')
                        start = parser.parse(start).strftime('%H:%M %p')
                        end = day_schedule[0].get('close')
                        end = parser.parse(end).strftime('%I:%M %p')
                        schedule_description = start+" - "+end
                        schedule_item[weekday.lower()] = schedule_description
            schedule.append(schedule_item)
            restaurant_item["schedules"] = schedule
            restaurant_item["type"]= type

            menu_url = f'https://www-api.panerabread.com/www-api/public/menu/categories/{restaurant_item["source_id"]}/version/41628/41636/41641/en-US'

            yield scrapy.Request(menu_url,callback=self.parse_menus,cb_kwargs={"restaurant_item": restaurant_item})

    async def parse_menus(self, response, restaurant_item):
        json_data = json.loads(response.text)

        menus = []
        for key,data in json_data["categoryDict"].items():
            if data.get("name")=="Sandwiches" and data.get("subCategories",[])!=[]:
                menu_item = RestaurantMenuItem()
                menu_item["source_category_id"] = data.get("catId")
                menu_item["category_name"] = data.get("name")
                product_list = []
                for cat in data.get("subCategories",[]):
                    category_id=cat.get('catId','')
                    for key,data in json_data["categoryDict"].items():
                        if category_id==data.get("catId",""):
                            placard_list=data.get("placards",[])
                            hashkey_api_url=f'https://www-api.panerabread.com/www-api/public/menu/placard/hashes/v2/{restaurant_item["source_id"]}/version/41646/en-US'
                            hashkey_response = await self.request_process(hashkey_api_url)
                            hashkey_json_data = json.loads(hashkey_response.text)
                            for key_hash,data_hash in hashkey_json_data["placardHashes"].items():
                                if int(key_hash) in placard_list:
                                    product_api_url=f'https://www-api.panerabread.com/www-api/public/menu/placard/hash/{data_hash}'
                                    product_response = await self.request_process(product_api_url)
                                    product_json_data = json.loads(product_response.text) 
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["source_product_id"] = product_json_data.get('productId')
                                    product_item["product_name"] = product_json_data.get('name') 
                                    product_item["description"] = product_json_data.get('description')
                                    product_item["url"] = f"https://www.panerabread.com/en-us/app/product/{data_hash}.html"
                                    product_item["price"] = product_json_data.get('price')
                                    for img in product_json_data["optSets"]:
                                        if  product_json_data.get('name')== img.get('name'):
                                            product_item["product_image"] = f"https://www.panerabread.com/content/dam/panerabread/menu-omni/integrated-web/detail/{img.get('imgKey')}.jpg"
                                        for cal in img["nutrients"]:
                                            if cal.get("name")=="Calories":
                                                product_item["min_calories"] = int(cal.get('value'))
                                    product_list.append(product_item)
                                    self.count+=1
                menu_item["products"] = product_list
                menus.append(menu_item)

            elif data.get("name")=="Salads" and data.get("subCategories",[])!=[]:
                menu_item = RestaurantMenuItem()
                menu_item["source_category_id"] = data.get("catId")
                menu_item["category_name"] = data.get("name")
                product_list = []
                for cat in data.get("subCategories",[]):
                    category_id=cat.get('catId','')
                    for key,data in json_data["categoryDict"].items():
                        if category_id==data.get("catId",""):
                            placard_list=data.get("placards",[])
                            hashkey_api_url=f'https://www-api.panerabread.com/www-api/public/menu/placard/hashes/v2/{restaurant_item["source_id"]}/version/41646/en-US'
                            hashkey_response = await self.request_process(hashkey_api_url)
                            hashkey_json_data = json.loads(hashkey_response.text)
                            for key_hash,data_hash in hashkey_json_data["placardHashes"].items():
                                if int(key_hash) in placard_list:
                                    product_api_url=f'https://www-api.panerabread.com/www-api/public/menu/placard/hash/{data_hash}'
                                    product_response = await self.request_process(product_api_url)
                                    product_json_data = json.loads(product_response.text) 
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["source_product_id"] = product_json_data.get('productId')
                                    product_item["product_name"] = product_json_data.get('name') 
                                    product_item["description"] = product_json_data.get('description')
                                    product_item["url"] = f"https://www.panerabread.com/en-us/app/product/{data_hash}.html"
                                    product_item["price"] = product_json_data.get('price')
                                    for img in product_json_data["optSets"]:
                                        if  product_json_data.get('name')== img.get('name'):
                                            product_item["product_image"] = f"https://www.panerabread.com/content/dam/panerabread/menu-omni/integrated-web/detail/{img.get('imgKey')}.jpg"
                                        for cal in img["nutrients"]:
                                            if cal.get("name")=="Calories":
                                                product_item["min_calories"] = int(cal.get('value'))
                                    product_list.append(product_item)
                                    self.count+=1    
                menu_item["products"] = product_list
                menus.append(menu_item)
                
            restaurant_item["menus"] = menus
        self.count = 1
        yield restaurant_item

    async def request_process(self, url):
        api_headers = {'referer': 'https://www.panerabread.com/'}
        request = scrapy.Request(url,headers=api_headers)
        response = await self.crawler.engine.download(request, self)
        return response             