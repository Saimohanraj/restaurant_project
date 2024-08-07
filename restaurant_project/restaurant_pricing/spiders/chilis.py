import scrapy
from restaurant_pricing.items import (
    RestaurantChilisItem,
    RestaurantChilisMenuItem,
    RestaurantChilisProductItem,
)

class ChilisSpider(scrapy.Spider):
    name = "chilis"

    def __init__(self, *args, **kwargs):
        city_url = kwargs.get("city_url")
        restaurant_url = kwargs.get("restaurant_url")
        self.restaurant_url = restaurant_url
        self.city_url = city_url
        super().__init__(*args, **kwargs)     

    def start_requests(self):
        yield scrapy.Request(self.city_url,callback=self.parse_locations)

    def parse_locations(self, response):   
        for restaurant in response.xpath('//div[@class="location"]'):
            restaurant_item = RestaurantChilisItem()
            restaurant_item["url"] = "https://www.chilis.com" + restaurant.xpath('.//a[contains(text(),"Order Now")]/@href').get("")

            if self.restaurant_url == restaurant_item["url"]:
                source_id = restaurant.xpath('.//a[contains(text(),"Order Now")]/@href').get("")
                restaurant_item["source_id"] = source_id.split("=")[-1]
                restaurant_item["url"] = "https://www.chilis.com" + restaurant.xpath('.//a[contains(text(),"Order Now")]/@href').get("")
                restaurant_item["location_name"] = restaurant.xpath('.//span[@class="location-title"]/text()').get("")
                restaurant_item["phone_number"] = restaurant.xpath('.//span[@class="tel"]/text()').get("")
                restaurant_item["street_address"] = restaurant.xpath('.//span[@class="street-address"]/text()').get("")
                restaurant_item["locality"] = restaurant.xpath('.//span[@class="locality"]/text()').get("")
                restaurant_item["city"] = response.url.split("/")[-1].title()
                restaurant_item["postal_code"] = restaurant.xpath('.//span[@class="postal-code"]/text()').get("")
                restaurant_item["state"] = restaurant.xpath('.//span[@class="region"]/text()').get("")
                restaurant_item["country"] = "US"

                headers = {
                    'authority': 'www.chilis.com',
                    'upgrade-insecure-requests': '1',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'referer': f'{response.url}',
                    'accept-language': 'en-US,en;q=0.9'
                }
               
                yield scrapy.Request(self.restaurant_url,headers=headers,callback=self.parse_menus,cb_kwargs={"restaurant_item":restaurant_item},dont_filter=True)

    async def parse_menus(self, response, restaurant_item=None):
        category_links = response.xpath("//h4/a/@href").getall()
       
        menus = []
        count = 1
        for category_link in category_links:
            category_link = "https://www.chilis.com" + category_link
            menu_response = await self.request_process(category_link)
            
            menu_item = RestaurantChilisMenuItem()
            menu_item["category_name"] = menu_response.xpath("//h1/text()").get("")

            product_list = []
            if menu_response.xpath('//div[@class="grid-item"]'): # For "Appetizers" and similar categories
                for product in menu_response.xpath('//div[@class="grid-item"]'):
                    product_item = RestaurantChilisProductItem()
                    product_item["sequence_number"] = count
                    product_item["product_name"] = product.xpath('.//span[@itemprop="name"]/text()').get("")
                    product_item["description"] = product.xpath('.//span[@itemprop="description"]/text()').get("")
                    product_item["product_image"] = product.xpath('.//meta[@itemprop="image"]/@content').get("")
                    url = product.xpath('.//a[contains(@href,"/menu/")]/@href').get("")
                    product_item["url"] = response.urljoin(url)
                    price = product.xpath('.//div[@class="item-cost-calories"]/span/text()').get("")
                    if "|" in price:
                        product_item["price"] = float(price.split("|")[0].replace("$","").strip())
                    else:
                        product_item["price"] = float(price.replace("$","").strip())
                    calories = product.xpath('.//div[@class="item-cost-calories"]/span/text()').get("")
                    if "|" in calories:
                        calorie = calories.split("|")[-1].strip()
                        if "-" in calorie:
                            product_item["min_calories"] = int(calorie.split("-")[0])
                            product_item["max_calories"] = int(calorie.split("-")[-1].split(" ")[0])
                        else:
                            product_item["min_calories"] = int(calorie.split(" ")[0])  
                    
                    product_list.append(product_item)
                    count=count+1              

            elif menu_response.xpath('//h1[@class="detail-title"]'):  # For "3 for $10.99" and similar categories
                product_item = RestaurantChilisProductItem()
                product_item["sequence_number"] = count
                product_item["product_name"] = menu_response.xpath('//h1[@class="detail-title"]/text()').get("")
                product_item["description"] = menu_response.xpath('//div[@class="detail-description"]/span/text()').get("")
                product_item["product_image"] = menu_response.xpath('//div[@class="detail-image"]/img/@src').get("")
                product_item["url"] = menu_response.url
                price = menu_response.xpath('//div[@class="detail-cost-calories"]/span/text()').get("")
                product_item["price"] = float(price.replace("$","").strip())
                
                product_list.append(product_item)
                count=count+1

            elif menu_response.xpath('//div[@class="item-body basic-list"]'):  # For "Sides" category
                for product in menu_response.xpath('//div[@class="item-body basic-list"]'):
                    product_item = RestaurantChilisProductItem()
                    product_item["sequence_number"] = count
                    product_name = product.xpath('.//p[@class="name"]/text()').get("")
                    if "|" in product_name:
                        product_item["product_name"] = product_name.split("|")[0].strip()
                    else:
                        product_item["product_name"] = product_name
                    product_item["description"] = product.xpath('.//p[@class="description"]/text()').get("")
                    product_item["product_image"] = menu_response.xpath('//img[@itemprop="image"]/@src').get("")
                    product_item["url"] = menu_response.url
                    price = product.xpath('.//p[@class="cost"]/text()').get("")
                    product_item["price"] = float(price.replace("$","").strip())
                    calories = product.xpath('.//p[@class="name"]/text()').get("")
                    if "|" in calories:
                        calorie = calories.split("|")[-1].strip()
                        if "-" in calorie:
                            product_item["min_calories"] = int(calorie.split("-")[0])
                            product_item["max_calories"] = int(calorie.split("-")[-1].split(" ")[0])
                        else:
                            product_item["min_calories"] = int(calorie.split(" ")[0])
                    
                    product_list.append(product_item)  
                    count=count+1       

            elif menu_response.xpath('//div[@class="multi-item-group"]'):  # For "Beverages" category
                for product in menu_response.xpath('//div[@class="menu-item-bev"]//div[@class="multi-item"]'):
                    product_item = RestaurantChilisProductItem()
                    product_item["sequence_number"] = count
                    product_name = product.xpath('.//p[@class="name"]/text()').get("")  
                    if "|" in product_name:
                        product_item["product_name"] = product_name.split("|")[0].strip()
                    else:
                        product_item["product_name"] = product_name
                    product_item["product_image"] = menu_response.xpath('//img[@itemprop="image"]/@src').get("")
                    product_item["url"] = menu_response.url
                    price = menu_response.xpath('//div[@class="multi-item-group"]//p[@class="cost"]/text()').get("")
                    product_item["price"] = float(price.replace("$","").strip())
                    calories = product.xpath('.//p[@class="name"]/text()').get("")
                    if "|" in calories:
                        calorie = calories.split("|")[-1].strip()
                        if "-" in calorie:
                            product_item["min_calories"] = int(calorie.split("-")[0])
                            product_item["max_calories"] = int(calorie.split("-")[-1].split(" ")[0])
                        else:
                            product_item["min_calories"] = int(calorie.split(" ")[0])
                    
                    product_list.append(product_item)
                    count=count+1

                for product in menu_response.xpath('//div[@class="menu-item-bev"]/div[@class="item-body"]'):
                    product_item = RestaurantChilisProductItem()
                    product_item["sequence_number"] = count
                    product_name = product.xpath('.//p[@class="name"]/text()').get("")  
                    if "|" in product_name:
                        product_item["product_name"] = product_name.split("|")[0].strip()
                    else:
                        product_item["product_name"] = product_name
                    product_item["product_image"] = menu_response.xpath('//img[@itemprop="image"]/@src').get("") 
                    product_item["url"] = menu_response.url
                    price = product.xpath('.//p[@class="cost"]/text()').get("")
                    product_item["price"] = float(price.replace("$","").strip())
                    calories = product.xpath('.//p[@class="name"]/text()').get("")
                    if "|" in calories:
                        calorie = calories.split("|")[-1].strip()
                        if "-" in calorie:
                            product_item["min_calories"] = int(calorie.split("-")[0])
                            product_item["max_calories"] = int(calorie.split("-")[-1].split(" ")[0])
                        else:
                            product_item["min_calories"] = int(calorie.split(" ")[0])

                    product_list.append(product_item)
                    count=count+1

            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus
        
        yield restaurant_item

    async def request_process(self, url):
        request = scrapy.Request(url)
        response = await self.crawler.engine.download(request, self)

        return response
