import scrapy
import json
import html
import re
from scrapy.spiders import SitemapSpider
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantMenuItem,
    RestaurantProductItem
)


def html_tag_cleaner(data):
    if data is not None:
        clean_text = re.sub(r'<.*?>', '', data)
        clean_text = clean_text.replace("\n;", " ")
        clean_text = clean_text.replace("\n", " ")
        clean_text = clean_text.replace("*", " ")
        clean_text = html.unescape(clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if "div." in clean_text:
            clean_text = re.findall(r"div.*\}(.*)", clean_text)
            clean_text = clean_text[0].strip()

    else:
        clean_text = data

    return clean_text


class OliveGardenSpider(SitemapSpider):
    name = 'olivegarden'
    sitemap_urls = ['https://www.olivegarden.com/en-locations-sitemap.xml']
    headers = {
        'accept': 'application/json, text/plain, */*',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'accept-language': 'en-US,en;q=0.9'
    }

    def sitemap_filter(self, entries):
        for entry in entries:
            yield entry

    def parse(self, response):
        json_data = response.xpath('//script[@type="application/ld+json"]/text()').get('').strip()
        data = json.loads(json_data)

        restaurant_item = RestaurantItem()
        address = data.get('address', {})
        source_id = response.xpath('//input[@id="restID"]/@value').get('').strip()
        restaurant_item["source_id"] = source_id

        restaurant_url = f"https://www.olivegarden.com/web-api/menu?locale=en_US&restaurantId={str(source_id).strip()}&categoryId=--&conceptCode=OG"

        restaurant_item["location_name"] = data.get('name')
        restaurant_item["url"] = restaurant_url
        city = address.get('addressLocality', "")
        state = address.get('addressRegion', "")
        postal_code = address.get('postalCode', "")

        restaurant_item["city"] = city
        restaurant_item["state"] = state
        restaurant_item["postal_code"] = postal_code

        restaurant_item["street_address_1"] = address.get('streetAddress')
        restaurant_item["street_address_2"] = city+", "+state + " "+postal_code
        restaurant_item["phone_number"] = data.get('telephone')
        restaurant_item["country"] = address.get('addressCountry')
        coordinates = data.get('geo', {})

        restaurant_item["latitude"] = coordinates.get('latitude')
        restaurant_item["longitude"] = coordinates.get('longitude')

        yield scrapy.Request(url=restaurant_url, headers=self.headers, callback=self.parse_restaurant_menus, cb_kwargs={"restaurant_id": source_id, "restaurant_item": restaurant_item})

    async def parse_restaurant_menus(self, response, restaurant_id, restaurant_item):
        data = json.loads(response.text)

        menus = []
        count = 1
        for cat in data.get('successResponse').get('menucategory'):
            menu_item = RestaurantMenuItem()
            product_list = []
            source_category_id = cat.get('repositoryId')[0]
            category_name = cat.get('name')[0]
            menu_item['source_category_id'] = source_category_id
            menu_item['category_name'] = category_name

            if cat.get('products') is not None:
                for pro in cat.get('products'):
                    product_item = await self.parse_menu_process(pro, count, restaurant_id, response.url)
                    product_list.append(product_item)
                    count = count+1
                menu_item["products"] = product_list
                menus.append(menu_item)
            else:
                for sub_cat in cat.get('menucategories'):
                    for pro in sub_cat.get('products'):
                        product_item = await self.parse_menu_process(pro, count, restaurant_id, response.url)
                        product_list.append(product_item)
                        count = count+1
                menu_item["products"] = product_list
                menus.append(menu_item)
            restaurant_item["menus"] = menus
        yield restaurant_item

    async def parse_menu_process(self, pro, count, restaurant_id, restaurant_url):
        product_item = RestaurantProductItem()
        product_item["sequence_number"] = count
        source_product_id = pro.get('repositoryId')[0]
        product_item["source_product_id"] = source_product_id
        product_item["product_name"] = pro.get('displayName')[0]

        calories = pro.get('nutritionCAL')
        if calories is not None:
            product_item["min_calories"] = calories[0] if len(
                calories) > 0 else ""

        product_url = f"https://www.olivegarden.com/web-api/menuitem/{str(source_product_id)}?locale=en_US&menuItemId={str(source_product_id)}&restaurantId={restaurant_id}"
        menu_response = await self.request_process(product_url)

        menu_data = json.loads(menu_response.text)

        product_item["url"] = f"https://www.olivegarden.com/menu/{pro.get('slug')[0]}/{source_product_id}/"
      
        try:
            description = menu_data.get('successResponse').get('product').get('longDescription')    
            product_item["description"] = html_tag_cleaner(description)
            product_item["product_image"] = menu_data.get('successResponse').get('product').get('largeImageUrl')
            product_item["price"] = menu_data.get('successResponse').get('price')[0].get('listPrice')
        except:
            pass

        return product_item

    async def request_process(self, url):
        request = scrapy.Request(url)
        response = await self.crawler.engine.download(request, self)

        return response
