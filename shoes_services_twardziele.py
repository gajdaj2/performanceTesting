"""
FastAPI serwis sprzedaży butów z autentykacją JWT Bearer
Prosty serwis - wszystko w pamięci, bez bazy danych!

Instalacja wymaganych pakietów:
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt]
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict

# ============================================================================
# KONFIGURACJA
# ============================================================================

SECRET_KEY = "super-secret-key-zmień-to-w-produkcji-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Kontekst haszowania haseł
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# FastAPI app
app = FastAPI(title="🥾 Shoes Shop API", version="1.0.0")

# Security
security = HTTPBearer()

# ============================================================================
# BAZA DANYCH W PAMIĘCI
# ============================================================================

# Liczniki ID
user_counter = 0
shoe_counter = 0
order_counter = 0

# Magazyny danych
users_db: Dict[int, dict] = {}  # {id: {username, email, hashed_password, created_at}}
shoes_db: Dict[int, dict] = {}  # {id: {name, brand, size, color, price, stock, description, created_at}}
orders_db: Dict[int, dict] = {}  # {id: {user_id, shoe_id, quantity, total_price, status, created_at}}


# ============================================================================
# MODELE PYDANTIC (Request/Response)
# ============================================================================

class UserRegister(BaseModel):
    """Rejestracja użytkownika"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Logowanie"""
    username: str
    password: str


class Token(BaseModel):
    """JWT Token"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Odpowiedź z danymi użytkownika"""
    id: int
    username: str
    email: str
    created_at: str


class ShoeCreate(BaseModel):
    """Tworzenie buta"""
    name: str = Field(..., min_length=3)
    brand: str
    size: str
    color: str
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    description: Optional[str] = None


class ShoeResponse(BaseModel):
    """Odpowiedź z danymi buta"""
    id: int
    name: str
    brand: str
    size: str
    color: str
    price: float
    stock: int
    description: Optional[str]
    created_at: str


class OrderCreate(BaseModel):
    """Zakup buta"""
    shoe_id: int
    quantity: int = Field(..., ge=1)


class OrderResponse(BaseModel):
    """Odpowiedź zamówienia"""
    id: int
    user_id: int
    shoe_id: int
    quantity: int
    total_price: float
    status: str
    created_at: str


# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def hash_password(password: str) -> str:
    """Haszowanie hasła"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Weryfikacja hasła"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tworzenie JWT tokenu"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency: Weryfikacja Bearer tokenu i pobranie aktualnego użytkownika"""
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Szukanie użytkownika po username
    user: Optional[dict] = None
    for user_id, user_data in users_db.items():
        if user_data["username"] == username:
            user = {"id": user_id, **user_data}
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


# ============================================================================
# ENDPOINTS - AUTENTYKACJA
# ============================================================================

