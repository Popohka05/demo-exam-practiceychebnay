from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from functools import wraps

from .forms import SimplifiedUserCreationForm
from .models import Order, PickupPoint, Product, Profile


def get_user_role(user):
    if not user.is_authenticated:
        return 'unauthorized'
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user, role='authorized')
        return profile.role


def require_role(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = get_user_role(request.user)
            if user_role not in allowed_roles:
                return HttpResponseForbidden("нет доступа")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def apply_product_filters(products, request):
    query = request.GET.get('search', '').strip()
    price_min = request.GET.get('price_min', '').strip()
    price_max = request.GET.get('price_max', '').strip()

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query)
        )

    if price_min:
        try:
            products = products.filter(price__gte=float(price_min))
        except ValueError:
            pass

    if price_max:
        try:
            products = products.filter(price__lte=float(price_max))
        except ValueError:
            pass

    return products


def build_product_list_context(products, user_role):
    is_admin = user_role == 'admin'
    can_edit = user_role in ['editor', 'admin']
    return {
        'products': products,
        'user_role': user_role,
        'show_edit': can_edit,
        'show_delete': is_admin,
        'show_add_product': is_admin,
    }


def product_list(request):
    user_role = get_user_role(request.user)
    products = Product.objects.select_related().all()

    if user_role in ['authorized', 'editor', 'admin']:
        products = apply_product_filters(products, request)

    context = build_product_list_context(products, user_role)
    return render(request, 'products.html', context)


def register_view(request):
    if request.method == 'POST':
        form = SimplifiedUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                Profile.objects.get_or_create(
                    user=user,
                    defaults={'role': 'authorized'}
                )
                login(request, user)
                return redirect('product_list')
            except Exception as e:
                form.add_error(None, f"Ошибка {str(e)}")
    else:
        form = SimplifiedUserCreationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            error = 'Введите логин и пароль'
            return render(request, 'login.html', {'error': error})

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('product_list')
        else:
            error = 'Неверный логин или пароль'
            return render(request, 'login.html', {'error': error})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('product_list')


@login_required(login_url='login')
@require_role(['authorized', 'editor', 'admin'])
def order_list(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'order_list.html', {'orders': orders})


@login_required(login_url='login')
@require_role(['authorized'])
def create_order(request, product_id, pickup_point_id):
    product = get_object_or_404(Product, id=product_id)
    pickup_point = get_object_or_404(PickupPoint, id=pickup_point_id)
    order = Order.objects.create(user=request.user, pickupPoint=pickup_point)
    order.products.add(product)
    return redirect('order_list')


@login_required(login_url='login')
@require_role(['editor', 'admin'])
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.name = request.POST.get('name', product.name)
        product.price = request.POST.get('price', product.price)
        product.description = request.POST.get('description', product.description)
        product.sku = request.POST.get('sku', product.sku)
        product.save()
        return redirect('product_list')

    return render(request, 'edit_product.html', {'product': product})


@login_required(login_url='login')
@require_role(['admin'])
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')

    return render(request, 'confirm_delete.html', {'object': product, 'object_type': 'товара'})


@login_required(login_url='login')
@require_role(['admin'])
def add_product(request):
    if request.method == 'POST':
        Product.objects.create(
            name=request.POST.get('name', ''),
            price=request.POST.get('price', 0),
            description=request.POST.get('description', ''),
            sku=request.POST.get('sku', '')
        )
        return redirect('product_list')

    return render(request, 'add_product.html')

@login_required(login_url='login')
@require_role(['admin'])
def manage_users(request):
    """Admin view to manage all users"""
    users = User.objects.select_related('profile').all()
    context = {
        'users': users,
        'user_role': get_user_role(request.user)
    }
    return render(request, 'manage_users.html', context)
