from locust import HttpUser, task, between
import random


class EcommerceUser(HttpUser):
    """Simulates real user behavior for an e-commerce API."""

    wait_time = between(1, 3)

    def on_start(self):
        self.user_id = random.randint(1, 1000)
        self.product_id = None

    @task(5)
    def browse_products(self):
        category = random.choice(["electronics", "books", "clothing"])
        response = self.client.get(
            "/api/products",
            params={"category": category, "page": random.randint(1, 10)},
            name="/api/products",
        )

        if response.status_code == 200:
            try:
                products = response.json()
                if products:
                    self.product_id = products[0]["id"]
            except ValueError:
                pass

    @task(3)
    def view_product_details(self):
        if self.product_id:
            self.client.get(
                f"/api/products/{self.product_id}",
                name="/api/products/[id]",
            )

    @task(2)
    def add_to_cart(self):
        if self.product_id:
            self.client.post(
                "/api/cart/items",
                json={
                    "product_id": self.product_id,
                    "quantity": random.randint(1, 5),
                },
                name="/api/cart/items",
            )

    @task(1)
    def checkout(self):
        self.client.post(
            "/api/orders",
            json={
                "user_id": self.user_id,
                "payment_method": "credit_card",
            },
            name="/api/orders",
        )

    @task(2)
    def get_user_profile(self):
        self.client.get(
            f"/api/users/{self.user_id}",
            name="/api/users/[id]",
        )

    @task(1)
    def search_products(self):
        queries = ["laptop", "phone", "book", "shirt", "shoes"]
        self.client.get(
            "/api/search",
            params={"q": random.choice(queries)},
            name="/api/search",
        )


class AdminUser(HttpUser):
    """Simulates a lower volume admin user."""

    wait_time = between(3, 5)
    weight = 1

    @task
    def check_dashboard(self):
        self.client.get(
            "/api/admin/dashboard",
            name="/api/admin/dashboard",
        )

    @task
    def view_orders(self):
        self.client.get(
            "/api/admin/orders",
            params={"page": random.randint(1, 100)},
            name="/api/admin/orders",
        )

    @task
    def update_product(self):
        self.client.put(
            f"/api/admin/products/{random.randint(1, 500)}",
            json={
                "name": "Updated Product",
                "price": random.uniform(10, 1000),
            },
            name="/api/admin/products/[id]",
        )

