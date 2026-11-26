
from .cart import Cart 

def cart_processor(request): 
    cart = Cart(request)
    
    return {
        'current_cart_object': cart, 
        'current_cart_total_quantity': cart.get_total_quantity() 
        }