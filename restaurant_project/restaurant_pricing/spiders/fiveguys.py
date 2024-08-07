import json
from restaurant_pricing.items import (
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem,
)
from restaurant_pricing.spiders import OloBaseSpider


class FiveGuysSpider(OloBaseSpider):

    name = "fiveguys"
    domain = "https://order.fiveguys.com"

    base_and_customize_keywords = [
        "Prefer no bun?",
        "Select Unlimited Toppings:"
    ]

    async def parse_api_menu(self, response, restaurant_item=None, source_id=None):
        json_data = json.loads(response.text)

        menus = []
        for category in json_data.get("categories", []):
            menu_item = RestaurantMenuItem()
            menu_item["source_category_id"] = category.get("id")
            menu_item["category_name"] = category.get("name")

            if menu_item["category_name"].strip() == "Special Assistance Required":
                continue

            product_list = []
            for sequence_number, product in enumerate(json_data.get("products", []), 1):
                product_item = RestaurantProductItem()
                if menu_item["source_category_id"] == product.get("category"):
                    product_item["sequence_number"] = sequence_number
                    product_item["source_product_id"] = product.get("id")
                    product_item["product_name"] = product.get("name")
                    product_item["description"] = product.get("description")
                    product_item["price"] = product.get("baseCost")
                    product_item["min_calories"] = product.get("baseCalories")
                    product_item["max_calories"] = product.get("maxCalories")
                    for image in product.get("images", []):
                        product_item["product_image"] = image.get("filename")

                    if len(product.get("optionGroups")) >= 1:
                        option_groups = product.get("optionGroups")
                    else:
                        product_list.append(product_item)
                        menu_item["products"] = product_list
                        continue

                    if menu_item["category_name"] == "Drinks" or menu_item["category_name"] == "Shakes":
                        product_list.append(product_item)
                        menu_item["products"] = product_list
                        continue               

                    product_response = await self.parse_options_group(
                        option_groups, source_id
                    )

                    base_options = []
                    response_json_data = json.loads(product_response.text)

                    # contains both base and add-ons details
                    if any(
                        match in response_json_data["optionGroups"][0]["description"]
                        for match in self.base_and_customize_keywords
                    ):
                        for opt in response_json_data.get("optionGroups", []):
                            description = opt["description"]

                            for choice in response_json_data.get("choices", []):
                                if choice["id"] in opt["choices"]:
                                    base_item = RestaurantBaseItem()
                                    base_item["description"] = description
                                    base_item["base"] = choice.get("name")
                                    base_item["base_price"] = choice.get(
                                        "priceDifference"
                                    )

                                    customize_id = choice["optionGroups"]

                                    if len(customize_id) == 0:
                                        base_options.append(base_item)
                                        continue
                                    else:
                                        customize_response_str = await self.parse_options_group(
                                            customize_id, source_id
                                        )

                                        customize_json_data = json.loads(
                                            customize_response_str.text
                                        )

                                        add_ons = []
                                        for base_data in customize_json_data.get(
                                            "optionGroups", []
                                        ):
                                            add_on_name = base_data["description"]
                                            for add_on in customize_json_data.get(
                                                "choices", []
                                            ):
                                                if add_on["id"] in base_data["choices"]:
                                                    add_on_item = RestaurantAddOnItem()
                                                    add_on_item[
                                                        "add_on_name"
                                                    ] = add_on_name

                                                    add_on_item[
                                                        "sub_name"
                                                    ] = add_on.get("name")
                                                    add_on_item["price"] = add_on.get(
                                                        "priceDifference"
                                                    )

                                                    if add_on_item["price"] == None:
                                                        add_on_item["price"] = 0
                                                    else:
                                                        add_on_item[
                                                            "price"
                                                        ] = add_on_item["price"]

                                                    add_ons.append(add_on_item)

                                    base_item["add_ons"] = add_ons
                                    base_options.append(base_item)

                        product_item["base_options"] = base_options
                        product_list.append(product_item)

                        menu_item["products"] = product_list
                        continue

                    # contains add-ons details with base as default
                    else:
                        base_item = RestaurantBaseItem()
                        base_item["description"] = "Default"
                        base_item["base"] = "Default"
                        base_item["base_price"] = ""

                        add_ons = await self.add_ons_process(
                            response_json_data, source_id
                        )
                        base_item["add_ons"] = add_ons
                        base_options.append(base_item)

                    product_item["base_options"] = base_options
                    product_list.append(product_item)

                menu_item["products"] = product_list

            menus.append(menu_item)
        restaurant_item["menus"] = menus

        yield restaurant_item

    async def add_ons_process(self, response, source_id):
        customize_check = response.get("choices", [])[0]["optionGroups"]

        if customize_check:
            for customize in response.get("choices", []):
                customize_option_ids = customize.get("optionGroups", [])

                if customize_option_ids:
                    add_on_response_str = await self.parse_options_group(
                        customize_option_ids, source_id
                    )

                    add_on_json_data = json.loads(add_on_response_str.text)

                    add_ons = []
                    for opt in add_on_json_data.get("optionGroups", []):
                        add_on_name = opt["description"]

                        for add_on in add_on_json_data.get("choices", []):
                            if add_on["id"] in opt["choices"]:
                                add_on_item = RestaurantAddOnItem()
                                add_on_item["add_on_name"] = add_on_name
                                add_on_item["sub_name"] = add_on.get("name")
                                add_on_item["price"] = add_on.get("priceDifference")

                                if add_on_item["price"] == None:
                                    add_on_item["price"] = 0
                                else:
                                    add_on_item["price"] = add_on_item["price"]
                                add_ons.append(add_on_item)

        else:
            add_ons = []
            add_on_name = response.get("optionGroups")[0]["description"]

            for opt in response.get("optionGroups", []):
                add_on_name = opt["description"]

                for customize in response.get("choices", []):
                    if customize["id"] in opt["choices"]:
                        add_on_item = RestaurantAddOnItem()
                        add_on_item["add_on_name"] = add_on_name
                        add_on_item["sub_name"] = customize.get("name")
                        add_on_item["price"] = customize.get("priceDifference")

                        if add_on_item["price"] == None:
                            add_on_item["price"] = 0
                        else:
                            add_on_item["price"] = add_on_item["price"]

                        add_ons.append(add_on_item)

        return add_ons    