@app.post("/api/auth/register", response_model=UserResponse, tags=["Auth"])
def register(user_data: UserRegister):
    """
    Rejestracja nowego użytkownika

    **Parametry:**
    - username: nazwa użytkownika (3-50 znaków)
    - email: email użytkownika
    - password: hasło (min 6 znaków)
    """
    global user_counter

    # Sprawdzenie czy użytkownik już istnieje
    for user in users_db.values():
        if user["username"] == user_data.username or user["email"] == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )

    # Tworzenie nowego użytkownika
    user_counter += 1
    new_user = {
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hash_password(user_data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    users_db[user_counter] = new_user

    return {
        "id": user_counter,
        "username": new_user["username"],
        "email": new_user["email"],
        "created_at": new_user["created_at"]
    }


@app.post("/api/auth/login", response_model=Token, tags=["Auth"])
def login(user_data: UserLogin):
    """
    Logowanie i uzyskanie JWT tokenu

    **Parametry:**
    - username: nazwa użytkownika
    - password: hasło

    **Zwraca Bearer token do autoryzacji**
    """
    # Szukanie użytkownika
    user = None
    for user_data_stored in users_db.values():
        if user_data_stored["username"] == user_data.username:
            user = user_data_stored
            break

    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UserResponse, tags=["Auth"])
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Pobranie informacji o zalogowanym użytkowniku

    **Wymagane:** Bearer token w header'ze `Authorization: Bearer <token>`
    """
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "created_at": current_user["created_at"]
    }


# ============================================================================
# ENDPOINTS - BUTY (PRODUCTS)
# ============================================================================

@app.get("/api/shoes", response_model=List[ShoeResponse], tags=["Shoes"])
def get_all_shoes(
        brand: Optional[str] = None,
        size: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
):
    """
    Pobranie listy butów

    **Parametry (opcjonalne):**
    - brand: filtruj po marce (Nike, Adidas, itp.)
    - size: filtruj po rozmiarze (35, 36, 37...)
    - skip: ile butów pominąć (dla paginacji)
    - limit: ile butów zwrócić
    """
    shoes_list = []

    for shoe_id, shoe_data in shoes_db.items():
        # Filtrowanie po marce
        if brand and brand.lower() not in shoe_data["brand"].lower():
            continue

        # Filtrowanie po rozmiarze
        if size and shoe_data["size"] != size:
            continue

        shoes_list.append({
            "id": shoe_id,
            **shoe_data
        })

    # Paginacja
    return shoes_list[skip:skip + limit]


@app.get("/api/shoes/{shoe_id}", response_model=ShoeResponse, tags=["Shoes"])
def get_shoe(shoe_id: int):
    """
    Pobranie informacji o konkretnym bucie
    """
    if shoe_id not in shoes_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shoe not found"
        )

    return {
        "id": shoe_id,
        **shoes_db[shoe_id]
    }


@app.post("/api/shoes", response_model=ShoeResponse, tags=["Shoes"])
def create_shoe(
        shoe_data: ShoeCreate,
        current_user: dict = Depends(get_current_user)
):
    """
    Dodanie nowego buta do sklepu (wymagane logowanie)

    **Wymagane:** Bearer token
    """
    global shoe_counter

    shoe_counter += 1
    new_shoe = {
        "name": shoe_data.name,
        "brand": shoe_data.brand,
        "size": shoe_data.size,
        "color": shoe_data.color,
        "price": shoe_data.price,
        "stock": shoe_data.stock,
        "description": shoe_data.description,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    shoes_db[shoe_counter] = new_shoe

    return {
        "id": shoe_counter,
        **new_shoe
    }


@app.put("/api/shoes/{shoe_id}", response_model=ShoeResponse, tags=["Shoes"])
def update_shoe(
        shoe_id: int,
        shoe_data: ShoeCreate,
        current_user: dict = Depends(get_current_user)
):
    """
    Aktualizacja informacji o bucie (wymagane logowanie)
    """
    if shoe_id not in shoes_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shoe not found"
        )

    updated_shoe = {
        "name": shoe_data.name,
        "brand": shoe_data.brand,
        "size": shoe_data.size,
        "color": shoe_data.color,
        "price": shoe_data.price,
        "stock": shoe_data.stock,
        "description": shoe_data.description,
        "created_at": shoes_db[shoe_id]["created_at"]
    }
    shoes_db[shoe_id] = updated_shoe

    return {
        "id": shoe_id,
        **updated_shoe
    }


@app.delete("/api/shoes/{shoe_id}", tags=["Shoes"])
def delete_shoe(
        shoe_id: int,
        current_user: dict = Depends(get_current_user)
):
    """
    Usunięcie buta ze sklepu (wymagane logowanie)
    """
    if shoe_id not in shoes_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shoe not found"
        )

    del shoes_db[shoe_id]
    return {"message": "Shoe deleted successfully"}


# ============================================================================
# ENDPOINTS - ZAMÓWIENIA (ORDERS)
# ============================================================================

@app.post("/api/orders", response_model=OrderResponse, tags=["Orders"])
def create_order(
        order_data: OrderCreate,
        current_user: dict = Depends(get_current_user)
):
    """
    Złożenie nowego zamówienia (wymaga zalogowania)

    **Wymagane:** Bearer token

    **Parametry:**
    - shoe_id: ID buta
    - quantity: ilość sztuk
    """
    global order_counter

    if order_data.shoe_id not in shoes_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shoe not found"
        )

    shoe = shoes_db[order_data.shoe_id]

    if shoe["stock"] < order_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough stock. Available: {shoe['stock']}"
        )

    total_price = shoe["price"] * order_data.quantity

    order_counter += 1
    new_order = {
        "user_id": current_user["id"],
        "shoe_id": order_data.shoe_id,
        "quantity": order_data.quantity,
        "total_price": total_price,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    orders_db[order_counter] = new_order

    # Zmniejszenie zapasu
    shoe["stock"] -= order_data.quantity

    return {
        "id": order_counter,
        **new_order
    }


@app.get("/api/orders", response_model=List[OrderResponse], tags=["Orders"])
def get_my_orders(current_user: dict = Depends(get_current_user)):
    """
    Pobranie historii zamówień zalogowanego użytkownika

    **Wymagane:** Bearer token
    """
    my_orders = []

    for order_id, order_data in orders_db.items():
        if order_data["user_id"] == current_user["id"]:
            my_orders.append({
                "id": order_id,
                **order_data
            })

    return my_orders


@app.get("/api/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(
        order_id: int,
        current_user: dict = Depends(get_current_user)
):
    """
    Pobranie szczegółów konkretnego zamówienia
    """
    if order_id not in orders_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    order = orders_db[order_id]

    if order["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this order"
        )

    return {
        "id": order_id,
        **order
    }


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["Info"])
def root():
    """API główny endpoint"""
    return {
        "message": "🥾 Welcome to Shoes Shop API",
        "docs": "/docs",
        "api_version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth/*",
            "shoes": "/api/shoes/*",
            "orders": "/api/orders/*"
        }
    }


# ============================================================================
# SEED - PRZYKŁADOWE DANE
# ============================================================================

@app.post("/api/seed", tags=["Admin"])
def seed_database():
    """
    Dodaj przykładowe buty do bazy danych
    """
    global shoe_counter

    if len(shoes_db) > 0:
        return {"message": "Database already seeded"}

    sample_shoes = [
        {
            "name": "Nike Air Max 90",
            "brand": "Nike",
            "size": "42",
            "color": "White",
            "price": 499.99,
            "stock": 10,
            "description": "Classic Nike running shoe with Air Max cushioning"
        },
        {
            "name": "Adidas Ultraboost 21",
            "brand": "Adidas",
            "size": "41",
            "color": "Black",
            "price": 599.99,
            "stock": 8,
            "description": "Premium running shoe with Boost technology"
        },
        {
            "name": "Jordan 1 Retro",
            "brand": "Jordan",
            "size": "43",
            "color": "Red",
            "price": 799.99,
            "stock": 5,
            "description": "Iconic basketball shoe"
        },
        {
            "name": "New Balance 990v5",
            "brand": "New Balance",
            "size": "40",
            "color": "Gray",
            "price": 449.99,
            "stock": 12,
            "description": "Premium lifestyle and running shoe"
        },
        {
            "name": "Puma RS-X",
            "brand": "Puma",
            "size": "39",
            "color": "Blue",
            "price": 349.99,
            "stock": 15,
            "description": "Retro inspired lifestyle shoe"
        },
    ]

    for shoe in sample_shoes:
        shoe_counter += 1
        shoes_db[shoe_counter] = {
            **shoe,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    return {
        "message": "Database seeded successfully",
        "shoes_added": len(sample_shoes)
    }


if __name__ == "__main__":
    import uvicorn

    print("🥾 Starting Shoes Shop API...")
    print("📚 Docs available at: http://localhost:8000/docs")
    print("🔑 First, register and login to get Bearer token!")

    uvicorn.run(app, host="0.0.0.0", port=8000)
