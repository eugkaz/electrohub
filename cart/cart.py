from django.conf import settings
from product.models import Product
from decimal import Decimal
from django.shortcuts import get_object_or_404

class Cart(object):
    def __init__(self, request):
        self.session = request.session
        cart_data_from_session = self.session.get(settings.CART_SESSION_ID)
        if not cart_data_from_session:
            cart_data_from_session = self.session[settings.CART_SESSION_ID] = {}
        for key, item_data in cart_data_from_session.items():
            if 'price' in item_data and isinstance(item_data['price'], Decimal):
                 cart_data_from_session[key]['price'] = str(item_data['price'])
        self.cart = cart_data_from_session

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def add(self, product_id, quantity=1, update_quantity=False):
        product_id_str = str(product_id)
        quantity = int(quantity)
        if product_id_str not in self.cart:
            try:
                product = Product.objects.get(id=product_id_str, in_stock=True)
                self.cart[product_id_str] = {'quantity': 0, 'price': str(product.price)}
            except Product.DoesNotExist:
                return 
        current_quantity = self.cart[product_id_str]['quantity']
        if update_quantity:
            if quantity < 0: 
                new_quantity = current_quantity + quantity 
            else: 
                new_quantity = quantity
        else:
            new_quantity = current_quantity + quantity
        if new_quantity <= 0:
            self.remove(product_id_str)
        else:
            self.cart[product_id_str]['quantity'] = new_quantity
            self.save()

    def remove(self, product_id):
        product_id_str = str(product_id)
        if product_id_str in self.cart:
            del self.cart[product_id_str]
            self.save()

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
            self.save()

    def get_total_cost(self) -> Decimal:
        total = Decimal('0.00')
        for item_data in self.cart.values():
            try:
                price_decimal = Decimal(item_data['price'])
                total += price_decimal * item_data['quantity']
            except Exception as e:
                print(f"Помилка конвертації ціни або розрахунку суми для товару: {item_data}, помилка: {e}")
        return total

    def get_item(self, product_id):
        product_id_str = str(product_id)
        item_data = self.cart.get(product_id_str)
        return item_data.copy() if item_data else None

    def __iter__(self):
        product_ids_in_cart = list(self.cart.keys())
        if not product_ids_in_cart: return
        products_from_db = Product.objects.filter(id__in=product_ids_in_cart)
        products_map = {str(p.id): p for p in products_from_db}
        cart_items_to_iterate = self.cart.copy()
        for product_id_str, item_data_from_session in cart_items_to_iterate.items():
            product_object = products_map.get(product_id_str)
            if product_object:
                try:
                    price_as_decimal = Decimal(item_data_from_session['price'])
                    yield {
                        'product': product_object,
                        'quantity': item_data_from_session['quantity'],
                        'price': price_as_decimal, 
                        'total_price': item_data_from_session['quantity'] * price_as_decimal
                    }
                except Exception as e:
                    print(f"Помилка при підготовці товару {product_id_str} для ітерації: {e}")
            else:
                print(f"ПОПЕРЕДЖЕННЯ: Товар з ID {product_id_str} з кошика не знайдено в базі даних. Пропускається при ітерації.")
                
    def __len__(self) -> int:
        return sum(item_data['quantity'] for item_data in self.cart.values())

    def get_total_quantity(self) -> int:
        return len(self)

    def get_product_ids(self) -> list:
        return list(self.cart.keys())

    def __bool__(self) -> bool:
        return bool(self.cart)