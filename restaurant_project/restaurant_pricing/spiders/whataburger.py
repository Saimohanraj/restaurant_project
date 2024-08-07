import scrapy
import json
from dateutil import parser
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantScheduleItem,
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem
)


class WhataBurgerSpider(scrapy.Spider):
    name = "whataburger"
    start_urls = ['https://locations.whataburger.com/directory.html']
    count=1

    api_headers = {
        'authority': 'api.whataburger.com',
        'x-device-fingerprint': '863a6567b9052bda53b876e4d416a70f',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
        'content-type': 'application/json',
        'accept': 'application/json',
        'x-client': 'SPA',
        'x-device-id': 'd34d932f-e136-5742-3c60-be4742104b50',
        'x-api-key': 'E08F3550-23FE-4360-BD6C-08314E6C3E2F',
        'referer': 'https://whataburger.com/',
        'accept-language': 'en-US,en;q=0.9'
    }

    def parse(self, response):
        states = response.xpath('//div[@class="Directory-content"]//li')
        for state in states:
            state_url = response.urljoin(state.xpath('.//a/@href').get(""))
            count = state.xpath('.//span/@data-count').get("") 
            if count == "(1)":
                yield scrapy.Request(state_url,callback=self.parse_details)
            else:
                yield scrapy.Request(state_url,callback=self.parse_cities)

    def parse_cities(self, response):
        cities = response.xpath('//div[@class="Directory-content"]//li')
        for city in cities:
            city_url = response.urljoin(city.xpath('.//a/@href').get(""))
            count = city.xpath('.//span/@data-count').get("")
            if count == "(1)":
                yield scrapy.Request(city_url,callback=self.parse_details)
            else:
                yield scrapy.Request(city_url,callback=self.parse_restaurants)

    def parse_restaurants(self, response):
        restaurants = response.xpath('//div[@class="Teaser-row Teaser-row--info"]')
        for restaurant in restaurants:
            restaurant_url = response.urljoin(restaurant.xpath('.//h2/a/@href').get(""))
            yield scrapy.Request(restaurant_url,callback=self.parse_details)

    def parse_details(self, response):
        restaurant_item = RestaurantItem()
        source_id = response.xpath('//span[@id="location-name"]/text()').get("")
        restaurant_item["source_id"] = source_id.split('#')[-1].strip()
        restaurant_item["location_name"] = response.xpath('//span[@class="Banner-titleGeo"]/text()').get("")
        restaurant_item["url"] = response.url
        restaurant_item["phone_number"] = response.xpath('//a[@class="Phone-link"]/text()').get("")
        restaurant_item["street_address_1"] = response.xpath('//span[@class="c-address-street-1"]/text()').get("")
        restaurant_item["city"] = response.xpath('//span[@class="c-address-city"]/text()').get("")
        restaurant_item["state"] = response.xpath('//span[@class="c-address-state"]/text()').get("")
        restaurant_item["postal_code"] = response.xpath('//span[@class="c-address-postal-code"]/text()').get("")
        restaurant_item["country"] = "US"
        restaurant_item["latitude"] = response.xpath('//meta[@itemprop="latitude"]/@content').get("")
        restaurant_item["longitude"] = response.xpath('//meta[@itemprop="longitude"]/@content').get("")
        restaurant_item["type"] = response.xpath('//ul[@class="Amenities"]/li//span[@itemprop="name"]/text()').getall()
        
        schedule = []
        for weekly_schedule in response.xpath('//div[@class="Core-hoursCol Text--extraSmall"]'):
            schedule_item = RestaurantScheduleItem()
            operation_type = weekly_schedule.xpath('./div[@class="Core-hoursHeadings"]/div/text()').get("")
            if operation_type == "Day":
                schedule_item["type"] = "DineIn"
            elif operation_type == "Drive Thru":
                schedule_item["type"] = "DriveThru"
            else:
                schedule_item["type"] = operation_type

            for day_schedule in weekly_schedule.xpath('.//table//tr[@itemprop="openingHours"]'):
                weekday = day_schedule.xpath('./td[@class="c-hours-details-row-day"]/text()').get("")
                weekday=parser.parse(weekday).strftime('%A')
                if weekday and weekday.lower() in ["sunday","monday","tuesday","wednesday","thursday","friday","saturday"]:
                    if day_schedule.xpath('./td[@class="c-hours-details-row-intervals"]/span/span'):
                        schedule_item[weekday.lower()] = ''.join(day_schedule.xpath('./td[@class="c-hours-details-row-intervals"]/span/span/text()').getall())
                    elif day_schedule.xpath('./td[@class="c-hours-details-row-intervals"]/span/text()'):   
                        schedule_item[weekday.lower()] = ''.join(day_schedule.xpath('./td[@class="c-hours-details-row-intervals"]/span/text()').getall())
                        
            schedule.append(schedule_item)
        restaurant_item["schedules"] = schedule

        location_url = f'https://api.whataburger.com/v2.4/locations?q={restaurant_item["source_id"]}&data=null'
     
        yield scrapy.Request(location_url,headers=self.api_headers,callback=self.parse_location_api,cb_kwargs={"restaurant_item": restaurant_item})

    async def parse_location_api(self, response, restaurant_item):
        json_data = json.loads(response.body)
    
        location_id = json_data["locations"][0]["id"]
          
        category_url = f'https://api.whataburger.com/v2.4/locations/{location_id}/menu/categories?data=null'
        category_response = await self.request_process(category_url)
    
        category_data=json.loads(category_response.text)
        
        menus = []
        for category in category_data:
            menu_item = RestaurantMenuItem()
            menu_item["source_category_id"] = category.get("id")
            menu_item["category_name"] = category.get("name")
         
            if menu_item["category_name"] == "Rewards" or menu_item["category_name"] == "Breakfast (available 11pm-11am)":
                continue

            product_url = f'https://api.whataburger.com/v2.4/locations//{location_id}/menu/categories/{menu_item["source_category_id"]}/recipes?data=null'
            product_response = await self.request_process(product_url)
           
            product_data = json.loads(product_response.text)

            product_list = []
            for product in product_data:
                parent_product_id = product.get("id")

                product_recipe_url = f"https://api.whataburger.com/v2.4/locations/{location_id}/menu/recipes/{parent_product_id}/child-recipes?data=null"
                product_recipe_response = await self.request_process(product_recipe_url)
                
                product_recipe_data = json.loads(product_recipe_response.text)

                for product_recipe in product_recipe_data.get("recipes"):
                    product_recipe_id = product_recipe.get("id")
                    product_slug = product_recipe_data.get("slug")
                 
                    product_child_recipe_url = f"https://api.whataburger.com/v2.4/locations/{location_id}/menu/child-recipes/{product_recipe_id}?data=null"
                    product_child_recipe_response = await self.request_process(product_child_recipe_url)

                    product_child_recipe_data = json.loads(product_child_recipe_response.text)
                    
                    if menu_item["category_name"] == "Burgers":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                        product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                        product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")

                        desc_list = []
                        for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for desc_mod in descript.get("modifierGroups"):
                                desc_select = desc_mod.get("isDefaultSelected")
                                if desc_select == True:
                                    desc_text = desc_mod.get("displayText")
                                    desc_list.append(desc_text)
                        desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                        product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                        if "meal" in product_item["product_name"] or "Meal" in product_item["product_name"]:
                            product_list.append(product_item)
                            self.count+=1

                        else:
                            base_options = []
                            base_item = RestaurantBaseItem()
                            base_item["description"] = "Default"
                            base_item["base"] = "Default"
                            base_item["base_price"] = ""
            
                            add_ons=[]
                            for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                if "Cheese" in addons.get("name") or "Popular Add-Ons" in addons.get("name"): 
                                    for addon in addons.get("modifierGroups"):
                                        add_on_item = RestaurantAddOnItem()
                                        add_on_item["add_on_name"] = addon.get("displayText")
                                        add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                        add_ons.append(add_on_item)

                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)    
                            product_item["base_options"] = base_options
                            product_list.append(product_item)
                            self.count+=1

                    elif menu_item["category_name"] == "All-Time Favorites":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                        product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                        product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")
                       
                        desc_list = []
                        for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for desc_mod in descript.get("modifierGroups"):
                                desc_select = desc_mod.get("isDefaultSelected")
                                if desc_select == True:
                                    desc_text = desc_mod.get("displayText")
                                    desc_list.append(desc_text)
                        desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                        product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                        if "meal" in product_item["product_name"] or "Meal" in product_item["product_name"]:
                            product_list.append(product_item)
                            self.count+=1

                        else:
                            base_options = []
                            base_item = RestaurantBaseItem()
                            base_item["description"] = "Default"
                            base_item["base"] = "Default"
                            base_item["base_price"] = ""
            
                            add_ons=[]
                            for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                if "Popular Add-Ons" in addons.get("name"): 
                                    for addon in addons.get("modifierGroups"):
                                        add_on_item = RestaurantAddOnItem()
                                        add_on_item["add_on_name"] = addon.get("displayText")
                                        add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                        add_ons.append(add_on_item)

                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)    
                            product_item["base_options"] = base_options
                            product_list.append(product_item)
                            self.count+=1

                    elif menu_item["category_name"] == "Chicken":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                        product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                        product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")

                        desc_list = []
                        for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for desc_mod in descript.get("modifierGroups"):
                                desc_select = desc_mod.get("isDefaultSelected")
                                if desc_select == True:
                                    desc_text = desc_mod.get("displayText")
                                    desc_list.append(desc_text)
                        desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                        product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                        if "meal" in product_item["product_name"] or "Meal" in product_item["product_name"]:
                            product_list.append(product_item)
                            self.count+=1

                        else:
                            base_options = []
                            base_item = RestaurantBaseItem()
                            base_item["description"] = "Default"
                            base_item["base"] = "Default"
                            base_item["base_price"] = ""
            
                            add_ons=[]
                            for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                if "Cheese" in addons.get("name") or "Popular Add-Ons" in addons.get("name"):
                                    if "Cheese (Included" in addons.get("name"):
                                        continue
                                    else:
                                        for addon in addons.get("modifierGroups"):
                                            add_on_item = RestaurantAddOnItem()
                                            add_on_item["add_on_name"] = addon.get("displayText")
                                            add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                            add_ons.append(add_on_item)

                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)    
                            product_item["base_options"] = base_options
                            product_list.append(product_item)
                            self.count+=1   

                    elif menu_item["category_name"] == "Fish":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                        product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                        product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")

                        desc_list = []
                        for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for desc_mod in descript.get("modifierGroups"):
                                desc_select = desc_mod.get("isDefaultSelected")
                                if desc_select == True:
                                    desc_text = desc_mod.get("displayText")
                                    desc_list.append(desc_text)
                        desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                        product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                        if "meal" in product_item["product_name"] or "Meal" in product_item["product_name"] or "Dinner" in product_item["product_name"]:
                            product_list.append(product_item)
                            self.count+=1

                        else:
                            base_options = []
                            base_item = RestaurantBaseItem()
                            base_item["description"] = "Default"
                            base_item["base"] = "Default"
                            base_item["base_price"] = ""
            
                            add_ons=[]
                            for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                if "Cheese" in addons.get("name") or "Popular Add-Ons" in addons.get("name"): 
                                    for addon in addons.get("modifierGroups"):
                                        add_on_item = RestaurantAddOnItem()
                                        add_on_item["add_on_name"] = addon.get("displayText")
                                        add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                        add_ons.append(add_on_item)

                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)    
                            product_item["base_options"] = base_options
                            product_list.append(product_item)
                            self.count+=1                                                 

                    elif menu_item["category_name"] == "Kids":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                        product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                        product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")

                        desc_list = []
                        for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for desc_mod in descript.get("modifierGroups"):
                                desc_select = desc_mod.get("isDefaultSelected")
                                if desc_select == True:
                                    desc_text = desc_mod.get("displayText")
                                    desc_list.append(desc_text)
                        desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                        product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  
                          
                        base_options = []
                        base_item = RestaurantBaseItem()
                        base_item["description"] = "Default"
                        base_item["base"] = "Default"
                        base_item["base_price"] = ""
        
                        add_ons=[]
                        for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            if "Cheese" in addons.get("name") or "Popular Add-Ons" in addons.get("name") or "Popular Add-ons" in addons.get("name") or "Dipping Sauces" in addons.get("name") or "Extras" in addons.get("name"): 
                                if addons.get("name") == "Dipping Sauce (Extras on Next Screen)":
                                    continue
                                else:
                                    for addon in addons.get("modifierGroups"):
                                        add_on_item = RestaurantAddOnItem()
                                        add_on_item["add_on_name"] = addon.get("displayText")
                                        add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                        add_ons.append(add_on_item)

                        base_item["add_ons"] = add_ons
                        base_options.append(base_item)    
                        product_item["base_options"] = base_options
                        product_list.append(product_item)
                        self.count+=1                  

                    elif menu_item["category_name"] == "Sides":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                        product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                        product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")

                        desc_list = []
                        for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for desc_mod in descript.get("modifierGroups"):
                                desc_select = desc_mod.get("isDefaultSelected")
                                if desc_select == True:
                                    desc_text = desc_mod.get("displayText")
                                    desc_list.append(desc_text)
                        desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                        product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'                         

                        if product_item["product_name"] == "Apple Slices":
                            product_list.append(product_item)
                            self.count+=1
                        else:
                            size_list = []
                            base_options = []
                            base_item = RestaurantBaseItem()
                            base_item["description"] = "Default"
                            base_item["base"] = "Default"
                            base_item["base_price"] = ""
                            add_ons=[]
                            size_groups = product_child_recipe_data.get("recipe").get("customizationGroups")[0].get("modifierGroups")
                            for size_group in size_groups:
                                for size in size_group.get("modifiers"):
                                    size_name = size.get("displayText")
                                    size_price = size.get("price")
                                    size_dict = {"size_name":size_name,"size_price":size_price}
                                    size_list.append(size_dict)
                            product_item["size"] = size_list
                            for addons in product_child_recipe_data.get("recipe").get("customizationGroups")[1:3]:
                                for addon in addons.get("modifierGroups"):
                                    add_on_item = RestaurantAddOnItem()
                                    add_on_item["add_on_name"] = addon.get("displayText")
                                    add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                    add_ons.append(add_on_item)
                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)    
                            product_item["base_options"] = base_options                                                        
                            product_list.append(product_item)
                            self.count+=1

                    elif menu_item["category_name"] == "Salads":         
                        if product_child_recipe_data.get("recipe").get("name") == "Buffalo Ranch Chicken Salad":
                            product_item = RestaurantProductItem()
                            product_item["sequence_number"] = self.count
                            product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                            product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                            product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")

                            desc_list = []
                            for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                for desc_mod in descript.get("modifierGroups"):
                                    desc_select = desc_mod.get("isDefaultSelected")
                                    if desc_select == True:
                                        desc_text = desc_mod.get("displayText")
                                        desc_list.append(desc_text)
                            desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                            product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                            ingre_id_list = []
                            mul_list = []
                            for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                for calor in calorie.get("modifierGroups"):
                                    calor_select = calor.get("isDefaultSelected")
                                    if calor_select == True:
                                        for calo in calor.get("modifiers"):
                                            calo_select = calo.get("isDefaultSelected")
                                            if calo_select == True:
                                                for cal in calo.get("ingredients"):
                                                    ingre_id = cal.get("ingredientId")
                                                    ingre_mul = cal.get("multiplier")
                                                    ingre_id_list.append(ingre_id)
                                                    mul_list.append(ingre_mul)
                            total_cal = []
                            for id,mul in zip(ingre_id_list,mul_list):
                                for ingre in product_child_recipe_data.get("ingredients"):
                                    ingred_id = ingre.get("id")
                                    if ingred_id == id:
                                        ingred_cal = ingre.get("nutritionInfo").get("calories")
                                        mul_cal = float(ingred_cal) * float(mul)
                                        total_cal.append(mul_cal)
                            final_cal = round(sum(i for i in total_cal))  
                            product_item["min_calories"] = final_cal        

                            image = product_child_recipe_data.get("recipe").get("imageUrl")
                            product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                            product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                            base_options = []
                            base_item = RestaurantBaseItem()
                            base_item["description"] = "Default"
                            base_item["base"] = "Default"
                            base_item["base_price"] = ""
            
                            add_ons=[]
                            for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                if "Popular Add-Ons" in addons.get("name"): 
                                    for addon in addons.get("modifierGroups"):
                                        add_on_item = RestaurantAddOnItem()
                                        add_on_item["add_on_name"] = addon.get("displayText")
                                        add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                        add_ons.append(add_on_item)

                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)    
                            product_item["base_options"] = base_options
                            product_list.append(product_item)
                            self.count+=1

                        else:
                            for chicken_type in product_child_recipe_data.get("recipe").get("customizationGroups")[0].get("modifierGroups"):
                                product_item = RestaurantProductItem()
                                product_item["sequence_number"] = self.count
                                product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                                product_item["product_name"] = product_child_recipe_data.get("recipe").get("name") + " " + chicken_type.get("displayText").strip()
                                product_item["price"] = chicken_type.get("modifiers")[0].get("price")

                                desc_list = []
                                for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                    for desc_mod in descript.get("modifierGroups"):
                                        desc_select = desc_mod.get("isDefaultSelected")
                                        if desc_select == True:
                                            desc_text = desc_mod.get("displayText")
                                            desc_list.append(desc_text)
                                desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                                desc = ", ".join(desc_list) + ". " + desc_string
                                product_item["description"] = desc.replace(desc.split(",")[0],chicken_type.get("displayText").strip())

                                ingre_id_list = []
                                mul_list = []
                                for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                    for calor in calorie.get("modifierGroups"):
                                        calor_select = calor.get("isDefaultSelected","")
                                        if calor_select == True:
                                            for calo in calor.get("modifiers"):
                                                calo_select = calo.get("isDefaultSelected")
                                                if calo_select == True:
                                                    for cal in calo.get("ingredients"):
                                                        ingre_id = cal.get("ingredientId")
                                                        ingre_mul = cal.get("multiplier")
                                                        ingre_id_list.append(ingre_id)
                                                        mul_list.append(ingre_mul)                       
                                total_cal = []
                                for id,mul in zip(ingre_id_list,mul_list):
                                    for ingre in product_child_recipe_data.get("ingredients"):
                                        ingred_id = ingre.get("id")
                                        if ingred_id == id:
                                            ingred_cal = ingre.get("nutritionInfo").get("calories")
                                            mul_cal = float(ingred_cal) * float(mul)
                                            total_cal.append(mul_cal)
                                final_cal = round(sum(i for i in total_cal))  
                                product_item["min_calories"] = final_cal

                                image = product_child_recipe_data.get("recipe").get("imageUrl")
                                product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                                product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                                base_options = []
                                base_item = RestaurantBaseItem()
                                base_item["description"] = "Default"
                                base_item["base"] = "Default"
                                base_item["base_price"] = ""
                
                                add_ons=[]
                                for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                    if "Popular Add-Ons" in addons.get("name"): 
                                        for addon in addons.get("modifierGroups"):
                                            add_on_item = RestaurantAddOnItem()
                                            add_on_item["add_on_name"] = addon.get("displayText")
                                            add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                            add_ons.append(add_on_item)

                                base_item["add_ons"] = add_ons
                                base_options.append(base_item)    
                                product_item["base_options"] = base_options
                                product_list.append(product_item)
                                self.count+=1

                    elif menu_item["category_name"] == "Desserts & Snacks":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")

                        name = product_child_recipe_data.get("recipe").get("name")
                        if name == "Cinnamon Roll":
                            size_list = []
                            size_groups = product_child_recipe_data.get("recipe").get("customizationGroups")[0].get("modifierGroups")
                            if len(size_groups) > 0:
                                for size_group in size_groups:
                                    desc_list = []
                                    size_name = size_group.get("displayText")
                                    size_price = size_group.get("modifiers")[0].get("price")
                                    desc_text = size_group.get("displayText")
                                    desc_list.append(desc_text)
                                    desc_string = product_child_recipe_data.get("recipe").get("comesWithText","") 
                                    description = ", ".join(desc_list) + ". " + desc_string
                                    size_dict = {"size_name":size_name,"size_price":size_price,"description":description}
                                    size_list.append(size_dict)
                                product_item["size"] = size_list
                                product_item["product_name"] = name
                        else:    
                            product_item["product_name"] = name
                            product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")
                        
                            desc_list = []
                            for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                for desc_mod in descript.get("modifierGroups"):
                                    desc_select = desc_mod.get("isDefaultSelected")
                                    if desc_select == True:
                                        desc_text = desc_mod.get("displayText")
                                        desc_list.append(desc_text)
                            desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                            product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'    
                        product_list.append(product_item)
                        self.count+=1

                    elif menu_item["category_name"] == "Drinks & Shakes":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                        product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")

                        ingre_id_list = []
                        mul_list = []
                        for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                            for calor in calorie.get("modifierGroups"):
                                calor_select = calor.get("isDefaultSelected")
                                if calor_select == True:
                                    for calo in calor.get("modifiers"):
                                        calo_select = calo.get("isDefaultSelected")
                                        if calo_select == True:
                                            for cal in calo.get("ingredients"):
                                                ingre_id = cal.get("ingredientId")
                                                ingre_mul = cal.get("multiplier")
                                                ingre_id_list.append(ingre_id)
                                                mul_list.append(ingre_mul)
                        total_cal = []
                        for id,mul in zip(ingre_id_list,mul_list):
                            for ingre in product_child_recipe_data.get("ingredients"):
                                ingred_id = ingre.get("id")
                                if ingred_id == id:
                                    ingred_cal = ingre.get("nutritionInfo").get("calories")
                                    mul_cal = float(ingred_cal) * float(mul)
                                    total_cal.append(mul_cal)
                        final_cal = round(sum(i for i in total_cal))  
                        product_item["min_calories"] = final_cal        

                        image = product_child_recipe_data.get("recipe").get("imageUrl")
                        product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                        product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'                          

                        size_flavour_groups = product_child_recipe_data.get("recipe").get("customizationGroups")[0].get("modifierGroups")
                        size_flavour_list = []
                        for size_flavour_group in size_flavour_groups:
                            desc_list = []
                            desc_text = size_flavour_group.get("displayText")
                            desc_list.append(desc_text)
                            desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")              

                            for size_flavour in size_flavour_group.get("modifiers"):   
                                flavour = size_flavour_group.get("displayText")
                                if product_item["product_name"] == "Honest Apple Juice" or product_item["product_name"] == "Simply Orange® Juice":
                                    flavour = ""
                                else:
                                    flavour = flavour    
                                size_name = size_flavour.get("displayText")
                                if product_item["product_name"] == "Honest Apple Juice" or product_item["product_name"] == "Simply Orange® Juice" or product_item["product_name"] == "Milk":
                                    size_name = ""
                                else:
                                    size_name = size_name    
                                size_price = size_flavour.get("price")
                                description = ", ".join(desc_list) + " " + size_name + ". " + desc_string
                                size_flavour_dict = {"flavour":flavour,"size_name":size_name,"size_price":size_price,"description":description}
                                size_flavour_list.append(size_flavour_dict)
                        product_item["size_flavour_list"] = size_flavour_list                      

                        product_list.append(product_item)
                        self.count+=1   

                    elif menu_item["category_name"] == "Lighter & Smaller":
                        if "Salad" in product_child_recipe_data.get("recipe").get("name"):
                            for chicken_type in product_child_recipe_data.get("recipe").get("customizationGroups")[0].get("modifierGroups"):
                                product_item = RestaurantProductItem()
                                product_item["sequence_number"] = self.count
                                product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                                product_item["product_name"] = product_child_recipe_data.get("recipe").get("name") + " " + chicken_type.get("displayText").strip()
                                product_item["price"] = chicken_type.get("modifiers")[0].get("price")

                                desc_list = []
                                for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                    for desc_mod in descript.get("modifierGroups"):
                                        desc_select = desc_mod.get("isDefaultSelected")
                                        if desc_select == True:
                                            desc_text = desc_mod.get("displayText")
                                            desc_list.append(desc_text)
                                desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                                desc = ", ".join(desc_list) + ". " + desc_string
                                product_item["description"] = desc.replace(desc.split(",")[0],chicken_type.get("displayText").strip())

                                ingre_id_list = []
                                mul_list = []
                                for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                    for calor in calorie.get("modifierGroups"):
                                        calor_select = calor.get("isDefaultSelected","")
                                        if calor_select == True:
                                            for calo in calor.get("modifiers"):
                                                calo_select = calo.get("isDefaultSelected")
                                                if calo_select == True:
                                                    for cal in calo.get("ingredients"):
                                                        ingre_id = cal.get("ingredientId")
                                                        ingre_mul = cal.get("multiplier")
                                                        ingre_id_list.append(ingre_id)
                                                        mul_list.append(ingre_mul)                       
                                total_cal = []
                                for id,mul in zip(ingre_id_list,mul_list):
                                    for ingre in product_child_recipe_data.get("ingredients"):
                                        ingred_id = ingre.get("id")
                                        if ingred_id == id:
                                            ingred_cal = ingre.get("nutritionInfo").get("calories")
                                            mul_cal = float(ingred_cal) * float(mul)
                                            total_cal.append(mul_cal)
                                final_cal = round(sum(i for i in total_cal))  
                                product_item["min_calories"] = final_cal        

                                image = product_child_recipe_data.get("recipe").get("imageUrl")
                                product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                                product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                                base_options = []
                                base_item = RestaurantBaseItem()
                                base_item["description"] = "Default"
                                base_item["base"] = "Default"
                                base_item["base_price"] = ""
                
                                add_ons=[]
                                for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                    if "Popular Add-Ons" in addons.get("name"): 
                                        for addon in addons.get("modifierGroups"):
                                            add_on_item = RestaurantAddOnItem()
                                            add_on_item["add_on_name"] = addon.get("displayText")
                                            add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                            add_ons.append(add_on_item)

                                base_item["add_ons"] = add_ons
                                base_options.append(base_item)    
                                product_item["base_options"] = base_options
                                product_list.append(product_item)
                                self.count+=1                            

                        else:
                            product_item = RestaurantProductItem()
                            product_item["sequence_number"] = self.count
                            product_item["source_product_id"] = product_child_recipe_data.get("recipe").get("id")
                            product_item["product_name"] = product_child_recipe_data.get("recipe").get("name")
                            product_item["price"] = product_child_recipe_data.get("recipe").get("recipeBasicInfo").get("price")

                            desc_list = []
                            for descript in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                for desc_mod in descript.get("modifierGroups"):
                                    desc_select = desc_mod.get("isDefaultSelected")
                                    if desc_select == True:
                                        desc_text = desc_mod.get("displayText")
                                        desc_list.append(desc_text)
                            desc_string = product_child_recipe_data.get("recipe").get("comesWithText","")            
                            product_item["description"] = ", ".join(desc_list) + ". " + desc_string

                            ingre_id_list = []
                            mul_list = []
                            for calorie in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                for calor in calorie.get("modifierGroups"):
                                    calor_select = calor.get("isDefaultSelected")
                                    if calor_select == True:
                                        for calo in calor.get("modifiers"):
                                            calo_select = calo.get("isDefaultSelected")
                                            if calo_select == True:
                                                for cal in calo.get("ingredients"):
                                                    ingre_id = cal.get("ingredientId")
                                                    ingre_mul = cal.get("multiplier")
                                                    ingre_id_list.append(ingre_id)
                                                    mul_list.append(ingre_mul)
                            total_cal = []
                            for id,mul in zip(ingre_id_list,mul_list):
                                for ingre in product_child_recipe_data.get("ingredients"):
                                    ingred_id = ingre.get("id")
                                    if ingred_id == id:
                                        ingred_cal = ingre.get("nutritionInfo").get("calories")
                                        mul_cal = float(ingred_cal) * float(mul)
                                        total_cal.append(mul_cal)
                            final_cal = round(sum(i for i in total_cal))  
                            product_item["min_calories"] = final_cal        

                            image = product_child_recipe_data.get("recipe").get("imageUrl")
                            product_item["product_image"] = f"https://wbimageserver.whataburger.com//food/{image}"
                            product_item["url"] = f'https://whataburger.com/locations/{restaurant_item["source_id"]}/menu/categories/{menu_item["category_name"].lower()}-{menu_item["source_category_id"]}/recipes/{product_slug}-{parent_product_id}/customization/{menu_item["source_category_id"]}'  

                            if "meal" in product_item["product_name"] or "Meal" in product_item["product_name"] or "Cinnamon Roll" in product_item["product_name"]:
                                product_list.append(product_item)
                                self.count+=1

                            else:
                                base_options = []
                                base_item = RestaurantBaseItem()
                                base_item["description"] = "Default"
                                base_item["base"] = "Default"
                                base_item["base_price"] = ""
                
                                add_ons=[]
                                for addons in product_child_recipe_data.get("recipe").get("customizationGroups"):
                                    if "Cheese" in addons.get("name") or "Popular Add-Ons" in addons.get("name") or "Ranchero" in addons.get("name") or "Dipping Sauces" in addons.get("name") or "Extras" in addons.get("name"): 
                                        if "Cheese (Included" in addons.get("name"):
                                            continue
                                        else:
                                            for addon in addons.get("modifierGroups"):
                                                add_on_item = RestaurantAddOnItem()
                                                add_on_item["add_on_name"] = addon.get("displayText")
                                                add_on_item["price"] = addon.get("modifiers")[0]["price"]       
                                                add_ons.append(add_on_item)

                                base_item["add_ons"] = add_ons
                                base_options.append(base_item)    
                                product_item["base_options"] = base_options
                                product_list.append(product_item)
                                self.count+=1                        

            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus
        self.count=1
        yield restaurant_item
            
    async def request_process(self, url):
        request = scrapy.Request(url, headers=self.api_headers)
        response = await self.crawler.engine.download(request, self)

        return response
