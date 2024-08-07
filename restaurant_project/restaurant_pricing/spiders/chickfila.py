import scrapy
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem
)

class ChickFilASpider(scrapy.Spider):
    name = 'chickfila'
    start_urls = ['https://www.chick-fil-a.com/locations/browse']
   
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
        restaurant_item["street_address_1"]=response.xpath('//p[@class="address"]/text()').get("").strip()
        address = response.xpath('//p[@class="address"]/br/following::text()[1]').get("").strip()
        restaurant_item["city"] = address.split(",")[0]
        restaurant_item["state"] = address.split(",")[-1].strip().split(" ")[0]
        restaurant_item["postal_code"] = address.split(",")[-1].strip().split(" ")[-1]
        restaurant_item["country"] = "US"
    
        operation_type = response.xpath('//h3[contains(text(),"Dining")]/following-sibling::ul/li/text()').getall()
        oper_type = [operat_type.strip() for operat_type in operation_type]
        restaurant_item["type"] = [op_type for op_type in oper_type if op_type != '']

        schedules_list = []
        for schedules in response.xpath('//h3[contains(text(),"Hours")]/following-sibling::div'):
            schedule = " : ".join(schedules.xpath('./p/text()').getall())
            schedules_list.append(schedule)
        restaurant_item["schedules_chickfila"] = "|".join(schedules_list)

        menu_url = response.urljoin(response.xpath('//a[@id="LocationDetail-Menu"]/@href').get(""))

        yield scrapy.Request(menu_url,callback=self.parse_menus,cb_kwargs={"restaurant_item": restaurant_item})

    async def parse_menus(self, response, restaurant_item):
        categories_names_list = response.xpath('//div[@data-component="menuNavMobile"]/div/div/h2/text()').getall()
        cat_name_list = [categories_name_list.strip() for categories_name_list in categories_names_list]
        category_name_list = [cate for cate in cat_name_list if cate != 'Breakfast']
        menus = []
        for category_nm in category_name_list:
            menu_item = RestaurantMenuItem()
            menu_item["category_name"] = category_nm
          
            if menu_item["category_name"] == "Dipping Sauces and Dressings": #to skip the mentioned category as it is not required
                continue

            product_list = []
            products_path = response.xpath(f'//h2[contains(text(),"{category_nm}")]/parent::div/following-sibling::div/div/div/a/@href').getall()
            for product_path in products_path:
                product_url = response.urljoin(product_path)
                product_response = await self.request_process(product_url)

                if menu_item["category_name"] == "Entrées":
                    for product in product_response.xpath('//div[@class="p-details__radio"]'):
                        product_item = RestaurantProductItem()
                        product_details = product.xpath("./label/span/@aria-label").get("") 
                        product_item["product_name"] = product_details.split(",")[0].strip()
                        product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                        product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                        product_item["url"] = product_url

                        base_options = []
                        base_item = RestaurantBaseItem()
                        base_item["description"] = "Default"
                        base_item["base"] = "Default"
                        base_item["base_price"] = "" 

                        add_ons=[]
                        for addon in product_response.xpath('//h2[contains(text(),"Extras")]/following-sibling::div/div/div'):
                            add_on_item = RestaurantAddOnItem()
                            add_on_item["add_on_name"] = ("".join(addon.xpath('./h4/text()').getall())).strip()
                            price = addon.xpath('./span/text()').get("").strip()
                            if "|" in price:
                                add_on_item["price"] = float(price.split("|")[0].split("$")[-1].strip())
                            else:
                                add_on_item["price"] = 0
                            add_ons.append(add_on_item)

                        base_item["add_ons"] = add_ons
                        base_options.append(base_item)    
                        product_item["base_options"] = base_options
                        product_list.append(product_item)                      

                elif menu_item["category_name"] == "Salads":
                    for product in product_response.xpath('//div[@class="p-details__radio"]'):
                        product_item = RestaurantProductItem()
                        product_details = product.xpath("./label/span/@aria-label").get("")
                        product_item["product_name"] = product_details.split(",")[0].strip()
                        product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                        product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                        product_item["url"] = product_url
                        product_list.append(product_item)
                         
                elif menu_item["category_name"] == "Sides":
                    if product_response.xpath("//h1/text()").get("").strip() == "Greek Yogurt Parfait":
                        product_item = RestaurantProductItem()
                        product_details = product_response.xpath('//div[@class="p-details__radio"]/label/span/@aria-label').get("")
                        product_item["product_name"] = product_response.xpath("//h1/text()").get("").strip()
                        product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                        product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        product_item["product_image"] = product_response.xpath('//div[@class="p-details__radio"]/input/@data-image-url').get("")
                        product_item["url"] = product_url
                        product_list.append(product_item)

                    elif product_response.xpath('//div[@class="p-details__radio"]'):  #products with options, enter into if condition
                        for product in product_response.xpath('//div[@class="p-details__radio"]'):
                            product_details = product.xpath("./label/span/@aria-label").get("")
                            if "Small" in product_details or "Medium" in product_details or "Large" in product_details or "Cup" in product_details or "Bowl" in product_details:
                                product_item = RestaurantProductItem()
                                product_item["product_name"] = product_response.xpath('//h1[@class="p-details__h1"]/text()').get("").strip()
                                product_item["size"] = product_details.split(",")[0].strip()
                                product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                                product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                                product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                                product_item["url"] = product_url
                                product_list.append(product_item)
                               
                            else:
                                product_item = RestaurantProductItem()
                                product_item["product_name"] = product_details.split(",")[0].strip()
                                product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                                product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                                product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                                product_item["url"] = product_url
                                product_list.append(product_item)
                           
                    else:  #products without options, enter into else condition; eg: Waffle Potato Chips in Sides
                        product_item = RestaurantProductItem()
                        product_item["product_name"] = ("".join(product_response.xpath('//h1[@class="p-details__h1"]/text()').getall())).strip()
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        price = product_response.xpath('//span[@id="productDetailPrice"]/text()').get("").strip()
                        product_item["price"] = float(price.split("$")[-1].split("/")[0])   
                        product_item["min_calories"] = int(product_response.xpath('//p[@class="p-nutri__block"][1]/span/text()').get(""))
                        product_item["product_image"] = product_response.xpath('//img[@id="mainImage"]/@src').get("")
                        product_item["url"] = product_url
                        product_list.append(product_item)
              
                elif menu_item["category_name"] == "Kid's Meals":
                    for product in product_response.xpath('//div[@class="p-details__radio"]'):
                        product_item = RestaurantProductItem()
                        product_details = product.xpath("./label/span/@aria-label").get("")
                        product_item["product_name"] = product_details.split(",")[0].strip()
                        product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                        product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                        product_item["url"] = product_url
                        product_list.append(product_item)

                elif menu_item["category_name"] == "Treats":
                    if product_response.xpath("//h1/text()").get("").strip() == "Frosted Lemonade":
                        product_item = RestaurantProductItem()
                        product_details = product_response.xpath('//div[@class="p-details__radio"]/label/span/@aria-label').get("")
                        product_item["product_name"] = product_details.split(",")[0].strip()
                        product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                        product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        product_item["product_image"] = product_response.xpath('//div[@class="p-details__radio"]/input/@data-image-url').get("")
                        product_item["url"] = product_url
                        product_list.append(product_item)

                    else:
                        for product in product_response.xpath('//div[@class="p-details__radio"]'):
                            if product_response.xpath("//h1/text()").get("").strip() == "Chocolate Chunk Cookie":
                                product_item = RestaurantProductItem()
                                product_details = product.xpath("./label/span/@aria-label").get("")
                                product_item["product_name"] = product_response.xpath('//h1[@class="p-details__h1"]/text()').get("").strip()
                                product_item["size"] = product_details.split(",")[0].strip()
                                product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                                product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                                product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                                product_item["url"] = product_url
                                product_list.append(product_item) 

                            else:
                                product_item = RestaurantProductItem()
                                product_details = product.xpath("./label/span/@aria-label").get("")
                                product_item["product_name"] = product_details.split(",")[0].strip()
                                product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                                product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                                product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                                product_item["url"] = product_url
                                product_list.append(product_item) 

                elif menu_item["category_name"] == "Drinks":
                    if product_response.xpath("//h1/text()").get("").strip() == "Iced Coffee":
                        product_item = RestaurantProductItem()
                        product_details = product_response.xpath('//div[@class="p-details__radio"]/label/span/@aria-label').get("")
                        product_item["product_name"] = product_details.split(",")[0].strip()
                        product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                        product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        product_item["product_image"] = product_response.xpath('//div[@class="p-details__radio"]/input/@data-image-url').get("")
                        product_item["url"] = product_url
                        product_list.append(product_item) 

                    elif product_response.xpath('//div[@class="p-details__radio"]'):  #products with options, enter into if condition
                        for product in product_response.xpath('//div[@class="p-details__radio"]'):
                            product_details = product.xpath("./label/span/@aria-label").get("")
                            if "Small" in product_details or "Medium" in product_details or "Large" in product_details:
                                product_item = RestaurantProductItem()
                                if "Sunjoy® w/ 1/2" in product_details:
                                    product_item["size"] = product_details.split(",")[0].strip()
                                    product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1])
                                    product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                elif "1/2" in product_details:    
                                    product_item["size"] = product_details.split("),")[0] + ")"
                                    product_item["price"] = float(product_details.split("),")[-1].strip().split(",")[0].split("$")[-1])
                                    product_item["min_calories"] = int(product_details.split("),")[-1].strip().split(",")[1].strip().split(" ")[0])
                                else:    
                                    product_item["size"] = product_details.split(",")[0].strip()
                                    product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                                    product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                product_item["product_name"] = ("".join(product_response.xpath('//h1[@class="p-details__h1"]/text()').getall())).strip()
                                product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                                product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                                product_item["url"] = product_url
                                product_list.append(product_item)
                            elif "1/2" in product_details:
                                product_item = RestaurantProductItem()
                                if "Sunjoy™ w/  1/2" in product_details:
                                    product_item["product_name"] = product_details.split(",")[0].strip()
                                    product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1])
                                    product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                else:
                                    product_item["product_name"] = product_details.split("),")[0] + ")"
                                    product_item["price"] = float(product_details.split("),")[-1].strip().split(",")[0].split("$")[-1])
                                    product_item["min_calories"] = int(product_details.split("),")[-1].strip().split(",")[1].strip().split(" ")[0])
                                product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                                product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                                product_item["url"] = product_url
                                product_list.append(product_item)         
                            else:
                                product_item = RestaurantProductItem()
                                product_item["product_name"] = product_details.split(",")[0].strip()
                                product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                                product_item["min_calories"] = int(product_details.split(",")[2].strip().split(" ")[0])
                                product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                                product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                                product_item["url"] = product_url
                                product_list.append(product_item)                                                        

                    else:  #products without options, enter into else condition; eg: Simply Orange in Drinks
                        product_item = RestaurantProductItem()
                        product_item["product_name"] = ("".join(product_response.xpath('//h1[@class="p-details__h1"]/text()').getall())).strip()
                        product_item["description"] = product_response.xpath('//div[@class="p-details__text"]/p/text()').get("").strip()
                        price = product_response.xpath('//span[@id="productDetailPrice"]/text()').get("").strip()
                        if price == '':
                            product_item["price"] = 0
                        else:    
                            product_item["price"] = float(price.split("$")[-1].split("/")[0])   
                        min_calories = product_response.xpath('//p[@class="p-nutri__block"][1]/span/text()').get("")
                        if min_calories == '':
                            product_item["min_calories"] = None
                        else:    
                            product_item["min_calories"] = int(min_calories)
                        product_item["product_image"] = product_response.xpath('//img[@id="mainImage"]/@src').get("")
                        product_item["url"] = product_url
                        product_list.append(product_item)

            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus
            
        if response.xpath('//a[contains(text(),"Catering")]/parent::li[@data-element="subNavMenuCategory"]//a'):
            category_catering = response.xpath('//a[contains(text(),"Catering")]/parent::li[@data-element="subNavMenuCategory"]//a')
            menu_item = RestaurantMenuItem()
            menu_item["category_name"] = category_catering.xpath('./text()').get("").strip()

            catering_url = response.urljoin(category_catering.xpath("./@href").get(""))
            catering_response = await self.request_process(catering_url)
            
            product_list = []
            packaged_meals_products_path = catering_response.xpath('//h2[contains(text(),"Packaged Meals")]/following-sibling::div/div/div/a/@href').getall()
            for packaged_meals_product_path in packaged_meals_products_path:
                packaged_meals_product_url = response.urljoin(packaged_meals_product_path)
                packaged_meals_product_response = await self.request_process(packaged_meals_product_url)

                for product in packaged_meals_product_response.xpath('//div[@class="p-details__radio"]'):
                    product_item = RestaurantProductItem()
                    product_details = product.xpath("./label/span/@aria-label").get("")
                    product_item["product_name"] = product_details.split(",")[0].strip()
                    product_item["price"] = float(product_details.split(",")[1].strip().split("$")[-1]) 
                    product_item["description"] = ("".join(packaged_meals_product_response.xpath('//div[@class="p-details__text"]/p/text()').getall())).strip()
                    product_item["product_image"] = product.xpath('./input/@data-image-url').get("")
                    product_item["url"] = packaged_meals_product_url
                    product_list.append(product_item)

            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus            

        yield restaurant_item

    async def request_process(self, url):
        request = scrapy.Request(url)
        response = await self.crawler.engine.download(request, self)

        return response
