import scrapy
import json
import dateutil.parser as parser
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantScheduleItem,
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem
)


class ShakeshackSpider(scrapy.Spider):
    name = 'shakeshack'
    headers = {
        'authorization': 'Basic VDQ1VTUxNVB0QjI1QWFJdU1qdVZhUG0yUFRJQkhhZFlOVklScUU5Szp1V2hoN2xUQ0RYdVFURXVWZG9HZWN0RWhMamxMWU5GOW9Bd3MwdEY4QmlMdG5TdFdSU05RWHpORWFtQlZMTnNuajdnRW5sSEJxdzNldm9taVVqTUMyQ1hLc3JidDdSUVFqMnR5dTlXekNCS1JGNE05d21WZEROUWN6eGRjQkVKeQ==',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
        'accept': '*/*',
    }
    count = 1

    def start_requests(self):
        start_urls = ["https://ssma24.com/production-location/regions"]
        for url in start_urls:
            yield scrapy.Request(url, callback=self.parse, headers=self.headers)

    def parse(self, response):
        json_data = json.loads(response.text)
        ids = []
        for js in json_data["result"]:
            ids.append(js.get("id"))
        for id in ids:
            url = f"https://ssma24.com/production-location/locations?regionId={id}&channel=WEB&includePrivate=false"
            yield scrapy.Request(url, callback=self.parse_restaurants, headers=self.headers)

    def parse_restaurants(self, response):
        json_data = json.loads(response.text)
        for restaurant in json_data["result"]:
            restaurant_item = RestaurantItem()
            restaurant_item["source_id"] = restaurant.get("locationId")
            restaurant_item["location_name"] = restaurant.get("name")
            restaurant_item["url"] = f"https://shakeshack.com/home#/location/{restaurant.get('locationId')}"
            restaurant_item["phone_number"] = restaurant.get("phone", "")
            restaurant_item["street_address_1"] = restaurant.get("streetAddress")
            restaurant_item["street_address_2"] = restaurant.get("crossStreet")
            restaurant_item["city"] = restaurant.get("city")
            restaurant_item["postal_code"] = restaurant.get("zip")
            restaurant_item["state"] = restaurant.get("state")
            restaurant_item["country"] = "US"
            restaurant_item["latitude"] = restaurant.get("latitude")
            restaurant_item["longitude"] = restaurant.get("longitude")

            schedule = []
            for weekly_schedule in restaurant['hours']['base'][0:1]:
                schedule_item = RestaurantScheduleItem()
                for day_schedule in weekly_schedule['ranges'][0:7]:
                    day = day_schedule.get('weekday')
                    weekday = parser.parse(day).strftime('%A')
                    if weekday and weekday.lower() in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
                        start = day_schedule.get('start').split(" ")[-1]
                        start = parser.parse(start).strftime('%H:%M %p')
                        end = day_schedule.get('end').split(" ")[-1]
                        end = parser.parse(end).strftime('%I:%M %p')
                        schedule_description = start+" - "+end
                        schedule_item[weekday.lower()] = schedule_description
                schedule.append(schedule_item)
            restaurant_item["schedules"] = schedule

            mod_list = []
            for mod in restaurant.get('handoffModes').keys():
                if restaurant["handoffModes"][mod]["isAvailable"] == True:
                    mod_list.append(mod)
                else:
                    continue
            restaurant_item["type"] = mod_list

            url = f"https://ssma24.com/v1.0/locations/{restaurant.get('oloId')}/menus?platform=web"

            yield scrapy.Request(url, callback=self.parse_products, headers=self.headers, cb_kwargs={"restaurant_item": restaurant_item})

    def parse_products(self, response, restaurant_item):
        menu_data = json.loads(response.text)

        menus = []
        for menu in menu_data:
            menu_item = RestaurantMenuItem()
            menu_item["source_category_id"] = menu.get('category_olo_id')
            menu_item["category_name"] = menu.get('name')

            product_list = []
            if (menu.get('name')) == 'Drinks':
                for product in (menu.get('products')):
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('name')
                    product_item["description"] = product.get('description')
                    product_item["url"] = f"https://shakeshack.com/home#/menu/productDetails/{menu.get('category_olo_id')}/{product.get('id')}"
                    product_item["product_image"] = product.get('kiosk_image')
                    price = product.get('cost')
                    if price == 0:
                        for l in product['categorized_options'][0:1]:
                            for ll in l['options'][0:1]:
                                product_item["price"] = ll.get('cost')
                    else:
                        product_item["price"] = float(price)
                    try:
                        product_item["min_calories"] = int(
                            product.get('basecalories'))
                    except:
                        pass
                  
                    sizes_data = []
                    if ('water' not in (product.get('name').lower())) and ('drink' not in (product.get('name').lower())):
                        for l in product['categorized_options']:
                            if 'SIZE' in (l.get('type')):
                                for ll in l['options']:
                                    quan_name = ll.get('name')
                                    quan_price = ll.get('cost')
                                    quan_calorie=(int(ll.get('basecalories',''))+int(product.get('basecalories'))) if ll.get('basecalories','')!=None else int(product.get('basecalories'))
                                    sizes = {"size_name": quan_name,
                                             "size_price": quan_price,"size_calorie":quan_calorie}
                                    sizes_data.append(sizes)
                        product_item["size"] = sizes_data
                        product_list.append(product_item)
                        self.count += 1
                    else:
                        product_list.append(product_item)
                        self.count += 1

            elif (menu.get('name')) == 'Shakes & Frozen Custard':
                for product in (menu.get('products')):
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('name')
                    product_item["description"] = product.get('description')
                    product_item[
                        "url"] = f"https://shakeshack.com/home#/menu/productDetails/{menu.get('category_olo_id')}/{product.get('id')}"
                    product_item["product_image"] = product.get('images').get('image_xlg')
                    price = product.get('cost')
                    if price == 0:
                        for l in product['categorized_options'][0:1]:
                            for ll in l['options'][0:1]:
                                product_item["price"] = ll.get('cost')
                    else:
                        product_item["price"] = float(price)
                    try:
                        product_item["min_calories"] = int(
                            product.get('basecalories'))
                    except:
                        pass
                    
                    flavour_data = []
                    sizes_data = []
                    if len(product.get('preliminary_options')) != 0:
                        for shake in product['preliminary_options']:
                            if (shake.get('type')) == 'FLAVOR':
                                for opt in shake['options'][0:1]:
                                    quan_name = opt.get('name')
                                    quan_price = opt.get('cost')
                                    flavours = {
                                        "flavour_name": quan_name, "flavour_price": quan_price}
                                    flavour_data.append(flavours)
                        if len(flavour_data) > 0:
                            product_item["flavour"] = flavour_data
                        for shake in product['preliminary_options']:
                            if (shake.get('type')) == 'SIZE':
                                for opt in shake['options']:
                                    quan_item = opt.get('name')
                                    quan_calorie=(int(opt.get('basecalories',''))+int(product.get('basecalories'))) if opt.get('basecalories','')!=None else int(product.get('basecalories'))
                                    for mod in opt['modifiers']:
                                        if (mod.get('type')) == 'FLAVOR':
                                            for opt in mod.get('options')[0:1]:
                                                quan_price = opt.get('cost')
                                                quan_flavour=opt.get('name')
                                                sizes = {"size_name": quan_item,
                                                        "size_price": quan_price,"size_flavour":quan_flavour,"size_calorie":quan_calorie}
                                                sizes_data.append(sizes)
                        product_item["size"] = sizes_data
                        product_list.append(product_item)
                        self.count += 1
                    else:
                        product_list.append(product_item)
                        self.count += 1

            elif (menu.get('name')) == 'Burgers':
                for product in (menu.get('products')):
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('name')
                    product_item["description"] = product.get('description')
                    product_item[
                        "url"] = f"https://shakeshack.com/home#/menu/productDetails/{menu.get('category_olo_id')}/{product.get('id')}"
                    product_item["product_image"] = product.get('kiosk_image')
                    price = product.get('cost')
                    if price == 0:
                        for l in product['categorized_options'][0:1]:
                            for ll in l['options'][0:1]:
                                product_item["price"] = ll.get('cost')
                    else:
                        product_item["price"] = float(price)
                    try:
                        product_item["min_calories"] = int(
                            product.get('basecalories'))
                    except:
                        pass
                   
                    base_options = []
                    base_item = RestaurantBaseItem()
                    base_item["description"] = "Default"
                    base_item["base"] = "Default"
                    base_item["base_price"] = ""
                    add_ons = []
                    for ele in product['categorized_options']:
                        if (ele.get('type')) == 'ADDITION':
                            for add in ele['options']:
                                add_on_item = RestaurantAddOnItem()
                                add_on_item["add_on_name"] = add.get("name")
                                add_on_item["price"] = float(add.get("cost"))
                                add_ons.append(add_on_item)
                    base_item["add_ons"] = add_ons
                    base_options.append(base_item)
                    product_item["base_options"] = base_options
                    product_list.append(product_item)
                    self.count += 1

            elif (menu.get('name')) == 'Crinkle Cut Fries':
                for product in (menu.get('products')):
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('name')
                    product_item["description"] = product.get('description')
                    product_item[
                        "url"] = f"https://shakeshack.com/home#/menu/productDetails/{menu.get('category_olo_id')}/{product.get('id')}"
                    product_item["product_image"] = product.get('kiosk_image')
                    price = product.get('cost')
                    if price == 0:
                        for l in product['categorized_options'][0:1]:
                            for ll in l['options'][0:1]:
                                product_item["price"] = ll.get('cost')
                    else:
                        product_item["price"] = float(price)
                    try:
                        product_item["min_calories"] = int(
                            product.get('basecalories'))
                    except:
                        pass
                    
                    product_list.append(product_item)
                    self.count += 1

            elif (menu.get('name')) == 'Chicken':
                for product in (menu.get('products')):
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('name')
                    product_item["description"] = product.get('description')
                    product_item[
                        "url"] = f"https://shakeshack.com/home#/menu/productDetails/{menu.get('category_olo_id')}/{product.get('id')}"
                    product_item["product_image"] = product.get('kiosk_image')
                    price = product.get('cost')
                    if price == 0:
                        for l in product['categorized_options'][0:1]:
                            for ll in l['options'][0:1]:
                                product_item["price"] = ll.get('cost')
                    else:
                        product_item["price"] = float(price)
                    try:
                        product_item["min_calories"] = int(product.get('basecalories'))
                    except:
                        pass
                   
                    sizes_data = []
                    base_options = []
                    base_item = RestaurantBaseItem()
                    base_item["description"] = "Default"
                    base_item["base"] = "Default"
                    base_item["base_price"] = ""
                    add_ons = []
                    if len(product.get('categorized_options')) != 0:
                        for ele in product['categorized_options']:
                            if (ele.get('type')) == 'SIZE':
                                for add in ele['options']:
                                    quan_item = add.get('name')
                                    quan_price = add.get('cost')
                                    quan_calorie=(int(add.get('basecalories',''))+int(product.get('basecalories'))) if add.get('basecalories','')!=None else int(product.get('basecalories'))
                                    sizes = {"size_name": quan_item,
                                             "size_price": quan_price,"size_calorie":quan_calorie}
                                    sizes_data.append(sizes)
                            elif (ele.get('type'))=='ADDITION':
                                for add in ele['options']:
                                    add_on_item = RestaurantAddOnItem()
                                    add_on_item["add_on_name"] = add.get(
                                        "name")
                                    add_on_item["price"] = float(
                                        add.get("cost"))
                                    add_ons.append(add_on_item)            
                            elif (ele.get('quick-add-options')) == 'sauce':
                                for add in ele['options']:
                                    add_on_item = RestaurantAddOnItem()
                                    add_on_item["add_on_name"] = add.get(
                                        "name")
                                    add_on_item["price"] = float(
                                        add.get("cost"))
                                    add_ons.append(add_on_item)
                        product_item["size"] = sizes_data
                        base_item["add_ons"] = add_ons
                        base_options.append(base_item)
                        product_item["base_options"] = base_options
                        product_list.append(product_item)
                        self.count += 1
                    else:
                        for ele in product['categorized_options']:
                            if (ele.get('quick-add-options')) == 'sauce':
                                for add in ele['options']:
                                    add_on_item = RestaurantAddOnItem()
                                    add_on_item["add_on_name"] = add.get(
                                        "name")
                                    add_on_item["price"] = float(
                                        add.get("cost"))
                                    add_ons.append(add_on_item)
                        base_item["add_ons"] = add_ons
                        base_options.append(base_item)
                        product_item["base_options"] = base_options
                        product_list.append(product_item)
                        self.count += 1

            elif (menu.get('name')) == 'Flat-Top Dogs':
                for product in (menu.get('products')):
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('name')
                    product_item["description"] = product.get('description')
                    product_item[
                        "url"] = f"https://shakeshack.com/home#/menu/productDetails/{menu.get('category_olo_id')}/{product.get('id')}"
                    product_item["product_image"] = product.get('kiosk_image')
                    price = product.get('cost')
                    if price == 0:
                        for l in product['categorized_options'][0:1]:
                            for ll in l['options'][0:1]:
                                product_item["price"] = ll.get('cost')
                    else:
                        product_item["price"] = float(price)
                    try:
                        product_item["min_calories"] = int(
                            product.get('basecalories'))
                    except:
                        pass
                  
                    base_options = []
                    base_item = RestaurantBaseItem()
                    base_item["description"] = "Default"
                    base_item["base"] = "Default"
                    base_item["base_price"] = ""
                    add_ons = []
                    for ele in product['categorized_options']:
                        if (ele.get('type')) == 'ADDITION':
                            for add in ele['options']:
                                add_on_item = RestaurantAddOnItem()
                                add_on_item["add_on_name"] = add.get("name")
                                add_on_item["price"] = float(add.get("cost"))
                                add_ons.append(add_on_item)
                    base_item["add_ons"] = add_ons
                    base_options.append(base_item)
                    product_item["base_options"] = base_options
                    product_list.append(product_item)
                    self.count += 1

            else:
                for product in (menu.get('products')):
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = product.get('id')
                    product_item["product_name"] = product.get('name')
                    product_item["description"] = product.get('description')
                    product_item[
                        "url"] = f"https://shakeshack.com/home#/menu/productDetails/{menu.get('category_olo_id')}/{product.get('id')}"
                    product_item["product_image"] = product.get('kiosk_image')
                    price = product.get('cost')
                    if price == 0:
                        for l in product['categorized_options'][0:1]:
                            for ll in l['options'][0:1]:
                                product_item["price"] = ll.get('cost')
                    else:
                        product_item["price"] = float(price)
                    try:
                        product_item["min_calories"] = int(
                            product.get('basecalories'))
                    except:
                        pass
                   
                    product_list.append(product_item)
                    self.count += 1

            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus
        self.count = 1
        yield restaurant_item
