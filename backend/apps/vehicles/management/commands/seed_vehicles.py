import io
import logging
import random

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from apps.vehicles.models import Vehicle, VehicleImage, VehicleUnit

logger = logging.getLogger(__name__)


VEHICLE_SEEDS = [
    {'make': 'Toyota', 'model': 'Vios', 'year': 2024, 'type': 'sedan', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 2500, 'description': 'Fuel-efficient compact sedan. Perfect for city driving and daily commutes. Features Apple CarPlay, reverse camera, and excellent air conditioning.'},
    {'make': 'Toyota', 'model': 'Innova', 'year': 2024, 'type': 'mpv', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 4000, 'description': 'Spacious family MPV with powerful diesel engine. Ideal for out-of-town trips and large groups. Comfortable ride with ample cargo space.'},
    {'make': 'Toyota', 'model': 'Fortuner', 'year': 2023, 'type': 'suv', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 5500, 'description': 'Premium mid-size SUV with commanding road presence. 4x4 capability, leather seats, and advanced safety features. Perfect for both city and provincial roads.'},
    {'make': 'Honda', 'model': 'Civic', 'year': 2024, 'type': 'sedan', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 3500, 'description': 'Sporty and sophisticated sedan with turbocharged engine. Honda SENSING safety suite, premium audio, and responsive handling.'},
    {'make': 'Honda', 'model': 'CR-V', 'year': 2024, 'type': 'suv', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 4500, 'description': 'Refined compact SUV with spacious interior. Panoramic sunroof, wireless charging, and Honda LaneWatch camera.'},
    {'make': 'Mitsubishi', 'model': 'Xpander', 'year': 2023, 'type': 'mpv', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 3000, 'description': 'Versatile 7-seater with SUV-like styling. Great ground clearance, flexible seating configurations, and excellent value for families.'},
    {'make': 'Mitsubishi', 'model': 'Montero Sport', 'year': 2024, 'type': 'suv', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 5000, 'description': 'Rugged yet refined SUV with legendary reliability. 4x4 drivetrain, touchscreen infotainment, and premium interior finishes.'},
    {'make': 'Nissan', 'model': 'Terra', 'year': 2024, 'type': 'suv', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 4800, 'description': 'Bold full-size SUV with intelligent 4x4. 360-degree camera, dual-zone climate control, and Nissan Intelligent Mobility features.'},
    {'make': 'Ford', 'model': 'Ranger', 'year': 2024, 'type': 'pickup', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 5, 'price_per_day': 5000, 'description': 'Tough and capable pickup truck. Best-in-class towing capacity, SYNC 4 infotainment, and off-road ready with Terrain Management System.'},
    {'make': 'Hyundai', 'model': 'Stargazer', 'year': 2024, 'type': 'mpv', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 2800, 'description': 'Modern family MPV with futuristic styling. SmartSense safety suite, wireless Apple CarPlay, and flexible seating for up to 7 passengers.'},
    {'make': 'Suzuki', 'model': 'Ertiga', 'year': 2023, 'type': 'mpv', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 2200, 'description': 'Affordable and practical 7-seater. Excellent fuel economy, compact dimensions for easy city parking, and surprisingly spacious third row.'},
    {'make': 'Toyota', 'model': 'HiAce', 'year': 2024, 'type': 'van', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 14, 'price_per_day': 7000, 'description': 'Spacious commuter van for large groups. Perfect for family reunions, corporate shuttles, and tour groups. Powerful and reliable diesel engine.'},
    {'make': 'Mazda', 'model': 'CX-5', 'year': 2024, 'type': 'suv', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 4200, 'description': 'Premium compact SUV with stunning KODO design. SKYACTIV technology, Bose sound system, and driver-focused cockpit with Nappa leather.'},
    {'make': 'Toyota', 'model': 'Avanza', 'year': 2024, 'type': 'mpv', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 2500, 'description': 'Compact and efficient 7-seater. Perfect for young families and small businesses. Modern features in an affordable package.'},
    {'make': 'Isuzu', 'model': 'D-MAX', 'year': 2024, 'type': 'pickup', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 5, 'price_per_day': 4800, 'description': 'Legendary durability in a modern pickup. Best-in-class fuel efficiency with Blue Power diesel, advanced safety features, and proven reliability.'},
    {'make': 'Honda', 'model': 'City', 'year': 2024, 'type': 'sedan', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 2800, 'description': 'Stylish subcompact sedan with class-leading space. Honda SENSING, ultra-low fuel consumption, and refined ride quality for daily driving.'},
    {'make': 'BYD', 'model': 'Atto 3', 'year': 2024, 'type': 'suv', 'transmission': 'automatic', 'fuel': 'electric', 'seats': 5, 'price_per_day': 4000, 'description': 'All-electric compact SUV with impressive range. Blade Battery technology, rotating touchscreen, and near-silent driving experience. Zero emissions.'},
    {'make': 'Toyota', 'model': 'Corolla Cross', 'year': 2024, 'type': 'suv', 'transmission': 'automatic', 'fuel': 'hybrid', 'seats': 5, 'price_per_day': 3800, 'description': 'Hybrid compact SUV combining efficiency and versatility. Toyota Safety Sense, excellent fuel economy, and smooth hybrid powertrain.'},
]

