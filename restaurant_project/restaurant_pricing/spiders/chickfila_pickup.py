import scrapy
import json
import re
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem
)

class ChickFilAPickupSpider(scrapy.Spider):
    name = 'chickfilapickup'
    start_urls = ['https://www.chick-fil-a.com/locations/browse']
    count=1
   
    def parse(self, response):
        state_urls = response.xpath('//article[@class="wrapper"]/ul/li/a/@href').getall()
        yield from response.follow_all(state_urls,callback=self.parse_locations)

    def parse_locations(self, response):
        restaurant_urls = response.xpath('//div[@class="location"]/h2/a/@href').getall()
        yield from response.follow_all(restaurant_urls,callback=self.parse_details)

    def parse_details(self, response):
        restaurant_item = RestaurantItem()
        restaurant_item["source_id"] = response.xpath('//div[@class="icon-wrapper"]/@data-clientkey').get("")
        restaurant_item["location_name"] = response.xpath('//h1/text()').get("")
        restaurant_item["url"] = response.url
        restaurant_item["phone_number"] = response.xpath('//div[@class="rail-module store-number "]/p/a/text()').get("")
        street_address = response.xpath('//p[@class="address"]/text()').get("").strip()
        address = response.xpath('//p[@class="address"]/br/following::text()[1]').get("").strip()
        if address == "":
            restaurant_item["street_address_1"] = street_address.split(",")[0].strip()
            restaurant_item["city"] = street_address.split(",")[1].strip()
            restaurant_item["state"] = street_address.split(",")[-1].strip().split(" ")[0]
            restaurant_item["postal_code"] = street_address.split(",")[-1].strip().split(" ")[-1]
        else:    
            restaurant_item["street_address_1"] = street_address
            restaurant_item["city"] = address.split(",")[0]
            restaurant_item["state"] = address.split(",")[-1].strip().split(" ")[0]
            restaurant_item["postal_code"] = address.split(",")[-1].strip().split(" ")[-1]
        restaurant_item["country"] = "US"
    
        operation_type = response.xpath('//ul[@class="location-service-hours "]/li//div[@class="icon-wrapper"]/following-sibling::p/text()').getall()
        restaurant_item["type"] = [operat_type.strip() for operat_type in operation_type]

        schedules_list = []
        for schedules in response.xpath('//h3[contains(text(),"Hours")]/following-sibling::div'):
            schedule = " : ".join(schedules.xpath('./p/text()').getall())
            schedules_list.append(schedule)
        restaurant_item["schedules_chickfila"] = "|".join(schedules_list)

        menu_url = f'https://order.api.my.chick-fil-a.com/orders/locations/3.1/{restaurant_item["source_id"]}/menu/client/individual'

        yield scrapy.Request(menu_url,callback=self.parse_menus,cb_kwargs={"restaurant_item": restaurant_item})

    async def parse_menus(self, response, restaurant_item):
        data = json.loads(response.text)

        calories_url = f'https://order.api.my.chick-fil-a.com/orders/locations/2.0/{restaurant_item["source_id"]}/menu/client/nutrition?language=en-US'
        calories_response = await self.request_process(calories_url)
        calories_data = json.loads(calories_response.text)

        menus = []
        for category in data.get("categories"):
            menu_item = RestaurantMenuItem()
            menu_item["category_name"] = category.get("name")
           
            if menu_item["category_name"] == "Breakfast": #to skip the mentioned category as it is not required
                continue

            product_list = []
            if menu_item["category_name"] == "Meals":  #add-ons required
                for product in category.get("items"):
                    if product.get("itemPrice") != 0:
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["product_name"] = product.get("name")
                        product_item["price"] = product.get("itemPrice")

                        if product_item["product_name"] == "Chick-fil-A® Spicy Chicken Sandwich Meal" or product_item["product_name"] == "Grilled Chicken Sandwich Meal":
                            cal_description = product.get("description") 
                            for calories_info in calories_data.get("items"):
                                if calories_info.get("description") == None:
                                    continue
                                else: 
                                    if cal_description == calories_info.get("description").strip():
                                        product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                        else:    
                            mobile_image = product.get("mobileImage")
                            for calories_info in calories_data.get("items"):
                                if mobile_image == calories_info.get("mobileImage"):
                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                        if "Ct" in product_item["product_name"]:
                            product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                        else:
                            product_item["pc_count"] = 1
                       
                        categories_itemgroupid = product.get("itemGroupId") 
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items")[0:1]:
                                    product_item["description"] = itemgroup.get("description")

                        product_item["product_image"] = product.get("desktopImage") 
                        category_tag = category.get("tag").replace("_","-").lower() 
                        product_tag = product.get("tag").replace("_","-").lower()
                        product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                        
                        if product_item["product_name"] == "Chick-fil-A® Cool Wrap Meal":
                            product_list.append(product_item)
                            self.count+=1
                        else:
                            base_options = []
                            for base_itemgroups in data.get("itemGroups"):
                                base_itemgroupsid = base_itemgroups.get("itemGroupId")
                                if categories_itemgroupid == base_itemgroupsid:
                                    base_itemgroups_id = base_itemgroups.get("items")[0].get("itemGroupId")
                                    for base_itemgroup in data.get("itemGroups"):
                                        base_itemgroup_id = base_itemgroup.get("itemGroupId")
                                        if base_itemgroups_id == base_itemgroup_id:
                                            for base_group in base_itemgroup.get("items"):
                                                if "Bread" in base_group.get("name"):
                                                    base_option_id = base_group.get("itemGroupId")
                                                    for base_optiongroups in data.get("itemGroups"):
                                                        base_optiongroupid = base_optiongroups.get("itemGroupId")
                                                        if base_option_id == base_optiongroupid:
                                                            for base_optiongroup in base_optiongroups.get("items"):
                                                                if base_optiongroup.get("modifierType") == "RECIPE":
                                                                    continue
                                                                else:
                                                                    base_item = RestaurantBaseItem()
                                                                    base_item["description"] = ""
                                                                    base_item["base"] = base_optiongroup.get("name")
                                                                    base_item["base_price"] = base_optiongroup.get("itemPrice")
                                                            
                                                                add_ons=[]
                                                                for addon_itemgroups in data.get("itemGroups"):
                                                                    addon_itemgroupsid = addon_itemgroups.get("itemGroupId")
                                                                    if categories_itemgroupid == addon_itemgroupsid:
                                                                        addon_itemgroups_id = addon_itemgroups.get("items")[0].get("itemGroupId")
                                                                        for addon_itemgroup in data.get("itemGroups"):
                                                                            addon_itemgroup_id = addon_itemgroup.get("itemGroupId")
                                                                            if addon_itemgroups_id == addon_itemgroup_id:
                                                                                for addon_group in addon_itemgroup.get("items"):
                                                                                    if "Bread" in addon_group.get("name"):
                                                                                        continue
                                                                                    else:
                                                                                        addon_option_id = addon_group.get("itemGroupId")
                                                                                        for addon_optiongroups in data.get("itemGroups"):
                                                                                            addon_optiongroupid = addon_optiongroups.get("itemGroupId")
                                                                                            if addon_option_id == addon_optiongroupid:
                                                                                                for addon_optiongroup in addon_optiongroups.get("items"):
                                                                                                    if addon_optiongroup.get("modifierType") == "RECIPE":
                                                                                                        continue
                                                                                                    else:
                                                                                                        add_on_item = RestaurantAddOnItem()
                                                                                                        add_on_item["add_on_name"] = addon_optiongroup.get("name")
                                                                                                        add_on_item["price"] = addon_optiongroup.get("itemPrice")
                                                                                                        add_ons.append(add_on_item)                                                                           
                                                                base_item["add_ons"] = add_ons
                                                                base_options.append(base_item)                       
                            product_item["base_options"] = base_options
                            product_list.append(product_item)
                            self.count+=1
                    else:
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items"):
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")   

                                    if product_item["product_name"] == "Club w/ No Cheese Meal":
                                        cal_description = product.get("description").strip().lower()
                                        for calories_info in calories_data.get("items"):
                                            if calories_info.get("description") == None:
                                                continue
                                            else: 
                                                if cal_description == calories_info.get("description").strip().lower():
                                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")         
                                    elif "No Cheese" in product_item["product_name"]:
                                        cal_description = itemgroup.get("description").strip().lower()
                                        for calories_info in calories_data.get("items"):
                                            if calories_info.get("description") == None:
                                                continue
                                            else: 
                                                if cal_description == calories_info.get("description").strip().lower():
                                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                                    else:    
                                        mobile_image = itemgroup.get("mobileImage")
                                        for calories_info in calories_data.get("items"):
                                            if mobile_image == calories_info.get("mobileImage"):
                                                product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")    
                                            
                                    if "Ct" in product_item["product_name"]:
                                        product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                                    else:
                                        product_item["pc_count"] = 1
                                   
                                    product_item["description"] = itemgroup.get("description")
                                    if product_item["description"] == None:
                                        product_item["description"] = product.get("description")  #for product "Grilled Chicken Club Meal"
                                    else:
                                        product_item["description"] = product_item["description"]   

                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    if product_item["product_image"] == None:
                                        product_item["product_image"] = product.get("desktopImage")  #for product "Spicy Chicken Sandwich Deluxe Meal"
                                    else:
                                        product_item["product_image"] = product_item["product_image"]

                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                   
                                    if "Ct" in product_item["product_name"]:
                                        product_list.append(product_item)
                                        self.count+=1
                                    else:    
                                        for base_itemgroups in data.get("itemGroups"):
                                            base_itemgroupsid = base_itemgroups.get("itemGroupId")
                                            if categories_itemgroupid == base_itemgroupsid:
                                                for base_item_group in base_itemgroups.get("items"):  #new line for this template
                                                    base_itemgroups_id = base_item_group.get("itemGroupId")
                                                    for base_itemgroup in data.get("itemGroups"):
                                                        base_itemgroup_id = base_itemgroup.get("itemGroupId")
                                                        if base_itemgroups_id == base_itemgroup_id:
                                                            for base_group in base_itemgroup.get("items"):
                                                                base_group_uniqueid = base_group.get("itemGroupId")
                                                                for base_group_unique in data.get("itemGroups"):
                                                                    base_groupid_unique = base_group_unique.get("itemGroupId")
                                                                    if base_group_uniqueid == base_groupid_unique:                             
                                                                        for base_groups_unique in base_group_unique.get("items"):
                                                                            if "Bread" in base_groups_unique.get("name"):
                                                                                base_option_id = base_groups_unique.get("itemGroupId")
                                                                                base_options = []
                                                                                for base_optiongroups in data.get("itemGroups"):
                                                                                    base_optiongroupid = base_optiongroups.get("itemGroupId")
                                                                                    if base_option_id == base_optiongroupid:
                                                                                        for base_optiongroup in base_optiongroups.get("items"):
                                                                                            if base_optiongroup.get("modifierType") == "RECIPE":
                                                                                                continue
                                                                                            else:
                                                                                                base_item = RestaurantBaseItem()
                                                                                                base_item["description"] = ""
                                                                                                base_item["base"] = base_optiongroup.get("name")
                                                                                                base_item["base_price"] = base_optiongroup.get("itemPrice")
                                                                                
                                                                                            for addon_itemgroups in data.get("itemGroups"):
                                                                                                addon_itemgroupsid = addon_itemgroups.get("itemGroupId")
                                                                                                if categories_itemgroupid == addon_itemgroupsid:
                                                                                                    for addon_item_group in addon_itemgroups.get("items"):  #new line for this template
                                                                                                        addon_itemgroups_id = addon_item_group.get("itemGroupId")
                                                                                                        for addon_itemgroup in data.get("itemGroups"):
                                                                                                            addon_itemgroup_id = addon_itemgroup.get("itemGroupId")
                                                                                                            if addon_itemgroups_id == addon_itemgroup_id:                                                                                                           
                                                                                                                addon_group_uniqueid = addon_itemgroup.get("items")[0].get("itemGroupId")
                                                                                                                for addon_group_unique in data.get("itemGroups"):
                                                                                                                    addon_groupid_unique = addon_group_unique.get("itemGroupId")
                                                                                                                    if addon_group_uniqueid == addon_groupid_unique:
                                                                                                                        add_ons=[]
                                                                                                                        for addon_groups_unique in addon_group_unique.get("items"):
                                                                                                                            if "Bread" in addon_groups_unique.get("name"):
                                                                                                                                continue
                                                                                                                            else:
                                                                                                                                addon_option_id = addon_groups_unique.get("itemGroupId")
                                                                                                                                for addon_optiongroups in data.get("itemGroups"):
                                                                                                                                    addon_optiongroupid = addon_optiongroups.get("itemGroupId")
                                                                                                                                    if addon_option_id == addon_optiongroupid:
                                                                                                                                        for addon_optiongroup in addon_optiongroups.get("items"):
                                                                                                                                            if addon_optiongroup.get("modifierType") == "RECIPE":
                                                                                                                                                continue
                                                                                                                                            else:
                                                                                                                                                add_on_item = RestaurantAddOnItem()
                                                                                                                                                add_on_item["add_on_name"] = addon_optiongroup.get("name")
                                                                                                                                                add_on_item["price"] = addon_optiongroup.get("itemPrice")
                                                                                                                                                add_ons.append(add_on_item)
                                                                                            base_item["add_ons"] = add_ons
                                                                                            base_options.append(base_item)
                                        product_item["base_options"] = base_options
                                        product_list.append(product_item)
                                        self.count+=1

            elif menu_item["category_name"] == "Entrées":  #add-ons required
                for product in category.get("items"):
                    if product.get("itemPrice") != 0:
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["product_name"] = product.get("name")
                        product_item["price"] = product.get("itemPrice")

                        for calories_info in calories_data.get("items"):
                            if product_item["product_name"] == calories_info.get("name"):
                                product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                     
                        if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                            product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                        else:
                            product_item["pc_count"] = 1
                       
                        product_item["description"] = product.get("description")
                        product_item["product_image"] = product.get("desktopImage") 
                        category_tag = category.get("tag").replace("_","-").lower() 
                        product_tag = product.get("tag").replace("_","-").lower()
                        product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                        
                        categories_itemgroupid = product.get("itemGroupId")  #new line for this template

                        if product_item["product_name"] == "Chick-fil-A® Cool Wrap Meal" or product_item["product_name"] == "Gluten Free Bun":
                            product_list.append(product_item)
                            self.count+=1
                        else:
                            base_options = []
                            for base_itemgroups in data.get("itemGroups"):
                                base_itemgroupsid = base_itemgroups.get("itemGroupId")
                                if categories_itemgroupid == base_itemgroupsid:                                                                    
                                    for base_group in base_itemgroups.get("items"): #modified line
                                        if "Bread" in base_group.get("name"):
                                            base_option_id = base_group.get("itemGroupId")
                                            for base_optiongroups in data.get("itemGroups"):
                                                base_optiongroupid = base_optiongroups.get("itemGroupId")
                                                if base_option_id == base_optiongroupid:
                                                    for base_optiongroup in base_optiongroups.get("items"):
                                                        if base_optiongroup.get("modifierType") == "RECIPE":
                                                            continue
                                                        else:
                                                            base_item = RestaurantBaseItem()
                                                            base_item["description"] = ""
                                                            base_item["base"] = base_optiongroup.get("name")
                                                            base_item["base_price"] = base_optiongroup.get("itemPrice")
                                                            
                                                        add_ons=[]
                                                        for addon_itemgroups in data.get("itemGroups"):
                                                            addon_itemgroupsid = addon_itemgroups.get("itemGroupId")
                                                            if categories_itemgroupid == addon_itemgroupsid:                                                            
                                                                for addon_group in addon_itemgroups.get("items"):
                                                                    if "Bread" in addon_group.get("name"):
                                                                        continue
                                                                    else:
                                                                        addon_option_id = addon_group.get("itemGroupId")
                                                                        for addon_optiongroups in data.get("itemGroups"):
                                                                            addon_optiongroupid = addon_optiongroups.get("itemGroupId")
                                                                            if addon_option_id == addon_optiongroupid:
                                                                                for addon_optiongroup in addon_optiongroups.get("items"):
                                                                                    if addon_optiongroup.get("modifierType") == "RECIPE":
                                                                                        continue
                                                                                    else:
                                                                                        add_on_item = RestaurantAddOnItem()
                                                                                        add_on_item["add_on_name"] = addon_optiongroup.get("name")
                                                                                        add_on_item["price"] = addon_optiongroup.get("itemPrice")
                                                                                        add_ons.append(add_on_item)                                                                           
                                                        base_item["add_ons"] = add_ons
                                                        base_options.append(base_item)                       
                            product_item["base_options"] = base_options
                            product_list.append(product_item)
                            self.count+=1
                    else:
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items"):
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")   

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                                        product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                                    else:
                                        product_item["pc_count"] = 1

                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    
                                    if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                                        product_list.append(product_item)
                                        self.count+=1
                                    elif product_item["product_name"] == "Chick-fil-A® Filet" or product_item["product_name"] == "Grilled Filet" or product_item["product_name"] == "Spicy Filet":  #new template
                                        base_options = []
                                        base_item = RestaurantBaseItem()
                                        base_item["description"] = "Default"
                                        base_item["base"] = "Default"
                                        base_item["base_price"] = "" 
                                        
                                        for addon_itemgroups in data.get("itemGroups"):
                                            addon_itemgroupsid = addon_itemgroups.get("itemGroupId")
                                            if categories_itemgroupid == addon_itemgroupsid:
                                                for addon_item_group in addon_itemgroups.get("items"):  #new line for this template
                                                    addon_itemgroups_id = addon_item_group.get("itemGroupId")
                                                    for addon_itemgroup in data.get("itemGroups"):
                                                        addon_itemgroup_id = addon_itemgroup.get("itemGroupId")
                                                        if addon_itemgroups_id == addon_itemgroup_id:                                                                                                                                                                  
                                                            add_ons=[]
                                                            for addon_groups_unique in addon_itemgroup.get("items"):  #modified line                                            
                                                                addon_option_id = addon_groups_unique.get("itemGroupId")
                                                                for addon_optiongroups in data.get("itemGroups"):
                                                                    addon_optiongroupid = addon_optiongroups.get("itemGroupId")
                                                                    if addon_option_id == addon_optiongroupid:
                                                                        for addon_optiongroup in addon_optiongroups.get("items"):
                                                                            if addon_optiongroup.get("modifierType") == "RECIPE":
                                                                                continue
                                                                            else:
                                                                                add_on_item = RestaurantAddOnItem()
                                                                                add_on_item["add_on_name"] = addon_optiongroup.get("name")
                                                                                add_on_item["price"] = addon_optiongroup.get("itemPrice")
                                                                                add_ons.append(add_on_item)                                                   
                                        base_item["add_ons"] = add_ons
                                        base_options.append(base_item)
                                        product_item["base_options"] = base_options
                                        product_list.append(product_item)   
                                        self.count+=1                                     
                                    else:    
                                        for base_itemgroups in data.get("itemGroups"):
                                            base_itemgroupsid = base_itemgroups.get("itemGroupId")
                                            if categories_itemgroupid == base_itemgroupsid:
                                                for base_item_group in base_itemgroups.get("items"):  #new line for this template
                                                    base_itemgroups_id = base_item_group.get("itemGroupId")
                                                    for base_itemgroup in data.get("itemGroups"):
                                                        base_itemgroup_id = base_itemgroup.get("itemGroupId")
                                                        if base_itemgroups_id == base_itemgroup_id:                                                                                                                                           
                                                            for base_groups_unique in base_itemgroup.get("items"):  #modified line
                                                                if "Bread" in base_groups_unique.get("name"):
                                                                    base_option_id = base_groups_unique.get("itemGroupId")
                                                                    base_options = []
                                                                    for base_optiongroups in data.get("itemGroups"):
                                                                        base_optiongroupid = base_optiongroups.get("itemGroupId")
                                                                        if base_option_id == base_optiongroupid:
                                                                            for base_optiongroup in base_optiongroups.get("items"):
                                                                                if base_optiongroup.get("modifierType") == "RECIPE":
                                                                                    continue
                                                                                else:
                                                                                    base_item = RestaurantBaseItem()
                                                                                    base_item["description"] = ""
                                                                                    base_item["base"] = base_optiongroup.get("name")
                                                                                    base_item["base_price"] = base_optiongroup.get("itemPrice")
                                                                   
                                                                                for addon_itemgroups in data.get("itemGroups"):
                                                                                    addon_itemgroupsid = addon_itemgroups.get("itemGroupId")
                                                                                    if categories_itemgroupid == addon_itemgroupsid:
                                                                                        for addon_item_group in addon_itemgroups.get("items"):  #new line for this template
                                                                                            addon_itemgroups_id = addon_item_group.get("itemGroupId")
                                                                                            for addon_itemgroup in data.get("itemGroups"):
                                                                                                addon_itemgroup_id = addon_itemgroup.get("itemGroupId")
                                                                                                if addon_itemgroups_id == addon_itemgroup_id:                                                                                                                                                                                               
                                                                                                    add_ons=[]
                                                                                                    for addon_groups_unique in addon_itemgroup.get("items"):  #modified line
                                                                                                        if "Bread" in addon_groups_unique.get("name"):
                                                                                                            continue
                                                                                                        else:
                                                                                                            addon_option_id = addon_groups_unique.get("itemGroupId")
                                                                                                            for addon_optiongroups in data.get("itemGroups"):
                                                                                                                addon_optiongroupid = addon_optiongroups.get("itemGroupId")
                                                                                                                if addon_option_id == addon_optiongroupid:
                                                                                                                    for addon_optiongroup in addon_optiongroups.get("items"):
                                                                                                                        if addon_optiongroup.get("modifierType") == "RECIPE":
                                                                                                                            continue
                                                                                                                        else:
                                                                                                                            add_on_item = RestaurantAddOnItem()
                                                                                                                            add_on_item["add_on_name"] = addon_optiongroup.get("name")
                                                                                                                            add_on_item["price"] = addon_optiongroup.get("itemPrice")
                                                                                                                            add_ons.append(add_on_item)                                
                                                                                base_item["add_ons"] = add_ons
                                                                                base_options.append(base_item)
                                        product_item["base_options"] = base_options
                                        product_list.append(product_item)
                                        self.count+=1

            elif menu_item["category_name"] == "Sides":  #add-ons not needed
                for product in category.get("items"):
                    if product.get("itemPrice") != 0:
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["product_name"] = product.get("name")
                        product_item["price"] = product.get("itemPrice")

                        for calories_info in calories_data.get("items"):
                            if product_item["product_name"] == calories_info.get("name"):
                                product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                        if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                            product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                        else:
                            product_item["pc_count"] = 1
                       
                        product_item["description"] = product.get("description")
                        product_item["product_image"] = product.get("desktopImage") 
                        category_tag = category.get("tag").replace("_","-").lower() 
                        product_tag = product.get("tag").replace("_","-").lower()
                        product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                        product_list.append(product_item)
                        self.count+=1
                    elif product.get("name") == "Greek Yogurt Parfait":
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items")[0:1]:  #only one option is required for this product
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")   

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    product_item["pc_count"] = 1
                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    product_list.append(product_item)   
                                    self.count+=1 
                    else:
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items"):
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")   

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                                        product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                                    else:
                                        product_item["pc_count"] = 1

                                    if "Small" in product_item["product_name"] or "Medium" in product_item["product_name"] or "Large" in product_item["product_name"]:
                                        product_item["size"] = product_item["product_name"].split(" ")[0]

                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    product_list.append(product_item)
                                    self.count+=1

            elif menu_item["category_name"] == "Beverages":  #add-ons not needed #Cup of Water, Iced Coffee have different template
                for product in category.get("items"):
                    if product.get("name") == "Cup of Water":
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["product_name"] = product.get("name")
                        product_item["price"] = product.get("itemPrice")

                        for calories_info in calories_data.get("items"):
                            if product_item["product_name"] == calories_info.get("name"):
                                product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                        product_item["pc_count"] = 1
                        product_item["description"] = product.get("description")
                        product_item["product_image"] = product.get("desktopImage") 
                        category_tag = category.get("tag").replace("_","-").lower() 
                        product_tag = product.get("tag").replace("_","-").lower()
                        product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                        product_list.append(product_item) 
                        self.count+=1
                    elif product.get("name") == "Iced Coffee":
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items")[0:1]:  #only one option is required for this product
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice") 

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    product_item["pc_count"] = 1
                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    product_list.append(product_item) 
                                    self.count+=1
                    elif product.get("itemPrice") != 0:
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["product_name"] = product.get("name")
                        product_item["price"] = product.get("itemPrice")

                        for calories_info in calories_data.get("items"):
                            if product_item["product_name"] == calories_info.get("name"):
                                product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                        product_item["pc_count"] = 1
                        product_item["description"] = product.get("description")
                        product_item["product_image"] = product.get("desktopImage") 
                        category_tag = category.get("tag").replace("_","-").lower() 
                        product_tag = product.get("tag").replace("_","-").lower()
                        product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                        product_list.append(product_item)  
                        self.count+=1 
                    else:
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items"):
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")   

                                    if "w/" in product_item["product_name"]:
                                        if product_item["product_name"] == "Gallon Sunjoy™ w/  1/2 Sweet Tea 1/2 Lemonade":
                                            for calories_info in calories_data.get("items"):
                                                if calories_info.get("name") == "Gallon Sunjoy® (1/2 Sweet Tea, 1/2 Lemonade)":
                                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                                        elif "1/2 Sweet Tea 1/2 Lemonade" in product_item["product_name"]:
                                            prod_name = product_item["product_name"].replace("w/ 1/2 Sweet Tea 1/2 Lemonade","(1/2 Sweet Tea, 1/2 Lemonade)")
                                            for calories_info in calories_data.get("items"):
                                                if prod_name == calories_info.get("name"):
                                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                                        elif "1/2 Sweet Tea 1/2 Diet Lemonade" in product_item["product_name"]:
                                            prod_name = product_item["product_name"].replace("w/ 1/2 Sweet Tea 1/2 Diet Lemonade","(1/2 Sweet Tea, 1/2 Diet Lemonade)")
                                            for calories_info in calories_data.get("items"):
                                                if prod_name == calories_info.get("name"):
                                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                                        elif "1/2 Unsweet Tea 1/2 Lemonade" in product_item["product_name"]:
                                            prod_name = product_item["product_name"].replace("w/ 1/2 Unsweet Tea 1/2 Lemonade","(1/2 Unsweet Tea, 1/2 Lemonade)")
                                            for calories_info in calories_data.get("items"):
                                                if prod_name == calories_info.get("name"):
                                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                                        elif "1/2 Unsweet Tea 1/2 Diet Lemonade" in product_item["product_name"]:     
                                            prod_name = product_item["product_name"].replace("w/ 1/2 Unsweet Tea 1/2 Diet Lemonade","(1/2 Unsweet Tea, 1/2 Diet Lemonade)")
                                            for calories_info in calories_data.get("items"):
                                                if prod_name == calories_info.get("name"):
                                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")                               
                                    else:    
                                        for calories_info in calories_data.get("items"):
                                            if product_item["product_name"] == calories_info.get("name"):
                                                product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    product_item["pc_count"] = 1

                                    if "Small" in product_item["product_name"] or "Medium" in product_item["product_name"] or "Large" in product_item["product_name"]:
                                        product_item["size"] = product_item["product_name"].split(" ")[0]

                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    product_list.append(product_item)
                                    self.count+=1

            elif menu_item["category_name"] == "Salads":  #add-ons not needed
                for product in category.get("items"):
                    categories_itemgroupid = product.get("itemGroupId")
                    for itemgroups in data.get("itemGroups"):
                        product_itemgroupid = itemgroups.get("itemGroupId")
                        if categories_itemgroupid == product_itemgroupid:
                            for itemgroup in itemgroups.get("items"):
                                product_item = RestaurantProductItem()
                                product_item["sequence_number"] = self.count
                                product_item["product_name"] = itemgroup.get("name")
                                product_item["price"] = itemgroup.get("itemPrice")   

                                for calories_info in calories_data.get("items"):
                                    if product_item["product_name"] == calories_info.get("name"):
                                        product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                                    product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                                else:
                                    product_item["pc_count"] = 1

                                product_item["description"] = itemgroup.get("description")
                                product_item["product_image"] = itemgroup.get("desktopImage")
                                category_tag = category.get("tag").replace("_","-").lower() 
                                product_tag = product.get("tag").replace("_","-").lower()
                                product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                product_list.append(product_item)
                                self.count+=1

            elif menu_item["category_name"] == "Treats":  #add-ons available only for Icedream Cup
                for product in category.get("items"):
                    if product.get("name") == "Frosted Lemonade":
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items")[0:1]:  #only one option is required for this product
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice") 

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    product_item["pc_count"] = 1
                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    product_list.append(product_item) 
                                    self.count+=1
                    elif product.get("name") == "Icedream<sup>®</sup> Cup":
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items"):
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")  

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    product_item["pc_count"] = 1
                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}" 
                                    
                                    base_options = []
                                    base_item = RestaurantBaseItem()
                                    base_item["description"] = "Default"
                                    base_item["base"] = "Default"
                                    base_item["base_price"] = "" 

                                    for addon_itemgroups in data.get("itemGroups"):
                                        addon_itemgroupsid = addon_itemgroups.get("itemGroupId")
                                        if categories_itemgroupid == addon_itemgroupsid:
                                            for addon_item_group in addon_itemgroups.get("items"):  #new line for this template
                                                addon_itemgroups_id = addon_item_group.get("itemGroupId")
                                                for addon_itemgroup in data.get("itemGroups"):
                                                    addon_itemgroup_id = addon_itemgroup.get("itemGroupId")
                                                    if addon_itemgroups_id == addon_itemgroup_id:                                                                                                                                                                                                                  
                                                        add_ons=[]
                                                        for addon_groups_unique in addon_itemgroup.get("items"):  #modified line                                            
                                                            addon_option_id = addon_groups_unique.get("itemGroupId")
                                                            for addon_optiongroups in data.get("itemGroups"):
                                                                addon_optiongroupid = addon_optiongroups.get("itemGroupId")
                                                                if addon_option_id == addon_optiongroupid:                                                                
                                                                    for addon_optiongroup in addon_optiongroups.get("items"):
                                                                        add_on_item = RestaurantAddOnItem()
                                                                        add_on_item["add_on_name"] = addon_optiongroup.get("name")
                                                                        add_on_item["price"] = addon_optiongroup.get("itemPrice")
                                                                        add_ons.append(add_on_item)                                                   
                                    base_item["add_ons"] = add_ons
                                    base_options.append(base_item)
                                    product_item["base_options"] = base_options
                                    product_list.append(product_item)    
                                    self.count+=1                                 
                    else:
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items"):
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")   

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    if "pack" in product_item["product_name"]:
                                        product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                                    else:
                                        product_item["pc_count"] = 1

                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    product_list.append(product_item)
                                    self.count+=1

            elif menu_item["category_name"] == "Kid's Meals":  #add-ons not needed
                for product in category.get("items"):
                    categories_itemgroupid = product.get("itemGroupId")
                    for itemgroups in data.get("itemGroups"):
                        product_itemgroupid = itemgroups.get("itemGroupId")
                        if categories_itemgroupid == product_itemgroupid:
                            for itemgroup in itemgroups.get("items"):
                                product_item = RestaurantProductItem()
                                product_item["sequence_number"] = self.count
                                product_item["product_name"] = itemgroup.get("name")
                                product_item["price"] = itemgroup.get("itemPrice")   

                                for calories_info in calories_data.get("items"):
                                    if product_item["product_name"] == calories_info.get("name"):
                                        product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                                    product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                                else:
                                    product_item["pc_count"] = 1

                                product_item["description"] = itemgroup.get("description")
                                product_item["product_image"] = itemgroup.get("desktopImage")
                                category_tag = category.get("tag").replace("_","-").lower() 
                                product_tag = product.get("tag").replace("_","-").lower()
                                product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                product_list.append(product_item)
                                self.count+=1

            elif menu_item["category_name"] == "Build your own Family Meal":  #add-ons not needed
                for product in category.get("items"):
                    if product.get("itemPrice") != 0:
                        product_item = RestaurantProductItem()
                        product_item["sequence_number"] = self.count
                        product_item["product_name"] = product.get("name")
                        product_item["price"] = product.get("itemPrice")

                        if product_item["product_name"] == "Gallon Sunjoy® w/ 1/2 Sweet Tea 1/2 Lemonade":
                            for calories_info in calories_data.get("items"):
                                if calories_info.get("name") == "Gallon Sunjoy® (1/2 Sweet Tea, 1/2 Lemonade)":
                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                        else:
                            for calories_info in calories_data.get("items"):
                                if product_item["product_name"] == calories_info.get("name"):
                                    product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                        if "Ct" in product_item["product_name"] or "ct" in product_item["product_name"]:
                            product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                        else:
                            product_item["pc_count"] = 1
                      
                        product_item["description"] = product.get("description")
                        product_item["product_image"] = product.get("desktopImage") 
                        category_tag = category.get("tag").replace("_","-").lower() 
                        product_tag = product.get("tag").replace("_","-").lower()
                        product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                        product_list.append(product_item)
                        self.count+=1
                    else:
                        categories_itemgroupid = product.get("itemGroupId")
                        for itemgroups in data.get("itemGroups"):
                            product_itemgroupid = itemgroups.get("itemGroupId")
                            if categories_itemgroupid == product_itemgroupid:
                                for itemgroup in itemgroups.get("items")[0:1]:  #only one option is required for the product "8oz Sauces"
                                    product_item = RestaurantProductItem()
                                    product_item["sequence_number"] = self.count
                                    product_item["product_name"] = itemgroup.get("name")
                                    product_item["price"] = itemgroup.get("itemPrice")   

                                    for calories_info in calories_data.get("items"):
                                        if product_item["product_name"] == calories_info.get("name"):
                                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")

                                    product_item["pc_count"] = 1
                                    product_item["description"] = itemgroup.get("description")
                                    product_item["product_image"] = itemgroup.get("desktopImage")
                                    category_tag = category.get("tag").replace("_","-").lower() 
                                    product_tag = product.get("tag").replace("_","-").lower()
                                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                                    product_list.append(product_item)
                                    self.count+=1

            elif menu_item["category_name"] == "8oz Sauces":  #add-ons not needed
                for product in category.get("items")[0:1]:  #only one option is required for the category "8oz Sauces" as all options have same price
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["product_name"] = product.get("name")
                    product_item["price"] = product.get("itemPrice")

                    for calories_info in calories_data.get("items"):
                        if product_item["product_name"] == calories_info.get("name"):
                            product_item["min_calories"] = calories_info.get("nutrition").get("calories").get("total")
                            
                    product_item["pc_count"] = 1
                    product_item["description"] = product.get("description")
                    product_item["product_image"] = product.get("desktopImage") 
                    category_tag = category.get("tag").replace("_","-").lower() 
                    product_tag = product.get("tag").replace("_","-").lower()
                    product_item["url"] = f"https://order.chick-fil-a.com/menu/{category_tag}/{product_tag}"
                    product_list.append(product_item)
                    self.count+=1

            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus
        self.count=1
        yield restaurant_item    

    async def request_process(self, url):
        request = scrapy.Request(url)
        response = await self.crawler.engine.download(request, self)
        return response    