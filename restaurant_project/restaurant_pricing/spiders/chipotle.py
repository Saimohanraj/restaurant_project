import scrapy
import json
from dateutil import parser
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantScheduleItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem
)


class ChipotleSpider(scrapy.Spider):
    name = "chipotle"
    start_urls = ["https://locations.chipotle.com/"]
    count=1

    def parse(self, response):
        states = response.xpath('//ul[@class="Directory-listLinks"]/li')
        for state in states:
            state_url = response.urljoin(state.xpath('.//a/@href').get(""))
            count = state.xpath('.//a/@data-count').get("") 
            if count == "(1)":
                yield scrapy.Request(state_url,callback=self.parse_details)
            else:
                yield scrapy.Request(state_url,callback=self.parse_cities)

    def parse_cities(self, response):
        if response.xpath('//ul[@class="Directory-listLinks"]/li'):
            cities = response.xpath('//ul[@class="Directory-listLinks"]/li')
            for city in cities:
                city_url = response.urljoin(city.xpath('.//a/@href').get(""))
                count = city.xpath('.//a/@data-count').get("")
                if count == "(1)":
                    yield scrapy.Request(city_url,callback=self.parse_details)
                else:
                    yield scrapy.Request(city_url,callback=self.parse_restaurants)
        else:
            restaurants = response.xpath('//li[@class="Directory-listTeaser"]')
            for restaurant in restaurants:
                restaurant_url = response.urljoin(restaurant.xpath('.//h2/a/@href').get(""))
                yield scrapy.Request(restaurant_url,callback=self.parse_details)        

    def parse_restaurants(self, response):
        restaurants = response.xpath('//li[@class="Directory-listTeaser"]')
        for restaurant in restaurants:
            restaurant_url = response.urljoin(restaurant.xpath('.//h2/a/@href').get(""))
            yield scrapy.Request(restaurant_url,callback=self.parse_details)

    async def parse_details(self, response):
        restaurant_item = RestaurantItem()
        restaurant_item["location_name"] = response.xpath('//h1/text()').get("")
        restaurant_item["url"] = response.url
        restaurant_item["phone_number"] = response.xpath('//div[@itemprop="telephone"]/text()').get("")
        restaurant_item["street_address_1"] = response.xpath('//span[@class="c-address-street-1"]/text()').get("")
        restaurant_item["city"] = response.xpath('//span[@class="c-address-city"]/text()').get("")
        restaurant_item["state"] = response.xpath('//abbr[@itemprop="addressRegion"]/text()').get("")
        restaurant_item["postal_code"] = response.xpath('//span[@itemprop="postalCode"]/text()').get("")
        restaurant_item["country"] = response.xpath('//abbr[@itemprop="addressCountry"]/text()').get("")
        restaurant_item["latitude"] = response.xpath('//meta[@itemprop="latitude"]/@content').get("")
        restaurant_item["longitude"] = response.xpath('//meta[@itemprop="longitude"]/@content').get("")

        schedule = []
        schedule_item = RestaurantScheduleItem()
        for day_schedule in response.xpath('//table//tr[@itemprop="openingHours"]'):
            weekday = day_schedule.xpath('./td[@class="c-location-hours-details-row-day"]/text()').get("")
            weekday=parser.parse(weekday).strftime('%A')
            if weekday and weekday.lower() in ["sunday","monday","tuesday","wednesday","thursday","friday","saturday"]:
                schedule_item[weekday.lower()] = ''.join(day_schedule.xpath('.//td[@class="c-location-hours-details-row-intervals"]/span/span/text()').getall())

        schedule.append(schedule_item)
        restaurant_item["schedules"] = schedule
    
        email = response.xpath("//*[@class='Core-email']/text()").get("")
        try:
            res_email_id = email.split(".")[1]
            loc_id = res_email_id
        except:
            res_order_id = response.xpath('//a[contains(text(),"Order Online")]/@href').get("")   
            loc_id = res_order_id.split("Index/")[-1].split("?")[0]

        api_url_burritos = f"https://services.chipotle.com/menuinnovation/v1/restaurants/{loc_id}/onlinemenu?channelId=web&includeUnavailableItems=true"
        api_url_lifestye_bowl = f"https://services.chipotle.com/menuinnovation/v1/restaurants/{loc_id}/onlinemeals?includeUnavailableItems=true"

        product_list = []
        for api_url in [api_url_lifestye_bowl,api_url_burritos]:
            menu_response = await self.request_process(api_url)
            menu_data = json.loads(menu_response.text)

            if "onlinemeals" in api_url:
                for life_data in menu_data:
                    category_name = life_data.get("mealType")
                    if category_name == "Lifestyle":
                        product_item = RestaurantProductItem()
                        product_item["category_name"] = category_name + " Bowl"
                        product_item["sequence_number"] = self.count
                        product_name = life_data.get("mealName","")
                        sub_name = life_data.get("entree").get("itemName").split(" ")[0]
                        product_item["product_name"] = product_name + " - " + sub_name
                        product_item["price"] =life_data.get("mealPrice","")
                        product_item["pc_count"] = 1
                        product_item["min_calories"] = life_data.get("calories","")
                        product_item["product_image"] = life_data.get("primaryImages",[])[2].get("imageUrl")
                        product_item["description"] = life_data.get("entree").get("ingredientsSummary")
                        product_item["url"] = "https://www.chipotle.com/order/build/"+ life_data["mealType"].lower()+ "-"+ life_data["mealName"].lower().split(" ")[-1]
                        product_list.append(product_item)   
                        self.count+=1            

            else:   
                for key in menu_data:
                    if key == "entrees":
                        for data in menu_data.get("entrees"):        
                            if data['itemType'] == "Quesadilla":
                                product_item = RestaurantProductItem()
                                product_item["category_name"] = data.get('itemType')
                                product_item["sequence_number"] = self.count
                                product_item["product_name"] = data.get("itemName")
                                product_item["price"] = data.get("unitPrice")
                                # product_item["min_calories"] = 
                                product_item["pc_count"] = 1
                                # product_item["description"] = 
                                # product_item["product_image"] = 
                                product_item["url"] = f'https://www.chipotle.com/order/build/{product_item["category_name"].lower()}'
                           
                                base_options = []
                                base_item = RestaurantBaseItem()
                                base_item["description"] = "Default"
                                base_item["base"] = "Default"
                                base_item["base_price"] = ""
                
                                add_ons=[]
                                for addon in data.get("contents"):
                                    if addon.get("itemType") == "Addon":
                                        add_on_item = RestaurantAddOnItem()
                                        add_on_item["add_on_name"] = addon.get("itemName")
                                        add_on_item["price"] = addon.get("unitPrice")   
                                        add_ons.append(add_on_item)

                                base_item["add_ons"] = add_ons
                                base_options.append(base_item)    
                                product_item["base_options"] = base_options
                                product_list.append(product_item)   
                                self.count+=1             

                            elif data['itemType'] == "KidsQuesadilla" or data['itemType'] == "KidsBYO":
                                if data['itemType'] == "KidsBYO":
                                    if data.get("primaryFillingName") not in ["Guacamole","Queso Blanco"]:
                                        product_item = RestaurantProductItem()
                                        product_item["category_name"] = "Kid's Meal"
                                        product_item["sequence_number"] = self.count
                                        product_item["product_name"] = data.get("itemName")
                                        product_item["price"] = data.get("unitPrice")
                                        # product_item["min_calories"] = 
                                        product_item["pc_count"] = 1
                                        # product_item["description"] = 
                                        # product_item["product_image"] = 
                                        product_item["url"] = "https://www.chipotle.com/order/build/kid's-build-your-own"

                                        base_options = []
                                        base_item = RestaurantBaseItem()
                                        base_item["description"] = "Default"
                                        base_item["base"] = "Default"
                                        base_item["base_price"] = ""
                        
                                        add_ons=[]
                                        for addon in menu_data.get("entrees"):
                                            if addon.get("itemType") == "KidsBYO":
                                                if addon.get("primaryFillingName") in ["Guacamole","Queso Blanco"]:
                                                    add_on_item = RestaurantAddOnItem()
                                                    add_on_item["add_on_name"] = addon.get("primaryFillingName")
                                                    add_on_item["price"] = addon.get("unitPrice")   
                                                    add_ons.append(add_on_item)

                                        base_item["add_ons"] = add_ons
                                        base_options.append(base_item)    
                                        product_item["base_options"] = base_options
                                        product_list.append(product_item)  
                                        self.count+=1          

                                elif data['itemType'] == "KidsQuesadilla": 
                                    if data.get("primaryFillingName") not in ["Guacamole"]:
                                        product_item = RestaurantProductItem()
                                        product_item["category_name"] = "Kid's Meal"
                                        product_item["sequence_number"] = self.count
                                        product_item["product_name"] = data.get("itemName")
                                        product_item["price"] = data.get("unitPrice")
                                        # product_item["min_calories"] = 
                                        product_item["pc_count"] = 1
                                        # product_item["description"] = 
                                        # product_item["product_image"] = 
                                        product_item["url"] = "https://www.chipotle.com/order/build/kid's-quesadilla"

                                        base_options = []
                                        base_item = RestaurantBaseItem()
                                        base_item["description"] = "Default"
                                        base_item["base"] = "Default"
                                        base_item["base_price"] = ""
                        
                                        add_ons=[]
                                        for addon in menu_data.get("entrees"):
                                            if addon.get("itemType") == "KidsQuesadilla":
                                                if addon.get("primaryFillingName") in ["Guacamole"]:
                                                    add_on_item = RestaurantAddOnItem()
                                                    add_on_item["add_on_name"] = addon.get("primaryFillingName")
                                                    add_on_item["price"] = addon.get("unitPrice")   
                                                    add_ons.append(add_on_item)

                                        base_item["add_ons"] = add_ons
                                        base_options.append(base_item)    
                                        product_item["base_options"] = base_options
                                        product_list.append(product_item) 
                                        self.count+=1      

                            elif data['itemType'] == "Tacos" and "CMG-2" in data['itemId']:
                                product_item = RestaurantProductItem()
                                product_item["category_name"] = data.get('itemType')
                                product_item["sequence_number"] = self.count
                                name = data.get("itemName").split(" ")
                                product_item["product_name"] = ' '.join(name[:-1]) + " " + "Tacos"
                                product_item["price"] = data.get("unitPrice")
                                # product_item["min_calories"] = 
                                product_item["pc_count"] = 3
                                # product_item["description"] = 
                                # product_item["product_image"] = 
                                product_item["url"] = f'https://www.chipotle.com/order/build/{product_item["category_name"].lower()}'

                                base_options = []
                                base_item = RestaurantBaseItem()
                                base_item["description"] = "Default"
                                base_item["base"] = "Default"
                                base_item["base_price"] = ""
                
                                add_ons=[]
                                for addon in data.get("contents"):
                                    if addon.get("itemType") == "Toppings":
                                        add_on_item = RestaurantAddOnItem()
                                        add_on_item["add_on_name"] = addon.get("itemName")
                                        add_on_item["price"] = addon.get("unitPrice")   
                                        add_ons.append(add_on_item)

                                base_item["add_ons"] = add_ons
                                base_options.append(base_item)    
                                product_item["base_options"] = base_options
                                product_list.append(product_item) 
                                self.count+=1
                   
                    if key == "sides":
                        for side_data in menu_data.get("sides"):
                            product_item = RestaurantProductItem()
                            product_item["category_name"] = "Sides & Drinks"
                            product_item["sequence_number"] = self.count
                            product_item["product_name"] = side_data.get("itemName")
                            product_item["price"] = side_data.get("unitPrice")
                            # product_item["min_calories"] = 
                            product_item["pc_count"] = 1
                            # product_item["description"] = 
                            # product_item["product_image"] = 
                            product_item["url"] = f'https://www.chipotle.com/order/build/{product_item["category_name"].lower().replace(" ","-")}'
                            product_list.append(product_item)
                            self.count+=1   

                    if key == "drinks":
                        for drink_data in menu_data.get("drinks"):
                            product_item = RestaurantProductItem()
                            product_item["category_name"] = "Sides & Drinks"
                            product_item["sequence_number"] = self.count
                            name = drink_data.get("itemName")
                            if "oz" in name:
                                if "oz Tractor Organic Lemonade" in name or "oz Tractor Organic Mandarin Agua Fresca" in name or "oz Tractor Organic Hibiscus Lemonade" in name or "oz Tractor Organic Berry Agua Fresca" in name:
                                    size_name = name.split(" ")
                                    product_item["product_name"] = " ".join(size_name[4:])
                                    product_item["size"] = " ".join(size_name[0:3])
                                else:    
                                    size_name = name.split(" ")
                                    product_item["product_name"] = " ".join(size_name[3:])
                                    product_item["size"] = " ".join(size_name[0:3])
                            else:
                                product_item["product_name"] = name
                            product_item["price"] = drink_data.get("unitPrice")
                            # product_item["min_calories"] = 
                            product_item["pc_count"] = 1
                            # product_item["description"] = 
                            # product_item["product_image"] = 
                            product_item["url"] = f'https://www.chipotle.com/order/build/{product_item["category_name"].lower().replace(" ","-")}'
                            product_list.append(product_item) 
                            self.count+=1 

            restaurant_item["menus"] = product_list
        self.count=1    
        yield restaurant_item

    async def request_process(self, url):
        api_headers = {
            "Ocp-Apim-Subscription-Key": "b4d9f36380184a3788857063bce25d6a",
            "Chipotle-CorrelationId": "OrderWeb-bfcac886-3766-4a16-b784-d7b761ced763",
        }
        request = scrapy.Request(url,headers=api_headers)
        response = await self.crawler.engine.download(request, self)
        return response    