# ── Real vehicle photo URLs (Unsplash — permanent, free, no API key) ──
# Each vehicle seed gets 2-3 images from these curated pools.
# Photos are automotive/vehicle themed and grouped by body type for variety.
REAL_IMAGE_URLS = {
    'sedan': [
        'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1502877338535-766e1452684a?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1550355291-bbee04a92027?w=800&h=500&fit=crop',
    ],
    'suv': [
        'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1541443131876-44b03de101c5?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1533106418989-88406c7cc8ca?w=800&h=500&fit=crop',
    ],
    'mpv': [
        'https://images.unsplash.com/photo-1559416523-140ddc3d238c?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1523987355523-c7b5b0dd90a7?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1546614042-7df3c24c9e5d?w=800&h=500&fit=crop',
    ],
    'van': [
        'https://images.unsplash.com/photo-1464219789935-c2d9d9aba644?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1551721434-8b94ddff0e6d?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1580674684081-7617fbf3d745?w=800&h=500&fit=crop',
    ],
    'pickup': [
        'https://images.unsplash.com/photo-1592861956120-e524fc739696?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=800&h=500&fit=crop',
        'https://images.unsplash.com/photo-1566576721346-d4a3b4eaeb55?w=800&h=500&fit=crop',
    ],
}

# Fallback pool — generic car images when type-specific pool is exhausted
_REAL_IMAGE_FALLBACK = [
    'https://images.unsplash.com/photo-1504214208698-ea1916a2195a?w=800&h=500&fit=crop',
    'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&h=500&fit=crop',
    'https://images.unsplash.com/photo-1555626906-fcf10d6851b4?w=800&h=500&fit=crop',
    'https://images.unsplash.com/photo-1485291571150-772bcfc10da5?w=800&h=500&fit=crop',
]

# ── Track which URLs each vehicle type has already used ──
# This ensures variety — different vehicles of the same type get
# different photos instead of all sharing the first URL in the pool.
_type_usage = {k: 0 for k in REAL_IMAGE_URLS}
_fallback_usage = 0


def _next_real_url(vehicle_type):
    """Round-robin through the photo pool for a given vehicle type.

    Falls back to the generic pool if the type is unknown or exhausted.
    """
    pool = REAL_IMAGE_URLS.get(vehicle_type)
    if not pool:
        return _next_fallback_url()
    idx = _type_usage[vehicle_type] % len(pool)
    _type_usage[vehicle_type] += 1
    return pool[idx]


def _next_fallback_url():
    global _fallback_usage
    idx = _fallback_usage % len(_REAL_IMAGE_FALLBACK)
    _fallback_usage += 1
    return _REAL_IMAGE_FALLBACK[idx]


def download_real_image(url, filename, max_size_mb=8):
    """Download an image from *url*, resize to 800px wide, strip EXIF,
    and return a :class:`ContentFile` suitable for Django's ImageField.

    On any failure (network error, bad response, corrupt image) the
    function logs a warning and returns ``None``.  The caller should
    fall back to :func:`generate_vehicle_image`.
    """
    try:
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Car-Rental-Seeder/1.0',
        })
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning('Failed to download %s: %s', url, e)
        return None

    try:
        img = Image.open(io.BytesIO(resp.content))
        fmt = (img.format or 'JPEG').upper()
        if fmt in ('JPG',):
            fmt = 'JPEG'

        # Resize to 800px wide, maintain aspect ratio
        if img.width > 800:
            ratio = 800 / img.width
            new_height = int(img.height * ratio)
            img = img.resize((800, new_height), Image.LANCZOS)

        # Strip EXIF by rebuilding the pixel data
        data = list(img.getdata())
        cleaned = Image.new(img.mode, img.size)
        cleaned.putdata(data)

        buf = io.BytesIO()
        cleaned.save(buf, format=fmt, quality=85)
        buf.seek(0)

        # Size check
        size_mb = buf.getbuffer().nbytes / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.warning('Image %s too large (%.1f MB), skipping', url, size_mb)
            return None

        return ContentFile(buf.read(), name=filename)
    except Exception as e:
        logger.warning('Failed to process image %s: %s', url, e)
        return None


