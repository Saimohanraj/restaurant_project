from restaurant_pricing.spiders import OloBaseSpider


class DeltacoSpider(OloBaseSpider):
    name = "deltaco"
    domain = "https://order.deltaco.com"

    not_base_customize_keywords = [
        "Customize",
        "Choose Size",
        "Choose Meal Size",
        "Meal",
        "Choose Your Dipping Sauce",
        "Crispy Chicken & Fries Box",
        "Choose 1st Taco",
        "Choose Bean & Cheese Burrito",
        "Choose One",
        "Choose Dressing",
        "Fiesta Pack",
        "Quesadilla Kid Loco® Meal",
        "Bean & Cheese Burrito Kid Loco® Meal",
        "Value Taco Kid Loco® Meal",
        "Crispy Chicken & Fries Box Meal",
        "Choose Burrito",
    ]

    base_only_keywords = [
        "Choose Size",
        "Meal",
        "Fiesta Pack",
        "Choose Burrito",
    ]

    default_base_keywords = [
        "Choose Your Dipping Sauce",
        "Crispy Chicken & Fries Box",
        "Choose 1st Taco",
        "Choose Bean & Cheese Burrito",
        "Choose One",
        "Choose Dressing",
    ]
