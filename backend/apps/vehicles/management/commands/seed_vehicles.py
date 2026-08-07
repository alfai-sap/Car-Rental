import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import io
from apps.vehicles.models import Vehicle, VehicleImage, VehicleUnit


VEHICLE_SEEDS = [
    {'make': 'Toyota', 'model': 'Vios', 'year': 2024, 'type': 'Sedan', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 2500, 'description': 'Fuel-efficient compact sedan. Perfect for city driving and daily commutes. Features Apple CarPlay, reverse camera, and excellent air conditioning.'},
    {'make': 'Toyota', 'model': 'Innova', 'year': 2024, 'type': 'MPV', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 4000, 'description': 'Spacious family MPV with powerful diesel engine. Ideal for out-of-town trips and large groups. Comfortable ride with ample cargo space.'},
    {'make': 'Toyota', 'model': 'Fortuner', 'year': 2023, 'type': 'SUV', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 5500, 'description': 'Premium mid-size SUV with commanding road presence. 4x4 capability, leather seats, and advanced safety features. Perfect for both city and provincial roads.'},
    {'make': 'Honda', 'model': 'Civic', 'year': 2024, 'type': 'Sedan', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 3500, 'description': 'Sporty and sophisticated sedan with turbocharged engine. Honda SENSING safety suite, premium audio, and responsive handling.'},
    {'make': 'Honda', 'model': 'CR-V', 'year': 2024, 'type': 'SUV', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 4500, 'description': 'Refined compact SUV with spacious interior. Panoramic sunroof, wireless charging, and Honda LaneWatch camera.'},
    {'make': 'Mitsubishi', 'model': 'Xpander', 'year': 2023, 'type': 'MPV', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 3000, 'description': 'Versatile 7-seater with SUV-like styling. Great ground clearance, flexible seating configurations, and excellent value for families.'},
    {'make': 'Mitsubishi', 'model': 'Montero Sport', 'year': 2024, 'type': 'SUV', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 5000, 'description': 'Rugged yet refined SUV with legendary reliability. 4x4 drivetrain, touchscreen infotainment, and premium interior finishes.'},
    {'make': 'Nissan', 'model': 'Terra', 'year': 2024, 'type': 'SUV', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 7, 'price_per_day': 4800, 'description': 'Bold full-size SUV with intelligent 4x4. 360-degree camera, dual-zone climate control, and Nissan Intelligent Mobility features.'},
    {'make': 'Ford', 'model': 'Ranger', 'year': 2024, 'type': 'Pickup', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 5, 'price_per_day': 5000, 'description': 'Tough and capable pickup truck. Best-in-class towing capacity, SYNC 4 infotainment, and off-road ready with Terrain Management System.'},
    {'make': 'Hyundai', 'model': 'Stargazer', 'year': 2024, 'type': 'MPV', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 2800, 'description': 'Modern family MPV with futuristic styling. SmartSense safety suite, wireless Apple CarPlay, and flexible seating for up to 7 passengers.'},
    {'make': 'Suzuki', 'model': 'Ertiga', 'year': 2023, 'type': 'MPV', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 2200, 'description': 'Affordable and practical 7-seater. Excellent fuel economy, compact dimensions for easy city parking, and surprisingly spacious third row.'},
    {'make': 'Toyota', 'model': 'HiAce', 'year': 2024, 'type': 'Van', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 14, 'price_per_day': 7000, 'description': 'Spacious commuter van for large groups. Perfect for family reunions, corporate shuttles, and tour groups. Powerful and reliable diesel engine.'},
    {'make': 'Mazda', 'model': 'CX-5', 'year': 2024, 'type': 'SUV', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 4200, 'description': 'Premium compact SUV with stunning KODO design. SKYACTIV technology, Bose sound system, and driver-focused cockpit with Nappa leather.'},
    {'make': 'Toyota', 'model': 'Avanza', 'year': 2024, 'type': 'MPV', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 7, 'price_per_day': 2500, 'description': 'Compact and efficient 7-seater. Perfect for young families and small businesses. Modern features in an affordable package.'},
    {'make': 'Isuzu', 'model': 'D-MAX', 'year': 2024, 'type': 'Pickup', 'transmission': 'automatic', 'fuel': 'diesel', 'seats': 5, 'price_per_day': 4800, 'description': 'Legendary durability in a modern pickup. Best-in-class fuel efficiency with Blue Power diesel, advanced safety features, and proven reliability.'},
    {'make': 'Honda', 'model': 'City', 'year': 2024, 'type': 'Sedan', 'transmission': 'automatic', 'fuel': 'gasoline', 'seats': 5, 'price_per_day': 2800, 'description': 'Stylish subcompact sedan with class-leading space. Honda SENSING, ultra-low fuel consumption, and refined ride quality for daily driving.'},
    {'make': 'BYD', 'model': 'Atto 3', 'year': 2024, 'type': 'SUV', 'transmission': 'automatic', 'fuel': 'electric', 'seats': 5, 'price_per_day': 4000, 'description': 'All-electric compact SUV with impressive range. Blade Battery technology, rotating touchscreen, and near-silent driving experience. Zero emissions.'},
    {'make': 'Toyota', 'model': 'Corolla Cross', 'year': 2024, 'type': 'SUV', 'transmission': 'automatic', 'fuel': 'hybrid', 'seats': 5, 'price_per_day': 3800, 'description': 'Hybrid compact SUV combining efficiency and versatility. Toyota Safety Sense, excellent fuel economy, and smooth hybrid powertrain.'},
]