def generate_vehicle_image(make, model, color=None):
    """Generate a placeholder image as last-resort fallback."""
    if color is None:
        color = random.choice([
            (52, 73, 94), (44, 62, 80), (127, 140, 141),
            (52, 152, 219), (41, 128, 185), (231, 76, 60),
            (192, 57, 43), (39, 174, 96), (46, 204, 113),
            (243, 156, 18), (155, 89, 182), (22, 160, 133),
            (211, 84, 0),
        ])

    width, height = 800, 500
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)

    body_color = tuple(max(0, c - 40) for c in color)
    draw.rectangle([150, 280, 650, 420], fill=body_color)
    draw.rectangle([250, 200, 550, 280], fill=body_color)
    draw.rectangle([270, 215, 380, 270], fill=(230, 240, 245))
    draw.rectangle([400, 215, 520, 270], fill=(230, 240, 245))
    draw.ellipse([200, 380, 260, 440], fill=(30, 30, 30))
    draw.ellipse([540, 380, 600, 440], fill=(30, 30, 30))
    draw.rectangle([620, 300, 645, 340], fill=(255, 255, 200))
    draw.rectangle([0, 440, 800, 500], fill=(60, 60, 60))
    for x in range(50, 700, 150):
        draw.rectangle([x, 468, x + 100, 472], fill=(255, 255, 255))

    try:
        font_large = ImageFont.truetype('arial.ttf', 36)
    except (IOError, OSError):
        font_large = ImageFont.load_default()

    text = f'{make} {model}'
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, 80), text, fill=(255, 255, 255), font=font_large)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = 'Seed the database with sample vehicles using real car photos from Unsplash.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing vehicles before seeding.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            Vehicle.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing vehicles.'))

        if Vehicle.objects.exists():
            self.stdout.write(self.style.WARNING(
                f'Database already has {Vehicle.objects.count()} vehicles. '
                'Use --clear to replace them.'
            ))
            return

        created = 0
        for seed in VEHICLE_SEEDS:
            vehicle = Vehicle.objects.create(**seed)

            # ── 2-3 images per vehicle: try real photos first ──
            num_images = random.randint(2, 3)
            real_count = 0
            for i in range(num_images):
                url = _next_real_url(seed['type'])
                filename = f'{seed["make"].lower()}_{seed["model"].lower()}_{i+1}.jpg'
                content = download_real_image(url, filename)
                if content is not None:
                    real_count += 1
                else:
                    # Fallback — generated placeholder
                    content = generate_vehicle_image(seed['make'], seed['model'])
                    if isinstance(content, ContentFile):
                        content = ContentFile(
                            content.read(),
                            name=f'{seed["make"].lower()}_{seed["model"].lower()}_{i+1}.jpg',
                        )

                VehicleImage.objects.create(
                    vehicle=vehicle,
                    image=content,
                    is_primary=(i == 0),
                )

            # ── 1-3 VehicleUnits with valid plate format ──
            num_units = random.randint(1, 3)
            for u in range(num_units):
                # Format: ABC-1234 (3 uppercase letters, dash, 3-4 digits)
                prefix = seed['make'][:3].upper().ljust(3, 'X')
                plate = f'{prefix}-{created:03d}{u+1}'
                VehicleUnit.objects.create(
                    vehicle=vehicle,
                    plate_number=plate,
                    status='available',
                    mileage=random.randint(1000, 50000),
                )

            img_source = f'{real_count}/{num_images} real' if real_count else 'all placeholder'
            self.stdout.write(
                f'  ✓ {seed["make"]} {seed["model"]} '
                f'({num_units} units, {img_source} images)'
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeded {created} vehicles successfully.'
        ))
