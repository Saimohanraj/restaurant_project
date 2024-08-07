import json
import scrapy
from restaurant_pricing.items import (
    RestaurantItem,
    RestaurantScheduleItem,
    RestaurantMenuItem,
    RestaurantProductItem,
    RestaurantBaseItem,
    RestaurantAddOnItem,
)


class OloBaseSpider(scrapy.Spider):
    name = "olo_base_spider"
    domain = "order.olo.com"
    base_and_customize_keywords = []
    not_base_customize_keywords = []
    base_only_keywords = []
    default_base_keywords = []

    api_headers = {
        "Accept": "application/json, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        "__RequestVerificationToken": "",
        "X-Requested-With": "XMLHttpRequest",
        "X-Olo-Request": "1",
        "X-Olo-Viewport": "Desktop",
        "X-Olo-App-Platform": "web",
        "X-Olo-Country": "us",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "TE": "trailers",
    }

    def __init__(self, *args, **kwargs):
        filter_state_code = kwargs.get("state_code")
        self.filter_state_code = (
            filter_state_code.split(",") if filter_state_code else []
        )
        self.filter_state_code = {state.upper() for state in self.filter_state_code}
        super().__init__(*args, **kwargs)

    def start_requests(self):
        yield scrapy.Request(f"{self.domain}/locations", callback=self.parse_locations)

    def parse_locations(self, response):
        yield response.follow(
            f"{self.domain}/api/vendors/regions?excludeCities=true",
            headers=self.api_headers,
            callback=self.parse_api_locations,
        )

    def parse_api_locations(self, response):
        json_data = json.loads(response.text)
        available_states = {state.get("code") for state in json_data}

        self.filter_state_code = (
            self.filter_state_code.intersection(available_states)
            if self.filter_state_code
            else available_states
        )

        for state in self.filter_state_code:

            yield response.follow(
                f"{self.domain}/api/vendors/search/{state}",
                headers=self.api_headers,
                callback=self.parse_api_state,
            )

    def parse_api_state(self, response):
        json_data = json.loads(response.text)

        for restaurant in json_data.get("vendor-search-results"):
            restaurant_item = RestaurantItem()
            restaurant_item["source_id"] = restaurant.get("id")
            restaurant_item["location_name"] = restaurant.get("name")
            restaurant_item["url"] = f"{self.domain}/menu/{restaurant.get('slug')}"
            restaurant_item["phone_number"] = restaurant.get("phoneNumber")

            address = restaurant.get("address", {})
            restaurant_item["street_address_1"] = address.get("streetAddress")
            restaurant_item["street_address_2"] = address.get("streetAddress2")
            restaurant_item["street_address_3"] = address.get("crossStreet")
            restaurant_item["city"] = address.get("city")
            restaurant_item["postal_code"] = address.get("postalCode")
            restaurant_item["state"] = address.get("state")
            restaurant_item["country"] = address.get("country")
            restaurant_item["latitude"] = restaurant.get("latitude")
            restaurant_item["longitude"] = restaurant.get("longitude")
            restaurant_item["type"] = restaurant.get("supportedHandoffModes")
            schedule = []

            for weekly_schedule in restaurant.get("weeklySchedule", {}).get(
                "calendars", []
            ):
                schedule_item = RestaurantScheduleItem()
                operation_type = weekly_schedule.get("scheduleDescription")
                if operation_type == "Business":
                    schedule_item["type"] = "CounterPickup"
                elif operation_type == "Drive-thru":
                    schedule_item["type"] = "DriveThru"
                elif operation_type == "Delivery":
                    schedule_item["type"] = "Dispatch"
                elif operation_type == "Park & Get It (Curbside)":
                    schedule_item["type"] = "CurbsidePickup"
                else:
                    schedule_item["type"] = operation_type

                for day_schedule in weekly_schedule.get("schedule"):
                    weekday = day_schedule.get("weekDay")
                    if weekday and weekday.lower() in [
                        "sunday",
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                    ]:
                        schedule_item[weekday.lower()] = day_schedule.get("description")
                schedule.append(schedule_item)
            restaurant_item["schedules"] = schedule

            yield response.follow(
                f"{self.domain}/api/vendors/{restaurant.get('slug')}",
                headers=self.api_headers,
                callback=self.parse_api_menu,
                cb_kwargs={
                    "restaurant_item": restaurant_item,
                    "source_id": restaurant_item["source_id"],
                },
            )

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

                    response_json_data = json.loads(product_response.text)

                    # contains both base and add-ons details
                    if not any(
                        match in response_json_data["optionGroups"][0]["description"]
                        for match in self.not_base_customize_keywords
                    ):
                        for choice in response_json_data.get("choices", []):
                            base_item = RestaurantBaseItem()
                            base_item["description"] = response_json_data[
                                "optionGroups"
                            ][0]["description"]
                            base_item["base"] = choice.get("name")
                            base_item["base_price"] = choice.get("priceDifference")

                            if base_item["base"] == "Customize Item":
                                continue

                            customize_id = choice["optionGroups"][0]

                            customize_url = f"{self.domain}/api/vendors/{source_id}/optiongroups/?ids%5B%5D={customize_id}"
                            customize_response_str = await self.request_process(
                                customize_url
                            )
                            customize_json_data = json.loads(
                                customize_response_str.text
                            )

                            add_ons = await self.add_ons_process(
                                customize_json_data, source_id
                            )

                            base_item["add_ons"] = add_ons
                            base_options.append(base_item)

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

            for customize in response.get("choices", []):
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

    async def request_process(self, url):
        request = scrapy.Request(url, headers=self.api_headers,)
        response = await self.crawler.engine.download(request, self)

        return response

    async def parse_options_group(self, option_groups, source_id):
        option_groups = [str(option) for option in option_groups]
        optiongroups = "&ids%5B%5D=".join(option_groups)

        option_groups_url = f"{self.domain}/api/vendors/{source_id}/optiongroups/?ids%5B%5D={optiongroups}"
        options_group_response = await self.request_process(option_groups_url)

        return options_group_response
