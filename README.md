# performanceTesting

Minimalna usluga FastAPI dla testu Locust (login + profil z bearer tokenem).

## Szybki start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Uruchom API

```bash
python app_fast.py
```

API startuje na `http://localhost:8000`.

### Uruchom test Locust

```bash
locust -f locustfile.py --host http://localhost:8000
```

Nastepnie otworz `http://localhost:8089` w przegladarce.

## Kontrakt API

- `POST /login` -> `{ "token": "..." }`
- `GET /profile` z naglowkiem `Authorization: Bearer <token>` -> `{ "username": "test" }`
- `GET /api/products` -> lista produktow (opcjonalnie `category`, `page`)
- `GET /api/products/{product_id}` -> szczegoly produktu
- `POST /api/cart/items` -> koszyk z suma
- `POST /api/orders` -> `order_id`, `status`, `total`
- `GET /api/users/{user_id}` -> profil uzytkownika
- `GET /api/search?q=...` -> lista produktow
- `GET /api/admin/dashboard` -> statystyki
- `GET /api/admin/orders` -> lista zamowien
- `PUT /api/admin/products/{product_id}` -> aktualizacja produktu

## Test e-commerce

```bash
locust -f locust_ecommerce.py --host http://localhost:8000
```

Nastepnie otworz `http://localhost:8089` w przegladarce.

## Testy Shoes API

```bash
locust -f locust_shoes.py --host http://localhost:8000
```

Nastepnie otworz `http://localhost:8089` w przegladarce.
