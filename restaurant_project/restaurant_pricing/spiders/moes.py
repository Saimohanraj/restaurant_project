import json

from restaurant_pricing.items import (
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem,
)

from restaurant_pricing.spiders import OloBaseSpider


class MoesSpider(OloBaseSpider):
    name = "moes"
    domain = "https://order.moes.com"

    base_and_customize_keywords = [
        "Protein Choice #1",
        "Choose Your Protein",
        "Choose your Protein",
        "Taco #1",
        "Item",
        "Make It a Meal",
    ]

    base_only_keywords = [
        "Bottled Water",
        "Bottled 20 oz Soft Drinks:",
        "Hubert’s Lemonaded",
    ]

    default_base_keywords = ["Flavor:"]

    async def parse_api_menu(self, response, restaurant_item=None, source_id=None):
        json_data = json.loads(response.text)

        menus = []
        for category in json_data.get("categories", []):
            menu_item = RestaurantMenuItem()
            menu_item["source_category_id"] = category.get("id")
            menu_item["category_name"] = category.get("name")

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

                    product_response = await self.parse_options_group(
                        option_groups, source_id
                    )
                    base_options = []
                    if product_response.status == 404:
                        base_item = RestaurantBaseItem()
                        base_item["description"] = "Default"
                        base_item["base"] = "Default"
                        base_item["base_price"] = ""

                        base_options.append(base_item)
                        product_item["base_options"] = base_options
                        product_list.append(product_item)
                        menu_item["products"] = product_list
                        continue

                    response_json_data = json.loads(product_response.text)

                    # contains both base and add-ons details
                    if any(
                        match in response_json_data["optionGroups"][0]["description"]
                        for match in self.base_and_customize_keywords
                    ):
                        # new lines to collect both regular and junior base details
                        junior_id = ""
                        if (
                            response_json_data["optionGroups"][0]["description"]
                            == "Item"
                            and len(response_json_data["optionGroups"][0]["choices"])
                            == 2
                        ):
                            junior_ids = [
                                choice["optionGroups"][0]
                                for choice in response_json_data.get("choices", [])
                                if choice["name"].strip() == "Junior"
                                and len(choice["optionGroups"]) > 0
                            ]

                            if len(junior_ids) > 0:
                                junior_id = junior_ids[0]
                                option_groups.append(junior_id)
                                product_response = await self.parse_options_group(
                                    option_groups, source_id
                                )

                                response_json_data = json.loads(product_response.text)

                        if (
                            response_json_data["optionGroups"][0]["description"]
                            == "Item"
                            and len(response_json_data["optionGroups"][0]["choices"])
                            == 1
                            and response_json_data["choices"][0]["name"] == "Junior"
                        ):
                            junior_ids = [
                                choice["optionGroups"][0]
                                for choice in response_json_data.get("choices", [])
                                if choice["name"].strip() == "Junior"
                                and len(choice["optionGroups"]) > 0
                            ]

                            if len(junior_ids) > 0:
                                junior_id = junior_ids[0]
                                option_groups.append(junior_id)
                                product_response = await self.parse_options_group(
                                    option_groups, source_id
                                )

                                response_json_data = json.loads(product_response.text)

                        if response_json_data["optionGroups"][0][
                            "description"
                        ] == "Item" and "Modify Proteins:" in [
                            x["description"] for x in response_json_data["optionGroups"]
                        ]:
                            response_json_data["optionGroups"] = [
                                x
                                for x in response_json_data["optionGroups"]
                                if x["description"].lower().startswith("make it a meal")
                            ]
                        # certain products has same description but different templates, hence filtered based on those product names
                        if product_item["product_name"] in [
                            "Chicken Club Quesadilla",
                            "Spicy Chicken Bowl",
                            "Chicken Club Bowl",
                            "BBQ Bowl",
                            "Gluten Friendly Bowl",
                            "High Protein Bowl",
                            "Steak and Queso Bowl",
                            "Steak and Queso Quesadilla",
                        ] and "Modify Proteins:" in [
                            x["description"] for x in response_json_data["optionGroups"]
                        ]:
                            response_json_data["optionGroups"] = [
                                x
                                for x in response_json_data["optionGroups"]
                                if x["description"].lower().startswith("make it a meal")
                                or x["description"]
                                .lower()
                                .startswith("choose your protein")
                            ]

                        for opt in response_json_data.get("optionGroups", []):
                            description = opt["description"]

                            for choice in response_json_data.get("choices", []):
                                if choice["id"] in opt["choices"]:
                                    base_item = RestaurantBaseItem()
                                    base_item["description"] = description
                                    base_item["base"] = choice.get("name")
                                    if base_item["base"] in ["Regular", "Junior"]:
                                        continue
                                    # new lines to concat regular and junior to base name
                                    if junior_id and opt["id"] == junior_id:
                                        base_item["base"] = (
                                            "Junior " + base_item["base"]
                                        )
                                    elif (
                                        junior_id
                                        and opt["id"] != junior_id
                                        and base_item["base"] != "Make It a Meal"
                                    ):
                                        base_item["base"] = (
                                            "Regular " + base_item["base"]
                                        )
                                    # end of new lines
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
                                        # start of new lines for guacamole fix in "make it a meal"
                                        if (
                                            customize_json_data["optionGroups"][0][
                                                "description"
                                            ]
                                            == "Side"
                                        ):

                                            customize_response_ids = customize_json_data[
                                                "optionGroups"
                                            ][
                                                0
                                            ][
                                                "choices"
                                            ]

                                            customize_ids = []
                                            for choice_id in customize_json_data[
                                                "choices"
                                            ]:
                                                if (
                                                    choice_id["id"]
                                                    in customize_response_ids
                                                    and choice_id["name"] != "Queso"
                                                ):
                                                    if (
                                                        len(choice_id["optionGroups"])
                                                        > 0
                                                    ):
                                                        customize_ids.append(
                                                            str(
                                                                choice_id[
                                                                    "optionGroups"
                                                                ][0]
                                                            )
                                                        )

                                            customize_id_clean = customize_response_str.url.split(
                                                "ids%5B%5D="
                                            )

                                            customize_id_clean.remove(
                                                f"https://order.moes.com/api/vendors/{str(source_id)}/optiongroups/?"
                                            )

                                            customize_id_clean = [
                                                customize_id.replace("&", "")
                                                if "&" in customize_id
                                                else customize_id
                                                for customize_id in customize_id_clean
                                            ]
                                            customize_ids = (
                                                customize_ids + customize_id_clean
                                            )

                                            customize_response_str = await self.parse_options_group(
                                                customize_ids, source_id
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

                                                    if (
                                                        add_on_name
                                                        == "Modify Proteins:"
                                                    ):
                                                        modify_id = add_on.get(
                                                            "optionGroups"
                                                        )[0]
                                                        customize_url = f"https://order.moes.com/api/vendors/{source_id}/optiongroups/?ids%5B%5D={modify_id}"
                                                        customize_response_str = await self.request_process(
                                                            customize_url
                                                        )
                                                        customize_json_data = json.loads(
                                                            customize_response_str.text
                                                        )

                                                        modify_add_ons = await self.add_ons_process(
                                                            customize_json_data,
                                                            source_id,
                                                        )

                                                        add_ons.extend(modify_add_ons)

                                                    else:
                                                        add_on_item[
                                                            "sub_name"
                                                        ] = add_on.get("name")
                                                        add_on_item[
                                                            "price"
                                                        ] = add_on.get(
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

                    # contains only base details without add-ons
                    elif any(
                        match in response_json_data["optionGroups"][0]["description"]
                        for match in self.base_only_keywords
                    ):
                        meal_ids = response_json_data["optionGroups"][0]["choices"]

                        for choice in response_json_data.get("choices", []):
                            base_item = RestaurantBaseItem()
                            base_item["description"] = response_json_data[
                                "optionGroups"
                            ][0]["description"]
                            base_item["base"] = choice.get("name")
                            base_item["base_price"] = choice.get("priceDifference")
                            base_id = choice.get("id")
                            if base_id in meal_ids:
                                base_options.append(base_item)

                    # contains only base as default without add-ons
                    elif any(
                        match in response_json_data["optionGroups"][0]["description"]
                        for match in self.default_base_keywords
                    ):
                        base_item = RestaurantBaseItem()
                        base_item["description"] = "Default"
                        base_item["base"] = "Default"
                        base_item["base_price"] = ""
                        base_options.append(base_item)

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
