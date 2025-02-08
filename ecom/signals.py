from django.db.models.signals import pre_save
from django.dispatch import receiver
from google import genai
from .models import Product
import logging

client = genai.Client(api_key="AIzaSyBt126CxGPUXZKKKW3JKnUj5VXlsSVHxVg")

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Product)
def set_product_fields(sender, instance, **kwargs):
    # Set weather_tag if it's empty or invalid
    if not instance.weather_tag or instance.weather_tag in ["", "nan", "error"]:
        try:
            weather_response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=(
                    f"classify product name to three preferences (winter, summer, rain). "
                    f"Example: tea or coffee useful for warm up... so it's best case needed in winter or rain. "
                    f"Beverage (such as bottled water, but milk is for all) usually needed in warm weather"
                    f"I will give you single product name (might include brand name or others), "
                    f"and you'll answer in a single word. If you can't and which goes for all, reply: NA. "
                    f"The product name is {instance.name}. Don't apply a Western-centric view to the product classification. "
                    f"ie: In western bbq trend in summer, but in Bangladesh in winter"
                    f"For Bangladesh remedies (Badminton plays in winter), popular activity."
                )
            )
            instance.weather_tag = weather_response.text.strip()
        except Exception as e:
            logger.error(f"Error fetching weather tag for product '{instance.name}': {e}")
            instance.weather_tag = "error"  # Fallback value for weather_tag

    # Set category if it's empty or invalid
    if not instance.category or instance.category in ["", "nan", "error"]:
        try:
            category_response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=(
                    f"Classify the product name into a category based on general use, as ecommerce sites category."
                    f"I will give you single product name (might include brand name or others), "
                    f"and you'll answer just the category name (Title). Do not use & anywhere, use and."
                    f"Examples: Electronic Devices, Electronic Accessories, Home Appliances, Health and Beauty, Baby and Toys, Home and Lifestyle, Women's Fashion, Men's Fashion, Watches and Accessories, Sports and Outdoor, Automotive and Motorbike, Digital Goods, Grocery, Pets Item, etc."
                    f"If the product doesn't fit into any specific category or If you can'tcategory, reply: NA. "
                    f"The product name is {instance.name}."
                )
            )
            instance.category = category_response.text.strip()
        except Exception as e:
            logger.error(f"Error fetching category for product '{instance.name}': {e}")
            instance.category = "error"  # Fallback value for category


