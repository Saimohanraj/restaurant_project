import scrapy
import json
import re
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantMenuItem,
    RestaurantProductItem
)

class GoopkitchenSpider(scrapy.Spider):
    name = "goopkitchen"
    count=1


    def start_requests(self):        
        api_url = 'https://api.koala.io/v1/ordering/store-locations/?sort[state_id]=asc&sort[label]=asc&include[]=operating_hours&include[]=attributes&include[]=delivery_hours&page=1&per_page=50'

        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJEQVhWVVp2VklBaHMxWDJoNmlXckFHNk5HUWsySDFhZmU2WFpLampHZGYxZjBBZktrUjE2Y3hWNW51S1UxZDVOTll6aU9mQ2t2YmIwMTlNbXVFdnUxdUNyRkpnNG5mYks5aFRqcVpiQVVEcW5PUGZLUjRrM291Y1UiLCJqdGkiOiI4MjYwODAwYjRkNDg1NTE4NzA3NzdjMzExNTZiN2I2OTA3ZTRjZmNmYjg4MDkyYmVmNGJhZmY0ZmZiMDAyMDBkM2U5OTEzOTA2MDcyMDY3ZSIsImlhdCI6MTY1MTgyMDQ0OC4wMTA5NjIsIm5iZiI6MTY1MTgyMDQ0OC4wMTA5NjUsImV4cCI6MTY1MTkwNjg0Ny45OTI1NTgsInN1YiI6IiIsInNjb3BlcyI6WyJhbGxlcmdpZXM6aW5kZXgiLCJhbmFseXRpY3NfZXZlbnRzOnNob3dfc2NoZW1hIiwiYmFza2V0X2xveWFsdHk6YXBwbHlfcmV3YXJkcyIsImJhc2tldF9sb3lhbHR5OmRlc3Ryb3lfcmV3YXJkIiwiYmFza2V0X2xveWFsdHk6Z2V0X2FwcGxpZWRfcmV3YXJkcyIsImJhc2tldF9sb3lhbHR5OmdldF9hdmFpbGFibGVfcmV3YXJkcyIsImJhc2tldHM6ZGVzdHJveV9wcm9tb19jb2RlIiwiYmFza2V0czpkZXN0cm95X3dhbnRlZF90aW1lIiwiYmFza2V0czpnZXRfYXZhaWxhYmxlX3dhbnRlZF90aW1lcyIsImJhc2tldHM6bGlzdF9yZXF1aXJlZF92ZXJpZmljYXRpb25zIiwiYmFza2V0czpzZXRfY29udmV5YW5jZSIsImJhc2tldHM6c2hvdyIsImJhc2tldHM6c3RvcmUiLCJiYXNrZXRzOnN0b3JlX2FsbGVyZ2llcyIsImJhc2tldHM6c3RvcmVfcHJvbW9fY29kZSIsImJhc2tldHM6c3RvcmVfd2FudGVkX3RpbWUiLCJiYXNrZXRzOnN1Ym1pdCIsImJhc2tldHM6dmFsaWRhdGVfYmFza2V0IiwiYmFza2V0czp2ZXJpZnlfYmFza2V0IiwiY29uZmlnOnNob3ciLCJncm91cDpvcmRlcmluZ19hcHAiLCJsb2NhdGlvbl9tZW51OnNob3ciLCJsb3lhbHR5OmNoZWNrX3JlZ2lzdHJhdGlvbl9zdGF0dXMiLCJsb3lhbHR5OmNyZWF0ZV9yZWRlbXB0aW9uIiwibG95YWx0eTpmb3Jnb3RfcGFzc3dvcmQiLCJsb3lhbHR5OmluZGV4X3JlZGVlbWFibGVzIiwibG95YWx0eTppbmRleF9yZWRlbXB0aW9ucyIsImxveWFsdHk6cmVnaXN0ZXIiLCJsb3lhbHR5OnJlc2V0X3Bhc3N3b3JkIiwibG95YWx0eTpzaG93X2xveWFsdHlfc3RhdGUiLCJsb3lhbHR5OnNob3dfbWUiLCJsb3lhbHR5OnVwZGF0ZV9tZSIsIm9yZGVyX2xveWFsdHk6Y2xhaW1fcmV3YXJkcyIsIm9yZGVyczpjdXN0b21lcl9hcnJpdmFsIiwib3JkZXJzOmRlc3Ryb3lfZmF2b3JpdGUiLCJvcmRlcnM6ZGlzcGF0Y2hfcmVjZWlwdF9lbWFpbCIsIm9yZGVyczppbmRleF9mYXZvcml0ZXMiLCJvcmRlcnM6aW5kZXhfbXlfb3JkZXJzIiwib3JkZXJzOnN0b3JlX2Zhdm9yaXRlIiwic3RvcmVfbG9jYXRpb25zOmRlc3Ryb3lfZmF2b3JpdGUiLCJzdG9yZV9sb2NhdGlvbnM6aW5kZXgiLCJzdG9yZV9sb2NhdGlvbnM6aW5kZXhfZmF2b3JpdGVzIiwic3RvcmVfbG9jYXRpb25zOnNob3ciLCJzdG9yZV9sb2NhdGlvbnM6c3RvcmVfZmF2b3JpdGUiLCJ0YWdzOmluZGV4IiwidXBzZWxsczpnZW5lcmF0ZSIsInVzZXJzOmRlc3Ryb3lfc3RvcmVkX2NhcmQiLCJ1c2VyczppbmRleF9zdG9yZWRfY2FyZHMiXX0.t6YFzUwpyhtYN56V8z2iWOkkldobMbQnULfcrDdoPuGT2HUDqbtJXxMVXDWOE_euxh3cj9f3iOZxWewpqoXJPVVyY2fiNv-CiFOFy21-ji8--ENry3BSmj5o_h9oRkGjRsr8U3mw_opIiYNkb-S7-I1QPZk5NLXGNwAwfdnxmd_P_LTWgcCkZeOkaM_itzrcK1_Bsl9aO8JshBCFfWAgJC-tfYewfXlyHsR4-FXspbJAQabQUoeq56a6gXScYLRqDvPdHXDCbR0YApJKeznRv0ShJjJuwNRe4_pIuMpk1PRb1QmljXOlCwpw4JDMiQNiAlOY5iaTp3p78etwASX94g8SlfdqvlupCeDIlpqRamnV8UOnsa0heDKqp2usg4hVIsZZtyG2M2RwGamUvrwvnAq4dsTkMRHhLUXV69yfWBnMOc2b8P2rIiJkcnF_AJ-dD-Xi-cPE4_WlQxANg8PRUJQKPfrpUAI7vuJDrjjQB7_zBZMykHnpBIoQmb8i_M3DYYPu-m06n8L7BtRzDndpqwWZ2GoWnCvHc4O8UbgQXAOQjxxAcKHqZXG9ZXLlap4BnkkmUwYxo67mn9jQerLfcF8Rfu4HyMlM6OWW29e-C_g_gzJBdakuslzYxnqsYPUHIpS0IGlh6QVS73N_VxNgUeaT_clVIvcLShldNhSGgpQ',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
            'x-channel-id': 'web',
            'x-koala-service': 'Koala Web Ordering / 1.6.1'
        }    

        yield scrapy.Request(api_url,headers=headers,callback=self.parse_details)

    def parse_details(self,response):
        json_data = json.loads(response.body)
        for data in json_data["data"]:
            restaurant_item = RestaurantItem()
            restaurant_item["source_id"] = data["id"]
            restaurant_item["location_name"] = data["cached_data"]["label"]
            restaurant_item["url"] = f'https://order.goopkitchen.com/store/{restaurant_item["source_id"]}/{restaurant_item["location_name"]}?filter=85'
            restaurant_item["street_address_1"] = data["cached_data"]["street_address"]
            restaurant_item["city"] = data["cached_data"]["city"]
            restaurant_item["state"] = data["cached_data"]["state"]
            restaurant_item["postal_code"] = data["cached_data"]["zip"]
            restaurant_item["phone_number"] = data["cached_data"]["phone_number"]
            restaurant_item["country"] = data["cached_data"]["country"]
            restaurant_item["latitude"] = data["latitude"]
            restaurant_item["longitude"] = data["longitude"]
            restaurant_item["schedules"] = "Open from 10:30am until 9:00pm"
           
            menu_url = f'https://order.goopkitchen.com/store/{restaurant_item["source_id"]}/{restaurant_item["location_name"]}?filter=85'

            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-language': 'en-US,en;q=0.9',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
            }

            yield scrapy.Request(url=menu_url,headers=headers,callback=self.parse_menus,cb_kwargs={"restaurant_item": restaurant_item})

    def parse_menus(self,response,restaurant_item):
        json_file = response.xpath('//script[@type="application/json"]/text()').get('')
        json_details = json.loads(json_file)
        menus = []
        for detail in json_details["props"]["pageProps"]["initialState"]["app"]["menu"]["data"]["categories"][0:9]:
            menu_item = RestaurantMenuItem()
            menu_item["source_category_id"] = detail["id"]
            menu_item["category_name"] = detail["name"]
            product_list = []
            for det in detail["products"]:
                if det["cost"] == 0:
                    if det["name"] == "The Bento Box":
                        for options in det["option_groups"][0:1]:
                            for option in options["options"]:
                                product_item = RestaurantProductItem()
                                product_item["sequence_number"] = self.count
                                product_item["source_product_id"] = option["id"]
                                product_item["product_name"] = (option["name"] + " - " + "The Bento Box").strip()
                                product_item["price"] = float("{0:.2f}".format(option["cost"] / 100.))
                                product_item["pc_count"] = 1
                                product_item["description"] = det["description"]
                                product_item["product_image"] = det["images"]["image_url_1_by_1"]
                                product_item["url"] = f'https://order.goopkitchen.com/store/{restaurant_item["source_id"]}/{restaurant_item["location_name"]}/{menu_item["source_category_id"]}/{menu_item["category_name"]}/{det["id"]}/{det["name"]}?filter=85'
                                product_list.append(product_item)
                                self.count+=1
                    elif menu_item["category_name"] == "Desserts":
                        for options in det["option_groups"][0:1]:
                            for option in options["options"]:
                                product_item = RestaurantProductItem()
                                product_item["sequence_number"] = self.count
                                product_item["source_product_id"] = option["id"]
                                product_item["product_name"] = (option["name"].split(" ")[0] + " " + det["name"]).strip()
                                product_item["price"] = float("{0:.2f}".format(option["cost"] / 100.))
                                if "Cookies" in product_item["product_name"] or "Brownie" in product_item["product_name"]:
                                    product_item["pc_count"] = int(re.findall(r"\d+",product_item["product_name"])[0])
                                else:
                                    product_item["pc_count"] = 1
                                product_item["description"] = det["description"]
                                product_item["product_image"] = det["images"]["image_url_1_by_1"]
                                product_item["url"] = f'https://order.goopkitchen.com/store/{restaurant_item["source_id"]}/{restaurant_item["location_name"]}/{menu_item["source_category_id"]}/{menu_item["category_name"]}/{det["id"]}/{det["name"]}?filter=85'
                                product_list.append(product_item)
                                self.count+=1
                    elif menu_item["category_name"] == "Dressings and Sauces":    
                        for options in det["option_groups"][0:1]:
                            for option in options["options"]:
                                product_item = RestaurantProductItem()
                                product_item["sequence_number"] = self.count
                                product_item["source_product_id"] = option["id"]
                                product_item["product_name"] = option["name"].strip()
                                product_item["price"] = float("{0:.2f}".format(option["cost"] / 100.))
                                product_item["pc_count"] = 1
                                product_item["description"] = det["description"]
                                product_item["product_image"] = det["images"]["image_url_1_by_1"]
                                product_item["url"] = f'https://order.goopkitchen.com/store/{restaurant_item["source_id"]}/{restaurant_item["location_name"]}/{menu_item["source_category_id"]}/{menu_item["category_name"]}/{det["id"]}/{det["name"]}?filter=85'
                                product_list.append(product_item)  
                                self.count+=1    
                                  
                else:    
                    product_item = RestaurantProductItem()
                    product_item["sequence_number"] = self.count
                    product_item["source_product_id"] = det["id"]
                    name = det["name"].strip()
                    if name == "Insider Delivery 5-Pack" or name == "Insider Delivery 10-Pack":
                        continue
                    else:
                        product_item["product_name"] = name
                    product_item["price"] = float("{0:.2f}".format(det["cost"] / 100.))
                    product_item["pc_count"] = 1
                    product_item["description"] = det["description"]
                    product_item["product_image"] = det["images"]["image_url_1_by_1"]
                    product_item["url"] = f'https://order.goopkitchen.com/store/{restaurant_item["source_id"]}/{restaurant_item["location_name"]}/{menu_item["source_category_id"]}/{menu_item["category_name"]}/{product_item["source_product_id"]}/{product_item["product_name"]}?filter=85'
                    product_list.append(product_item)
                    self.count+=1

            menu_item["products"] = product_list
            menus.append(menu_item)
            restaurant_item["menus"] = menus
        self.count=1
        yield restaurant_item

    