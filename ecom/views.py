from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.http import HttpResponseRedirect,HttpResponse
from django.core.mail import send_mail
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.conf import settings

def home_view(request):
    # Fetch all products
    products = models.Product.objects.all()

    # Filter by category if a category is specified in the request
    category = request.GET.get('category')
    if category:
        products = products.filter(category=category)

    # Get distinct categories
    categories = models.Product.objects.values_list('category', flat=True).distinct()

    # Handle cart counter logic
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0

    # Redirect authenticated users
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')

    return render(request, 'ecom/index.html', {
        'products': products,
        'categories': categories,  # Pass categories to template
        'product_count_in_cart': product_count_in_cart,
        'selected_category': category,  # Optional: To highlight the selected category
    })


#for showing login button for admin
def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return HttpResponseRedirect('adminlogin')


def customer_signup_view(request):
    userForm=forms.CustomerUserForm()
    customerForm=forms.CustomerForm()
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST)
        customerForm=forms.CustomerForm(request.POST,request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customer=customerForm.save(commit=False)
            customer.user=user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
        return HttpResponseRedirect('customerlogin')
    return render(request,'ecom/customersignup.html',context=mydict)

#-----------for checking user iscustomer
def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()



#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,CUSTOMER
def afterlogin_view(request):
    if is_customer(request.user):
        return redirect('customer-home')
    else:
        return redirect('admin-dashboard')

#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    # for cards on dashboard
    customercount = models.Customer.objects.all().count()
    productcount = models.Product.objects.all().count()
    ordercount = models.Orders.objects.all().count()

    # for recent order tables
    orders = models.Orders.objects.all()
    order_data = []

    for order in orders:
        # Get the ordered products from the OrderItem model
        order_items = models.OrderItem.objects.filter(order=order)
        ordered_products = []
        for item in order_items:
            ordered_products.append({
                'product': item.product,
                'quantity': item.quantity
            })
        
        # Get the customer who placed the order
        customer = order.customer

        order_data.append({
            'order': order,
            'customer': customer,
            'ordered_products': ordered_products
        })

    mydict = {
        'customercount': customercount,
        'productcount': productcount,
        'ordercount': ordercount,
        'data': order_data,
    }
    
    return render(request, 'ecom/admin_dashboard.html', context=mydict)

# admin view customer table
@login_required(login_url='adminlogin')
def view_customer_view(request):
    customers=models.Customer.objects.all()
    return render(request,'ecom/view_customer.html',{'customers':customers})

# admin delete customer
@login_required(login_url='adminlogin')
def delete_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('view-customer')


@login_required(login_url='adminlogin')
def update_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return redirect('view-customer')
    return render(request,'ecom/admin_update_customer.html',context=mydict)

# admin view the product
@login_required(login_url='adminlogin')
def admin_products_view(request):
    products=models.Product.objects.all()
    return render(request,'ecom/admin_products.html',{'products':products})


# admin add product by clicking on floating button
@login_required(login_url='adminlogin')
def admin_add_product_view(request):
    productForm=forms.ProductForm()
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
        return HttpResponseRedirect('admin-products')
    return render(request,'ecom/admin_add_products.html',{'productForm':productForm})

import os

@login_required(login_url='adminlogin')
def delete_product_view(request, pk):
    try:
        # Get the product object
        product = models.Product.objects.get(id=pk)

        # Get the relative path from the model (this will be the part after 'static/')
        image_name = product.product_image.name  # This gives the relative path, e.g. 'product_image/download.jpg'

        # Construct the full path by joining MEDIA_ROOT and the image_name
        product_image_path = os.path.join(settings.MEDIA_ROOT, image_name)

        # Print the full path for debugging
        print(f"Attempting to delete image at: {product_image_path}")

        # Check if the image exists and delete it
        if os.path.exists(product_image_path):
            os.remove(product_image_path)
            print(f"Deleted image: {product_image_path}")
        else:
            print(f"Image file does not exist: {product_image_path}")

        # Delete the product
        product.delete()

        # Redirect to the product list page
        return redirect('admin-products')

    except models.Product.DoesNotExist:
        # Handle case when the product does not exist
        print(f"Product with id {pk} does not exist.")
        return redirect('admin-products')

    except Exception as e:
        # Catch any other exceptions and print them for debugging
        print(f"Error occurred: {e}")
        return redirect('admin-products')

@login_required(login_url='adminlogin')
def update_product_view(request, pk):
    product = models.Product.objects.get(id=pk)
    old_image_path = None

    # Store old image path before update
    if product.product_image:
        old_image_path = os.path.join(settings.MEDIA_ROOT, product.product_image.name)

    productForm = forms.ProductForm(instance=product)

    if request.method == 'POST':
        print("Form submitted!")  # Debugging line
        productForm = forms.ProductForm(request.POST, request.FILES, instance=product)

        if productForm.is_valid():
            print("Form is valid!")  # Debugging line

            # If a new image is uploaded, delete the old one
            if 'product_image' in request.FILES:
                if old_image_path and os.path.exists(old_image_path):
                    os.remove(old_image_path)
                    print(f"Deleted old image: {old_image_path}")  # Debugging line

            productForm.save()
            print("Product updated successfully!")  # Debugging line
            return redirect('admin-products')
        else:
            print("Form errors:", productForm.errors)  # Debugging line

    return render(request, 'ecom/admin_update_product.html', {'productForm': productForm})



from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from ecom.models import Product
import logging

# Logger for debugging
logger = logging.getLogger(__name__)

# View to trigger update for all products
@login_required(login_url='adminlogin')
def update_all_products(request):
    try:
        # Fetch products with 'category' or 'weather_tag' as NULL, empty, "nan", or "error"
        products_to_update = Product.objects.filter(
            category__in=[None, '', 'nan', 'error'],
            weather_tag__in=[None, '', 'nan', 'error']
        )
        
        updated_count = 0
        # Use transaction.atomic to ensure all updates happen together
        with transaction.atomic():
            for product in products_to_update:
                product.save()  # This will trigger the pre_save signal
                updated_count += 1
                logger.info(f"Product '{product.name}' updated successfully.")

        return HttpResponse(f"Updated {updated_count} products successfully!")

    except Exception as e:
        logger.error(f"Error occurred during update: {e}")
        return HttpResponse("Error occurred while updating products.")

@login_required(login_url='adminlogin')
def admin_view_booking_view(request):
    orders = models.Orders.objects.all()

    # Preparing order items related to each order
    order_data = []

    for order in orders:
        order_items = models.OrderItem.objects.filter(order=order)
        ordered_products = []

        # Loop through all order items and get the product details
        for item in order_items:
            ordered_products.append({
                'product_name': item.product.name,
                'product_image': item.product.product_image.url,
                'quantity': item.quantity,
                'product_id': item.product.id  # Add product ID
            })

        # Append the order along with its items to the order_data list
        order_data.append({
            'order': order,
            'ordered_products': ordered_products,
        })

    # Passing data to the template
    return render(request, 'ecom/admin_view_booking.html', {'data': order_data})


@login_required(login_url='adminlogin')
def delete_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    order.delete()
    return redirect('admin-view-booking')

# for changing status of order (pending,delivered...)
@login_required(login_url='adminlogin')
def update_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    orderForm=forms.OrderForm(instance=order)
    if request.method=='POST':
        orderForm=forms.OrderForm(request.POST,instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request,'ecom/update_order.html',{'orderForm':orderForm})


# admin view the feedback
@login_required(login_url='adminlogin')
def view_feedback_view(request):
    feedbacks=models.Feedback.objects.all().order_by('-id')
    return render(request,'ecom/view_feedback.html',{'feedbacks':feedbacks})



#---------------------------------------------------------------------------------
#------------------------ PUBLIC CUSTOMER RELATED VIEWS START ---------------------
#---------------------------------------------------------------------------------
def search_view(request):
    # whatever user write in search box we get in query
    query = request.GET['query']
    products=models.Product.objects.all().filter(name__icontains=query)
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # word variable will be shown in html when user click on search button
    word="Searched Result :"

    if request.user.is_authenticated:
        return render(request,'ecom/customer_home.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart})
    return render(request,'ecom/index.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart})




# any one can add product to cart, no need of signin
def add_to_cart_view(request, pk):
    # Fetch all products
    products = models.Product.objects.all()

    # Filter by category if a category is specified in the request
    category = request.GET.get('category')
    if category:
        products = products.filter(category=category)

    # Get distinct categories
    categories = models.Product.objects.values_list('category', flat=True).distinct()

    # For cart counter, fetching product IDs added by the customer from cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 1

    response = render(request, 'ecom/index.html', {
        'products': products,
        'categories': categories,  # Pass categories to the template
        'product_count_in_cart': product_count_in_cart,
        'selected_category': category,  # Optional: To highlight the selected category
    })

    # Adding product ID to cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids == "":
            product_ids = str(pk)
        else:
            product_ids = product_ids + "|" + str(pk)
        response.set_cookie('product_ids', product_ids)
    else:
        response.set_cookie('product_ids', pk)

    product = models.Product.objects.get(id=pk)
    messages.info(request, product.name + ' added to cart successfully!')

    return response


# for checkout of cart
def cart_view(request):
    #for cart counter
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # fetching product details from db whose id is present in cookie
    products=None
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            products=models.Product.objects.all().filter(id__in = product_id_in_cart)

            #for total price shown in cart
            for p in products:
                total=total+p.price
    return render(request,'ecom/cart.html',{'products':products,'total':total,'product_count_in_cart':product_count_in_cart})


def remove_from_cart_view(request,pk):
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # removing product id from cookie
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_id_in_cart=product_ids.split('|')
        product_id_in_cart=list(set(product_id_in_cart))
        product_id_in_cart.remove(str(pk))
        products=models.Product.objects.all().filter(id__in = product_id_in_cart)
        #for total price shown in cart after removing product
        for p in products:
            total=total+p.price

        #  for update coookie value after removing product id in cart
        value=""
        for i in range(len(product_id_in_cart)):
            if i==0:
                value=value+product_id_in_cart[0]
            else:
                value=value+"|"+product_id_in_cart[i]
        response = render(request, 'ecom/cart.html',{'products':products,'total':total,'product_count_in_cart':product_count_in_cart})
        if value=="":
            response.delete_cookie('product_ids')
        response.set_cookie('product_ids',value)
        return response



#---------------------------------------------------------------------------------
#------------------------ CUSTOMER RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
from django.views.decorators.cache import cache_control
from django.contrib.auth.decorators import login_required

 
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_home_view(request):
    # Fetch all products
    products = models.Product.objects.all()

    # Filter by category if a category is specified in the request
    category = request.GET.get('category')
    if category:
        products = products.filter(category=category)

    # Get distinct categories
    categories = models.Product.objects.values_list('category', flat=True).distinct()

    # Handle cart counter logic
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0

    return render(request, 'ecom/customer_home.html', {
        'products': products,
        'categories': categories,  # Pass categories to template
        'product_count_in_cart': product_count_in_cart,
        'selected_category': category,  # Optional: To highlight the selected category
    })
 
# shipment address before placing order
@login_required(login_url='customerlogin')
def customer_address_view(request):
    # this is for checking whether product is present in cart or not
    # if there is no product in cart we will not show address form
    product_in_cart=False
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_in_cart=True
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    addressForm = forms.AddressForm()
    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        if addressForm.is_valid():
            # here we are taking address, email, mobile at time of order placement
            # we are not taking it from customer account table because
            # these thing can be changes
            email = addressForm.cleaned_data['Email']
            mobile=addressForm.cleaned_data['Mobile']
            address = addressForm.cleaned_data['Address']
            #for showing total price on payment page.....accessing id from cookies then fetching  price of product from db
            total=0
            if 'product_ids' in request.COOKIES:
                product_ids = request.COOKIES['product_ids']
                if product_ids != "":
                    product_id_in_cart=product_ids.split('|')
                    products=models.Product.objects.all().filter(id__in = product_id_in_cart)
                    for p in products:
                        total=total+p.price

            response = render(request, 'ecom/payment.html',{'total':total})
            response.set_cookie('email',email)
            response.set_cookie('mobile',mobile)
            response.set_cookie('address',address)
            return response
    return render(request,'ecom/customer_address.html',{'addressForm':addressForm,'product_in_cart':product_in_cart,'product_count_in_cart':product_count_in_cart})


@login_required(login_url='customerlogin')
def location_page(request):

    return render(request, 'ecom/get_location.html')

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
# OpenWeather API Key
API_KEY = 'da7f01ad8490f329345846b4e3d5b45f'
@login_required(login_url='customerlogin')
@csrf_exempt
def get_weather(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lon = data.get('longitude')

            if lat and lon:
                url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric'
                response = requests.get(url)

                if response.status_code == 200:
                    weather_data = response.json()
                    weather_description = weather_data['weather'][0]['description'].lower()
                    temperature = weather_data['main']['temp']

                    # Determine the weather tag
                    if 'rain' in weather_description or 'drizzle' in weather_description or 'thunderstorm' in weather_description or 'tornado' in weather_description:
                        weather_tag = 'Rain'
                    elif 'snow' in weather_description or 'sleet' in weather_description or 'fog' in weather_description or 'mist' in weather_description or temperature <= 22:
                        weather_tag = 'Winter'
                    elif 'clear' in weather_description or 'few clouds' in weather_description or 'scattered clouds' in weather_description or 'hot' in weather_description or temperature > 25:
                        weather_tag = 'Summer'
                    else:
                        if temperature <= 22:
                            weather_tag = 'Winter'
                        else:
                            weather_tag = 'Summer'


                    # Fetch products based on the weather tag
                    products = Product.objects.filter(weather_tag=weather_tag).values('id', 'name', 'price', 'description', 'product_image')

                    return JsonResponse({
                        'city': weather_data.get('name', 'Unknown'),
                        'temperature': weather_data['main']['temp'],
                        'description': weather_data['weather'][0]['description'],
                        'humidity': weather_data['main']['humidity'],
                        'pressure': weather_data['main']['pressure'],
                        'products': list(products)  # Make sure 'id' is part of the returned data
                    })
                else:
                    return JsonResponse({'error': 'Failed to fetch weather data'}, status=400)

            return JsonResponse({'error': 'Invalid coordinates'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)




@login_required(login_url='customerlogin')
def manual_weather_page(request):
    weather_tag = ''
    products = []
    if request.method == 'POST':
        weather_description = request.POST.get('weather_description')
        temperature = float(request.POST.get('temperature', 0))

        if weather_description:
            # Determine weather tag based on description
            weather_description = weather_description.lower()
            if 'rain' in weather_description:
                weather_tag = 'Rain'
            elif 'snow' in weather_description or 'cold' in weather_description or temperature <= 22:
                weather_tag = 'Winter'
            elif 'clear' in weather_description or 'hot' in weather_description or temperature > 25:
                weather_tag = 'Summer'
            else:
                weather_tag = 'Summer' if temperature > 22 else 'Winter'
        
        elif temperature:
            if temperature <= 22:
                weather_tag = 'Winter'
            else:
                weather_tag = 'Summer'

        # Fetch products based on weather tag
        products = Product.objects.filter(weather_tag=weather_tag)

    return render(request, 'ecom/manual_weather_input.html', {
        'weather_tag': weather_tag,
        'products': products
    })



# here we are just directing to this view...actually we have to check whther payment is successful or not
#then only this view should be accessed
@login_required(login_url='customerlogin')
def payment_success_view(request):
    # Retrieve the customer object
    customer = models.Customer.objects.get(user_id=request.user.id)
    
    # Retrieve products from the cart (stored in cookies)
    products = None
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_list = product_ids.split('|')
            products = models.Product.objects.filter(id__in=product_id_list)
    
    # Retrieve shipping details from cookies
    email = request.COOKIES.get('email')
    mobile = request.COOKIES.get('mobile')
    address = request.COOKIES.get('address')
    
    # Create a single order
    order = models.Orders.objects.create(
        customer=customer,
        status='Pending',
        email=email,
        mobile=mobile,
        address=address
    )
    
    # Create an order item for each product in the cart
    if products:
        for product in products:
            # Here quantity is set to 1; adjust if you have quantity logic
            models.OrderItem.objects.create(order=order, product=product, quantity=1)
    
    # Clear cookies after order placement
    response = render(request, 'ecom/payment_success.html')
    response.delete_cookie('product_ids')
    response.delete_cookie('email')
    response.delete_cookie('mobile')
    response.delete_cookie('address')
    return response


from .models import Orders, OrderItem

def my_order_view(request):
    customer = request.user.customer  # Assuming the customer is linked to the user
    orders = Orders.objects.filter(customer=customer)  # Get the orders for the customer

    order_data = []
    for order in orders:
        order_items = OrderItem.objects.filter(order=order)
        # Get the first product's ID if available
        first_product_id = order_items.first().product.id if order_items.exists() else None
        order_data.append((order, order_items, first_product_id))

    return render(request, 'ecom/my_order.html', {'data': order_data})



#--------------for discharge patient bill (pdf) download and printing
import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = io.BytesIO()
    # Change encoding to UTF-8 instead of ISO-8859-1
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('Error generating PDF', content_type='text/plain')


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def download_invoice_view(request, orderID, productID):
    order = models.Orders.objects.get(id=orderID)
    order_items = models.OrderItem.objects.filter(order=order)  # Get all items for this order
    
    # Prepare product details and calculate total
    products = []
    total_price = 0  # Initialize total price
    for item in order_items:
        product = item.product
        products.append({
            'product_name': product.name,
            'product_image': product.product_image.url,
            'product_price': product.price * item.quantity,  # Total price for quantity
            'product_quantity': item.quantity,  # Add quantity here
        })
        total_price += product.price  # Add to total price

    # Prepare the context for rendering the PDF
    mydict = {
        'orderID': order.id,  # Pass the orderID to the template
        'orderDate': order.order_date,
        'customerName': request.user,
        'customerEmail': order.email,
        'customerMobile': order.mobile,
        'shipmentAddress': order.address,
        'orderStatus': order.status,
        'products': products,  # Pass the list of products
        'totalPrice': total_price,  # Pass the total price
    }
    return render_to_pdf('ecom/download_invoice.html', mydict)


 
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    return render(request,'ecom/my_profile.html',{'customer':customer})

 
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return HttpResponseRedirect('my-profile')
    return render(request,'ecom/edit_profile.html',context=mydict)


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def send_feedback_view(request):
    feedbackForm=forms.FeedbackForm()
    if request.method == 'POST':
        feedbackForm = forms.FeedbackForm(request.POST)
        if feedbackForm.is_valid():
            feedbackForm.save()
            return render(request, 'ecom/feedback_sent.html')
    return render(request, 'ecom/send_feedback.html', {'feedbackForm':feedbackForm})


#---------------------------------------------------------------------------------
#------------------------ ABOUT US AND CONTACT US VIEWS START --------------------
#---------------------------------------------------------------------------------
def aboutus_view(request):
    return render(request,'ecom/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email),message, settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = False)
            return render(request, 'ecom/contactussuccess.html')
    return render(request, 'ecom/contactus.html', {'form':sub})
