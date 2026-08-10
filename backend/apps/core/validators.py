"""
Shared image validators for file uploads.

Every app that accepts image uploads should import from here
rather than duplicating _validate_image_content / _validate_image_size.
"""
from django.core.exceptions import ValidationError


def validate_image_size(image, limit_mb=10):
    """Reject images larger than *limit_mb* MB."""
    if image.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Image file too large (max {limit_mb} MB).")


def validate_image_content(image):
    """Verify the uploaded file is a valid image and strip EXIF metadata.

    Uses Pillow to:
    1. Verify it is a real image (not a renamed .exe / script)
    2. Confirm the format is allowed (jpeg, png, webp)
    3. Strip EXIF/GPS metadata before saving (privacy)
    """
    from PIL import Image
    import io

    allowed = {'jpeg', 'png', 'webp'}

    try:
        img = Image.open(image)
    except Exception:
        raise ValidationError(
            'The uploaded file is not a valid image. Please upload a JPG, PNG, or WebP file.'
        )

    try:
        fmt = (img.format or '').lower()
    except Exception:
        raise ValidationError(
            'Could not determine the image format. Please upload a JPG, PNG, or WebP file.'
        )

    if fmt not in allowed:
        raise ValidationError(
            f"Unsupported image format: {fmt or 'unknown'}. "
            f"Allowed: {', '.join(sorted(allowed))}."
        )

    # Strip EXIF data by re-saving without metadata
    try:
        data = list(img.getdata())
        cleaned = Image.new(img.mode, img.size)
        cleaned.putdata(data)

        buf = io.BytesIO()
        save_format = 'JPEG' if fmt in ('jpeg', 'jpg') else fmt.upper()
        cleaned.save(buf, format=save_format, quality=85)
        buf.seek(0)

        # Replace the uploaded file content with the cleaned version
        image.file = buf
        image.size = buf.getbuffer().nbytes
    except Exception as e:
        raise ValidationError(
            f"Failed to process the image: {e}. Please try a different file."
        )
