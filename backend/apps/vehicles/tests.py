import os
import tempfile
from django.test import TestCase
from django.contrib.auth import get_user_model
from PIL import Image
from rest_framework.test import APIClient
from rest_framework import status
from apps.vehicles.models import Vehicle, VehicleImage

User = get_user_model()


def create_test_image(name='test.jpg'):
    """Create a simple test image file."""
    image = Image.new('RGB', (100, 100), color='blue')
    tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(tmp, format='JPEG')
    tmp.close()
    return tmp.name


class VehicleModelTests(TestCase):
    def test_create_vehicle(self):
        v = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='Sedan',
            transmission='automatic', fuel='gasoline', seats=5,
            price_per_day=2500.00, description='Compact sedan',
        )
        self.assertEqual(str(v), '2024 Toyota Vios (available)')
        self.assertEqual(v.status, 'available')

    def test_vehicle_defaults(self):
        v = Vehicle.objects.create(make='Honda', model='Civic', year=2024, price_per_day=3000.00)
        self.assertEqual(v.transmission, 'automatic')
        self.assertEqual(v.fuel, 'gasoline')
        self.assertEqual(v.seats, 5)


class VehicleAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@test.com', username='admin',
            password='AdminPass123!',
            is_verified=True,
        )
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='sedan',
            transmission='automatic', fuel='gasoline', seats=5,
            price_per_day=2500.00, status='available',
        )

    def _login_admin(self):
        resp = self.client.post('/api/auth/login/', {
            'email': 'admin@test.com', 'password': 'AdminPass123!',
        }, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_list_vehicles_public(self):
        response = self.client.get('/api/vehicles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_vehicles_excludes_maintenance_for_public(self):
        Vehicle.objects.create(make='Honda', model='Civic', year=2024, price_per_day=3000.00, status='unavailable')
        response = self.client.get('/api/vehicles/')
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_vehicle_public(self):
        response = self.client.get(f'/api/vehicles/{self.vehicle.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['make'], 'Toyota')

    def test_create_vehicle_admin_only(self):
        response = self.client.post('/api/vehicles/', {
            'make': 'Honda', 'model': 'Civic', 'year': 2024,
            'type': 'Sedan', 'price_per_day': 3000.00,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login_admin()
        response = self.client.post('/api/vehicles/', {
            'make': 'Honda', 'model': 'Civic', 'year': 2024,
            'type': 'sedan', 'price_per_day': 3000.00,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_vehicle_admin_only(self):
        self._login_admin()
        response = self.client.patch(f'/api/vehicles/{self.vehicle.pk}/', {
            'price_per_day': 2800.00,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['price_per_day'], '2800.00')

    def test_delete_vehicle_admin_only(self):
        response = self.client.delete(f'/api/vehicles/{self.vehicle.pk}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login_admin()
        response = self.client.delete(f'/api/vehicles/{self.vehicle.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_filter_by_type(self):
        Vehicle.objects.create(make='Honda', model='CR-V', year=2024, type='suv', price_per_day=4000.00)
        response = self.client.get('/api/vehicles/?type=suv')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['model'], 'CR-V')

    def test_search_vehicles(self):
        response = self.client.get('/api/vehicles/?search=Vios')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_ordering_by_price(self):
        Vehicle.objects.create(make='Honda', model='Civic', year=2024, price_per_day=3000.00)
        response = self.client.get('/api/vehicles/?ordering=price_per_day')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [r['price_per_day'] for r in response.data['results']]
        self.assertEqual(prices, ['2500.00', '3000.00'])


class VehicleImageAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@test.com', username='admin',
            password='AdminPass123!',
            is_verified=True,
        )
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='sedan',
            price_per_day=2500.00,
        )

    def _login_admin(self):
        resp = self.client.post('/api/auth/login/', {
            'email': 'admin@test.com', 'password': 'AdminPass123!',
        }, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_upload_image_admin(self):
        self._login_admin()
        img_path = create_test_image()
        try:
            with open(img_path, 'rb') as f:
                response = self.client.post(
                    f'/api/vehicles/{self.vehicle.pk}/images/',
                    {'image': f, 'is_primary': True},
                    format='multipart',
                )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data['is_primary'])
        finally:
            os.unlink(img_path)

    def test_list_images_public(self):
        # First upload as admin
        self._login_admin()
        img_path = create_test_image()
        try:
            with open(img_path, 'rb') as f:
                self.client.post(
                    f'/api/vehicles/{self.vehicle.pk}/images/',
                    {'image': f, 'is_primary': True},
                    format='multipart',
                )
        finally:
            os.unlink(img_path)

        # List as public (nested router doesn't paginate by default)
        client2 = APIClient()
        response = client2.get(f'/api/vehicles/{self.vehicle.pk}/images/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Nested router returns list directly (no .results wrapper)
        self.assertGreaterEqual(len(response.data), 1)

    def test_upload_image_public_fails(self):
        img_path = create_test_image()
        try:
            with open(img_path, 'rb') as f:
                response = self.client.post(
                    f'/api/vehicles/{self.vehicle.pk}/images/',
                    {'image': f},
                    format='multipart',
                )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        finally:
            os.unlink(img_path)
