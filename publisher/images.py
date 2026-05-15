import os
import sys

from google.cloud import storage as gcs_storage
from PIL import Image

from config import PUBLISHER_DIR


def process_images(slug: str, date_path: str) -> None:
    """Process all images in publisher/staging/<slug>/ and upload variants to GCS."""
    staging_dir = os.path.join(PUBLISHER_DIR, "staging", slug)

    if not os.path.exists(staging_dir):
        print(f"Staging folder not found: {staging_dir}")
        sys.exit(1)

    image_extensions = (".png", ".jpg", ".jpeg")
    images = [f for f in os.listdir(staging_dir) if f.lower().endswith(image_extensions)]

    if not images:
        print(f"No images found in: {staging_dir}")
        return

    client = gcs_storage.Client()
    bucket = client.bucket("stephenoravec-media")

    for filename in images:
        source_path = os.path.join(staging_dir, filename)
        name = os.path.splitext(filename)[0]
        gcs_prefix = f"blog/{date_path}/{name}"

        img = Image.open(source_path)

        sizes = {
            "1000": 1000,
            "2000": 2000,
            "400": 400,
        }

        for suffix, width in sizes.items():
            if img.width > width:
                ratio = width / img.width
                height = int(img.height * ratio)
                resized = img.resize((width, height), Image.Resampling.LANCZOS)
            else:
                resized = img.copy()

            temp_path = os.path.join(staging_dir, f"{name}-{suffix}.webp")
            resized.save(temp_path, "WEBP", quality=85)

            blob = bucket.blob(f"{gcs_prefix}-{suffix}.webp")
            blob.upload_from_filename(temp_path)
            print(f"Uploaded: {gcs_prefix}-{suffix}.webp")

            os.remove(temp_path)

        og_width = 1200
        og_height = 630
        og_ratio = og_width / og_height
        img_ratio = img.width / img.height

        if img_ratio > og_ratio:
            new_width = int(img.height * og_ratio)
            left = (img.width - new_width) // 2
            cropped = img.crop((left, 0, left + new_width, img.height))
        else:
            new_height = int(img.width / og_ratio)
            top = (img.height - new_height) // 2
            cropped = img.crop((0, top, img.width, top + new_height))

        og = cropped.resize((og_width, og_height), Image.Resampling.LANCZOS)
        og_temp_path = os.path.join(staging_dir, f"{name}-og.webp")
        og.save(og_temp_path, "WEBP", quality=85)

        blob = bucket.blob(f"{gcs_prefix}-og.webp")
        blob.upload_from_filename(og_temp_path)
        print(f"Uploaded: {gcs_prefix}-og.webp")

        os.remove(og_temp_path)

        blob = bucket.blob(f"{gcs_prefix}-original{os.path.splitext(filename)[1]}")
        blob.upload_from_filename(source_path)
        print(f"Uploaded: {gcs_prefix}-original{os.path.splitext(filename)[1]}")