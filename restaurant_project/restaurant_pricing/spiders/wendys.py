import scrapy
import json
import xmltodict
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantScheduleItem,
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem
)


class WendysSpider(scrapy.Spider):
    name = 'wendys'
    start_urls = ['https://locations.wendys.com/united-states']
   
    def parse(self, response):
        state_urls = response.xpath('//a[@class="Directory-listLink"]/@href').getall()
        yield from response.follow_all(state_urls,callback=self.parse_locations)

    def parse_locations(self, response):
        if response.xpath('//a[@data-ya-track="visitpage"]'):
            list_of_restaurants=response.xpath('//a[@data-ya-track="visitpage"]')
            for restaurant in list_of_restaurants:
                restaurant_url=response.urljoin(restaurant.xpath('./@href').get(""))
                yield scrapy.Request(restaurant_url,callback=self.parse_details)

        else:
            list_of_cities=response.xpath("//li[@class='Directory-listItem']")
            for city in list_of_cities:
                city_url=response.urljoin(city.xpath('./a/@href').get(""))
                count=city.xpath('./span/text()').get("")
                if count=="(1)":
                    yield scrapy.Request(city_url,callback=self.parse_details)
                else:
                    yield scrapy.Request(city_url,callback=self.parse_restaurants)

    def parse_restaurants(self, response):
        restaurants_urls=response.xpath('//a[@data-ya-track="visitpage"]/@href').getall()
        yield from response.follow_all(restaurants_urls,callback=self.parse_details)

    def parse_details(self, response):
        restaurant_item = RestaurantItem()
        restaurant_item["source_id"] = response.xpath('//div[@class="LocationInfo-services"]/@data-corporatecode').get("").strip()
        restaurant_item["location_name"] = response.url.split("/")[-1].strip()
        restaurant_item["url"] = response.url
        restaurant_item["phone_number"] = response.xpath('//span[@itemprop="telephone"]/text()').get("").strip()
        restaurant_item["street_address_1"] = response.xpath('//span[@class="c-address-street-1"]/text()').get("").strip()
        restaurant_item["city"] = response.xpath('//span[@class="c-address-city"]/text()').get("").strip()
        restaurant_item["postal_code"] = response.xpath('//span[@itemprop="postalCode"]/text()').get("").strip()
        restaurant_item["state"] = response.xpath('//abbr[@itemprop="addressRegion"]/text()').get("").strip()
        restaurant_item["country"] = "US"

        schedule = []
        for weekly_schedule in response.xpath('//div[@class="LocationInfo-hours"]'):
            schedule_item = RestaurantScheduleItem()
            operation_type = weekly_schedule.xpath('.//h4/text()').get("")
            if operation_type == "Restaurant Hours":
                schedule_item["type"] = "Restaurant"
            elif operation_type == "Drive Thru Hours":
                schedule_item["type"] = "DriveThru"
            else:
                schedule_item["type"] = operation_type

            for day_schedule in weekly_schedule.xpath('.//div/table//tr'):
                weekday = day_schedule.xpath('.//td[@class="c-location-hours-details-row-day"]/text()').get("")
                if weekday and weekday.lower() in ["sunday","monday","tuesday","wednesday","thursday","friday","saturday"]:
                    if day_schedule.xpath('.//td[@class="c-location-hours-details-row-intervals"]/span/span'):
                        schedule_item[weekday.lower()] = ''.join(day_schedule.xpath('.//td[@class="c-location-hours-details-row-intervals"]/span/span/text()').getall())
                    elif day_schedule.xpath('.//td[@class="c-location-hours-details-row-intervals"]/span/text()'):
                        schedule_item[weekday.lower()] = ''.join(day_schedule.xpath('.//td[@class="c-location-hours-details-row-intervals"]/span/text()').getall())
                        
            schedule.append(schedule_item)
        restaurant_item["schedules"] = schedule

        menu_api = f'https://orderservice.wendys.com/OrderingServices/rest/menu/getSiteMenu?lang=en&cntry=US&sourceCode=ORDER.WENDYS&version=11.3.2&siteNum={restaurant_item["source_id"]}&freeStyleMenu=true'
    
        yield scrapy.Request(url=menu_api, callback=self.parse_menus_api, cb_kwargs={"restaurant_item": restaurant_item})

    def parse_menus_api(self, response, restaurant_item=None):
        data_dict = xmltodict.parse(response.text)  
        json_data = json.dumps(data_dict)
        menu_data = json.loads(json_data)

        menus = []
        for category in menu_data.get("menuResponse").get("menuLists").get("subMenus", [])[1:]:
            menu_item = RestaurantMenuItem()
            menu_item["source_category_id"] = category.get("subMenuId")
            menu_item["category_name"] = category.get("displayName")

            if menu_item["category_name"] == "Give Something Back":
                continue

            if menu_item["category_name"] in ["Croissants","Breakfast Combos","Biscuits","Classics","Sides and More","Coffee"]:
                continue

            product_list = []
            for product in menu_data.get("menuResponse").get("menuLists").get("salesItems", []):
                product_item = RestaurantProductItem()
                if type(category.get("menuItems",[])) != str:
                    if product.get("alaCarteMenuItemId") in category.get("menuItems",[]):
                        product_item["source_product_id"] = product.get("alaCarteMenuItemId")
                        product_item["url"] = f'https://order.wendys.com/product/{product_item["source_product_id"]}'
                        name = product.get("displayName")
                        if name == "Coca-Cola Freestyle" or name == "Pineapple Mango Lemonade": #modified line
                            product_item["product_name"] = product.get("name")
                        else:
                            product_item["product_name"] = product.get("displayName") 
                        product_item["description"] = product.get("description")

                        for image in menu_data.get("menuResponse").get("menuLists").get("menuItems", []):
                            if product.get("alaCarteMenuItemId") == image.get("menuItemId"):
                                product_image = image.get("baseImageName")
                                product_item["product_image"] = f"https://app.wendys.com/unified/assets/menu/pg-cropped/{product_image}_medium_US_en.png"
                        
                        product_item["price"] = float(product.get("price"))
                        calories = product.get("calorieRange").split(" ")[0].strip()
                        if "-" in calories:
                            product_item["min_calories"] = int(calories.split("-")[0])
                            product_item["max_calories"] = int(calories.split("-")[-1].replace(",",""))
                        else:                
                            product_item["min_calories"] = int(calories.replace(",",""))
                   
                        base_options = []
                        base_item = RestaurantBaseItem()
                        base_item["description"] = "Default"
                        base_item["base"] = "Default"
                        base_item["base_price"] = ""

                        add_ons=[]
                        for mod in menu_data.get("menuResponse").get("menuLists").get("modifiers", []):
                            if isinstance(mod.get("itemModifiers"), list):
                                for item_mod in mod.get("itemModifiers"):
                                    add_on_item = RestaurantAddOnItem()
                                    if item_mod.get("modifierGroupId") in product.get("modifierGroups",[]):
                                        add_on_item["add_on_name"] = mod.get("displayName")
                                        add_on_item["price"] = float(item_mod.get("price"))
                                        add_ons.append(add_on_item)      
                            else:
                                add_on_item = RestaurantAddOnItem()
                                if mod.get("itemModifiers").get("modifierGroupId") in product.get("modifierGroups",[]):
                                    add_on_item["add_on_name"] = mod.get("displayName")
                                    add_on_item["price"] = float(mod.get("itemModifiers").get("price"))
                                    add_ons.append(add_on_item)

                        if menu_item["category_name"] == "Beverages" or menu_item["category_name"] == "Frosty" or menu_item["category_name"] == "Bakery":
                            product_list.append(product_item)
                        else:    
                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)    
                            product_item["base_options"] = base_options  
                            product_list.append(product_item)
               
            if product_list == []:
                for product in menu_data.get("menuResponse").get("menuLists").get("menuItems", []):
                    product_item = RestaurantProductItem()
                    if product.get("menuItemId") in category.get("menuItems",[]):
                        product_item["source_product_id"] = product.get("menuItemId")
                        product_item["url"] = f'https://order.wendys.com/product/{product_item["source_product_id"]}'
                        product_item["product_name"] = product.get("displayName")
                        product_item["description"] = product.get("description")
                        product_image = product.get("baseImageName")
                        product_item["product_image"] = f"https://app.wendys.com/unified/assets/menu/pg-cropped/{product_image}_medium_US_en.png"
                   
                        if menu_item["category_name"] == "Combos":
                            for product_size_ids in product.get("salesGroups",[])[1:2]:
                                size_ids = product_size_ids.get("salesItemIds",[])
                            combo_size_item={}
                            for combo_size_ids in menu_data.get("menuResponse").get("menuLists").get("comboConfig", [])[0:1]:
                                for combo_size_id in combo_size_ids.get("comboSizes",[]):
                                    combo_size = combo_size_id.get("comboGroups").get("salesItemId")
                                    if combo_size in size_ids:
                                        combo_size_item["size"] = combo_size_id.get("size").title()
                                        if combo_size_id.get("priceIncrement") == None:
                                            combo_size_item["price_increment"] = None
                                        else:
                                            combo_size_item["price_increment"] = float(combo_size_id.get("priceIncrement"))
                                        product_item={**product_item, **combo_size_item}

                                        product_item["price"] = float(product.get("price"))
                                        calories = product.get("calorieRange")
                                        if not calories:
                                            product_item["min_calories"] = None
                                            product_item["max_calories"] = None 
                                        elif "-" in calories:
                                            product_item["min_calories"] = int(calories.split(" ")[0].split("-")[0].strip().replace(",",""))
                                            product_item["max_calories"] = int(calories.split(" ")[0].split("-")[-1].strip().replace(",",""))        
                                        else:       
                                            product_item["min_calories"] = int(calories.split(" ")[0].strip().replace(",","")) 
                
                                    product_list.append(product_item)
                        else:
                            product_item["price"] = float(product.get("price"))
                            calories = product.get("calorieRange")
                            if not calories:
                                product_item["min_calories"] = None
                                product_item["max_calories"] = None 
                            elif "-" in calories:
                                product_item["min_calories"] = int(calories.split(" ")[0].split("-")[0].strip().replace(",",""))
                                product_item["max_calories"] = int(calories.split(" ")[0].split("-")[-1].strip().replace(",",""))        
                            else:       
                                product_item["min_calories"] = int(calories.split(" ")[0].strip().replace(",","")) 
                    
                            product_list.append(product_item)

            
            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus
        
        yield restaurant_item                        
    