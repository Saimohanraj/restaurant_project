# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter, adapter
import scrapy
from urllib.parse import quote, urlparse
import os
import hashlib


class RestaurantPricingPipeline:
    def process_item(self, item, spider):
        return item


class RestaurantImagePipeline:
    async def process_item(self, item, spider):
        for menu in item["menus"]:
            for product in menu.get("products", []):
                image_url = product.get("product_image", "")
                downloads_directory = os.path.join(
                    os.getcwd(), f"Images/{spider.name}")
                if not os.path.exists(downloads_directory):
                    os.makedirs(downloads_directory)
                if image_url:
                    image_name_parse = urlparse(image_url)
                    image_name = os.path.basename(image_name_parse.path)
                    image_name = image_name.split(".")
                    hash_image_name = hashlib.md5(
                        bytes(image_name[0], encoding="utf-8")
                    ).hexdigest()
                    request = scrapy.Request(image_url)
                    image_response = await spider.crawler.engine.download(
                        request, spider
                    )
                    if image_response.status == 200:
                        if f"{hash_image_name}.{image_name[1]}" not in os.listdir(
                            downloads_directory
                        ):
                            with open(
                                f"{downloads_directory}/{hash_image_name}.{image_name[1]}",
                                "wb",
                            ) as f:
                                f.write(image_response.body)

        return item
