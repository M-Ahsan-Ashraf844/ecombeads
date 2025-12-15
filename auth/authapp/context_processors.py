from .models import category

def categories_context(request):
    return {
        'categories': category.objects.all()
    }