COLORS = [
    (52, 73, 94),    # Dark blue-gray
    (44, 62, 80),    # Dark navy
    (127, 140, 141), # Gray
    (52, 152, 219),  # Blue
    (41, 128, 185),  # Dark blue
    (231, 76, 60),   # Red
    (192, 57, 43),   # Dark red
    (39, 174, 96),   # Green
    (46, 204, 113),  # Light green
    (243, 156, 18),  # Orange
    (155, 89, 182),  # Purple
    (22, 160, 133),  # Teal
    (211, 84, 0),    # Burnt orange
]


def generate_vehicle_image(make, model, color=None):
    """Generate a simple placeholder image for a vehicle with text overlay."""
    if color is None:
        color = random.choice(COLORS)

    width, height = 800, 500
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)

    # Draw a simple car silhouette
    # Body
    body_color = tuple(max(0, c - 40) for c in color)
    draw.rectangle([150, 280, 650, 420], fill=body_color)
    draw.rectangle([250, 200, 550, 280], fill=body_color)
    # Windows
    draw.rectangle([270, 215, 380, 270], fill=(230, 240, 245))
    draw.rectangle([400, 215, 520, 270], fill=(230, 240, 245))
    # Wheels
    draw.ellipse([200, 380, 260, 440], fill=(30, 30, 30))
    draw.ellipse([540, 380, 600, 440], fill=(30, 30, 30))
    # Headlights
    draw.rectangle([620, 300, 645, 340], fill=(255, 255, 200))
    # Road
    draw.rectangle([0, 440, 800, 500], fill=(60, 60, 60))
    draw.rectangle([50, 468, 150, 472], fill=(255, 255, 255))
    draw.rectangle([200, 468, 300, 472], fill=(255, 255, 255))
    draw.rectangle([350, 468, 450, 472], fill=(255, 255, 255))
    draw.rectangle([500, 468, 600, 472], fill=(255, 255, 255))
    draw.rectangle([650, 468, 750, 472], fill=(255, 255, 255))

    # Text
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 20)
    except (IOError, OSError):
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    text = f"{make} {model}"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, 80), text, fill=(255, 255, 255), font=font_large)

    subtitle = random.choice([
        'Available for Rent', 'Low Mileage', 'Well Maintained',
        'Ready to Go', 'Book Now', 'Premium Condition',
    ])
    bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    sub_width = bbox[2] - bbox[0]
    draw.text(((width - sub_width) // 2, 130), subtitle, fill=(200, 210, 220), font=font_small)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = 'Seed the database with sample vehicles and generated images.'

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
            # Generate 2-3 images per vehicle
            num_images = random.randint(2, 3)
            for i in range(num_images):
                color = random.choice(COLORS)
                image_file = generate_vehicle_image(seed['make'], seed['model'], color)
                VehicleImage.objects.create(
                    vehicle=vehicle,
                    image=ContentFile(
                        image_file.read(),
                        name=f'{seed["make"].lower()}_{seed["model"].lower()}_{i+1}.jpg'
                    ),
                    is_primary=(i == 0),
                )
            # Create 1-3 VehicleUnits per vehicle with unique plate numbers
            num_units = random.randint(1, 3)
            for u in range(num_units):
                plate = f"{seed['make'][:3].upper()}-{created:03d}-{u+1}"
                VehicleUnit.objects.create(
                    vehicle=vehicle,
                    plate_number=plate,
                    status='available',
                    mileage=random.randint(1000, 50000),
                )
            created += 1
            self.stdout.write(f'  ✓ {seed["make"]} {seed["model"]} ({num_units} units)')

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeded {created} vehicles with images successfully.'
        ))
