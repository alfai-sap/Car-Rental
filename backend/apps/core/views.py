from inertia import render


def home(request):
    """Home page — displays available vehicles."""
    return render(request, 'Home', {
        'message': 'Welcome to Car Rental',
    })


def about(request):
    """About page."""
    return render(request, 'About', {
        'title': 'About Us',
    })
