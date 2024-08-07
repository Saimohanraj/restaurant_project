import json
import pandas as pd


with open("sample.json", "r") as f:
    json_file = f.read()

json_data = json.loads(json_file)


def restaurant_data(json_data):
    restaurant_data_list = []

    for data in json_data:
        restaurant_data = {}
        restaurant_data["source_id"] = data.get("source_id", "")
        restaurant_data["name"] = data.get("name", "")
        restaurant_data["url"] = data.get("url", "")
        restaurant_data["phone_number"] = data.get("phone_number", "")
        restaurant_data["street_address_1"] = data.get("street_address_1", "")
        restaurant_data["street_address_2"] = data.get("street_address_2", "")
        restaurant_data["street_address_3"] = data.get("street_address_3", "")
        restaurant_data["city"] = data.get("city", "")
        restaurant_data["postal_code"] = data.get("postal_code", "")
        restaurant_data["state"] = data.get("state", "")
        restaurant_data["country"] = data.get("country", "")
        restaurant_data["latitude"] = data.get("latitude", "")
        restaurant_data["longitude"] = data.get("longitude", "")
        types = data.get("type", [])
        restaurant_data["CurbsidePickup"] = True if "CurbsidePickup" in types else False
        restaurant_data["DriveThru"] = True if "DriveThru" in types else False
        restaurant_data["Dispatch"] = True if "Dispatch" in types else False
        restaurant_data["CounterPickup"] = True if "CounterPickup" in types else False

        restaurant_data_list.append(restaurant_data)

    df = pd.DataFrame(restaurant_data_list)
    df.to_csv("restaurant_data.csv", index=None, encoding="utf-8-sig")


def restaurant_menus(json_data):
    product_data_list = []

    for data in json_data:
        source_id = data.get("source_id", "")
        name = data.get("name", "")
        for menu in data["menus"]:
            source_category_id = menu.get("source_category_id", "")
            category_name = menu.get("category_name", "")

            for product in menu.get("products", []):
                product_data = {}
                product_data["source_id"] = source_id
                product_data["name"] = name
                product_data["source_category_id"] = source_category_id
                product_data["category_name"] = category_name
                product_data["sequence_number"] = product.get(
                    "sequence_number", "")
                product_data["source_product_id"] = product.get(
                    "source_product_id", "")
                product_data["product_name"] = product.get("product_name", "")
                product_data["description"] = product.get("description", "")
                product_data["price"] = product.get("price", "")
                product_data["min_calories"] = product.get("min_calories", "")
                product_data["max_calories"] = product.get("max_calories", "")
                product_data["product_image"] = product.get(
                    "product_image", "")
                product_data_list.append(product_data)

    df = pd.DataFrame(product_data_list)

    df.to_csv("restaurant_menus.csv", index=None, encoding="utf-8-sig")


def restaurant_addons(json_data):
    product_data_list = []

    for data in json_data:
        source_id = data.get("source_id", "")
        name = data.get("name", "")
        for menu in data["menus"]:
            source_category_id = menu.get("source_category_id", "")
            category_name = menu.get("category_name", "")

            for product in menu.get("products", []):
                source_product_id = product.get("source_product_id", "")
                product_name = product.get("product_name", "")
                if not product.get("base_options", []):
                    items = {}
                    items["source_id"] = source_id
                    items["name"] = name
                    # menu
                    items["source_category_id"] = source_category_id
                    items["category_name"] = category_name
                    # product
                    items["source_product_id"] = source_product_id
                    items["product_name"] = product_name
                    product_data_list.append(items)
                    continue

                for base_option in product["base_options"]:
                    base_opt = {}
                    description = base_option.get("description", "")
                    base = base_option.get("base", "")
                    base_price = base_option.get("base_price", "")
                    if not base_option.get("add_ons", ""):
                        base_opt["source_id"] = source_id
                        base_opt["name"] = name
                        # menu
                        base_opt["source_category_id"] = source_category_id
                        base_opt["category_name"] = category_name
                        # product
                        base_opt["source_product_id"] = source_product_id
                        base_opt["product_name"] = product_name
                        # base option
                        base_opt["description"] = description
                        base_opt["base"] = base
                        base_opt["base_price"] = base_price
                        product_data_list.append(base_opt)
                        continue
                    for addon in base_option["add_ons"]:
                        addon_data = {}
                        # branch
                        addon_data["source_id"] = source_id
                        addon_data["name"] = name
                        # menu
                        addon_data["source_category_id"] = source_category_id
                        addon_data["category_name"] = category_name
                        # product
                        addon_data["source_product_id"] = source_product_id
                        addon_data["product_name"] = product_name
                        # base option
                        addon_data["description"] = description
                        addon_data["base"] = base
                        addon_data["base_price"] = base_price
                        # Addons
                        addon_data["add_on_name"] = addon.get(
                            "add_on_name", "")
                        addon_data["sub_name"] = addon.get("sub_name", "")
                        addon_data["price"] = addon.get("price", "")

                        product_data_list.append(addon_data)

    df = pd.DataFrame(product_data_list)
    df.to_csv("restaurant_addons.csv", index=None, encoding="utf-8-sig")


def process_csv():
    restaurant_data(json_data)
    restaurant_menus(json_data)
    restaurant_addons(json_data)


process_csv()
