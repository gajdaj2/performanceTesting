from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import secrets
from typing import Optional
import uvicorn

app = FastAPI()

USERS = {"test": "test123"}
TOKENS: dict[str, str] = {}

PRODUCTS = [
    {"id": 1, "name": "Laptop Pro", "category": "electronics", "price": 1299.0},
    {"id": 2, "name": "Smartphone X", "category": "electronics", "price": 899.0},
    {"id": 3, "name": "Noise Cancelling Headphones", "category": "electronics", "price": 199.0},
    {"id": 4, "name": "E-Reader", "category": "electronics", "price": 129.0},
    {"id": 5, "name": "Python Basics", "category": "books", "price": 39.0},
    {"id": 6, "name": "Data Science 101", "category": "books", "price": 49.0},
    {"id": 7, "name": "Clean Architecture", "category": "books", "price": 59.0},
    {"id": 8, "name": "Sci-Fi Novel", "category": "books", "price": 24.0},
    {"id": 9, "name": "Classic T-Shirt", "category": "clothing", "price": 19.0},
    {"id": 10, "name": "Hoodie", "category": "clothing", "price": 49.0},
    {"id": 11, "name": "Jeans", "category": "clothing", "price": 59.0},
    {"id": 12, "name": "Sneakers", "category": "clothing", "price": 89.0},
    {"id": 13, "name": "Tablet", "category": "electronics", "price": 499.0},
    {"id": 14, "name": "Notebook", "category": "books", "price": 12.0},
    {"id": 15, "name": "Jacket", "category": "clothing", "price": 99.0},
]

CART_ITEMS: list[dict] = []
ORDERS: list[dict] = []

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str

class ProfileResponse(BaseModel):
    username: str

class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    price: float

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int

class CartItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    line_total: float

class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total: float

class OrderCreate(BaseModel):
    user_id: int
    payment_method: str

class OrderResponse(BaseModel):
    order_id: int
    user_id: int
    status: str
    total: float

class UserProfile(BaseModel):
    user_id: int
    name: str
    email: str
    tier: str

class AdminDashboard(BaseModel):
    products: int
    users: int
    orders: int
    revenue: float

class AdminOrdersResponse(BaseModel):
    page: int
    page_size: int
    total: int
    orders: list[OrderResponse]

@app.get("/home")
async def home():
    return {"message": "Hello World"}


@app.get("/")
async def home():
    return {"message": "Hello World"}


@app.get("/world")
async def world():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"message": "Hello World"}

@app.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    if USERS.get(payload.username) != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    TOKENS[token] = payload.username
    return {"token": token}


def _get_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()

@app.get("/profile", response_model=ProfileResponse)
async def profile(authorization: Optional[str] = Header(default=None, alias="Authorization")):
    token = _get_bearer_token(authorization)
    username = TOKENS.get(token) if token else None
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"username": username}


def _paginate(items: list[dict], page: int, page_size: int = 10) -> list[dict]:
    if page < 1:
        page = 1
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


def _find_product(product_id: int) -> Optional[dict]:
    for product in PRODUCTS:
        if product["id"] == product_id:
            return product
    return None


def _cart_summary() -> CartResponse:
    items: list[CartItemResponse] = []
    total = 0.0
    for item in CART_ITEMS:
        items.append(CartItemResponse(**item))
        total += item["line_total"]
    return CartResponse(items=items, total=round(total, 2))


@app.get("/api/products", response_model=list[ProductResponse])
async def list_products(category: Optional[str] = None, page: int = 1):
    filtered = PRODUCTS
    if category:
        filtered = [p for p in PRODUCTS if p["category"] == category]
    return _paginate(filtered, page)


@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/api/cart/items", response_model=CartResponse)
async def add_to_cart(payload: CartItemCreate):
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    product = _find_product(payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    unit_price = float(product["price"])
    line_total = round(unit_price * payload.quantity, 2)
    CART_ITEMS.append({
        "product_id": payload.product_id,
        "quantity": payload.quantity,
        "unit_price": unit_price,
        "line_total": line_total,
    })
    return _cart_summary()


@app.post("/api/orders", response_model=OrderResponse)
async def create_order(payload: OrderCreate):
    total = sum(item["line_total"] for item in CART_ITEMS)
    order_id = len(ORDERS) + 1
    order = {
        "order_id": order_id,
        "user_id": payload.user_id,
        "status": "paid",
        "total": round(total, 2),
    }
    ORDERS.append(order)
    CART_ITEMS.clear()
    return order


@app.get("/api/users/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: int):
    tier = "vip" if user_id % 10 == 0 else "standard"
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "tier": tier,
    }


@app.get("/api/search", response_model=list[ProductResponse])
async def search_products(q: Optional[str] = None):
    if not q:
        return []
    query = q.lower()
    results = [p for p in PRODUCTS if query in p["name"].lower()]
    return results[:10]


@app.get("/api/admin/dashboard", response_model=AdminDashboard)
async def admin_dashboard():
    revenue = sum(order["total"] for order in ORDERS)
    return {
        "products": len(PRODUCTS),
        "users": 1000,
        "orders": len(ORDERS),
        "revenue": round(revenue, 2),
    }


@app.get("/api/admin/orders", response_model=AdminOrdersResponse)
async def admin_orders(page: int = 1, page_size: int = 10):
    items = _paginate(ORDERS, page, page_size)
    return {
        "page": page,
        "page_size": page_size,
        "total": len(ORDERS),
        "orders": items,
    }


@app.put("/api/admin/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, payload: ProductUpdate):
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.name is not None:
        product["name"] = payload.name
    if payload.price is not None:
        product["price"] = float(payload.price)
    return product

if __name__ == "__main__":

    uvicorn.run(app, host="localhost", port=8000)