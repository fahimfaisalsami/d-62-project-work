import os
import shutil
import pandas as pd
from django.core.management.base import BaseCommand
from ecom.models import Product  # Import your Product model
from django.conf import settings

class Command(BaseCommand):
    help = "Import products from an Excel file"

    def handle(self, *args, **kwargs):
        # Set file paths
        excel_file_path = r"C:\Users\ThinkPad\Downloads\Project-20250203T205101Z-001\Project\updated_file.xlsx"
        images_source_folder = r"C:\Users\ThinkPad\Downloads\Project-20250203T205101Z-001\Project\Product list images"
        images_destination_folder = os.path.join(settings.BASE_DIR, "static", "product_image")

        if not os.path.exists(excel_file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {excel_file_path}"))
            return

        # Ensure the destination folder exists
        os.makedirs(images_destination_folder, exist_ok=True)

        # Read the Excel file
        df = pd.read_excel(excel_file_path, engine="openpyxl")

        for _, row in df.iterrows():
            product_name = row.get("name", "").strip()
            product_image_filename = row.get("product_image", "").strip()  # Only filename
            price = row.get("price", 0)
            description = str(row.get("description", "")).strip()

            category = str(row.get("category", "")).strip()  # Ensures it's always a string

            weather_tag = str(row.get("weather_tag", "")).strip()  # Ensures it's always a string


            # Build full path of the image in source folder
            source_image_path = os.path.join(images_source_folder, product_image_filename)

            # Destination path inside Django static folder
            destination_image_path = os.path.join(images_destination_folder, product_image_filename)
            relative_image_path = f"product_image/{product_image_filename}"  # Relative path for Django

            # Move image if it exists
            if os.path.exists(source_image_path):
                shutil.copy(source_image_path, destination_image_path)  # Copy instead of move to keep original
                self.stdout.write(self.style.SUCCESS(f"Image copied: {product_image_filename}"))
            else:
                self.stdout.write(self.style.ERROR(f"Image not found: {source_image_path}"))
                continue  # Skip this product if image is missing

            # Create or update the product
            product, created = Product.objects.update_or_create(
                name=product_name,
                defaults={
                    "product_image": relative_image_path,  # Save relative path
                    "price": price,
                    "description": description,
                    "category": category,
                    "weather_tag": weather_tag,
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} product: {product_name}"))

        self.stdout.write(self.style.SUCCESS("Excel file imported successfully!"))
