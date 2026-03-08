from locust import HttpUser, task, between
import random


class ShoesUser(HttpUser):
    """Symuluje zachowanie klienta sklepu z butami."""

    wait_time = between(1, 3)

    def on_start(self):
        self.username = f"user{random.randint(1, 100000)}"
        self.email = f"{self.username}@example.com"
        self.password = "test123"
        self.shoe_id = None
        self.token = None

        # Rejestracja i logowanie
        with self.client.post(
            "/api/auth/register",
            json={
                "username": self.username,
                "email": self.email,
                "password": self.password,
            },
            name="/api/auth/register",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"register failed: {response.status_code} - {response.text}")
                return

        with self.client.post(
            "/api/auth/login",
            json={
                "username": self.username,
                "password": self.password,
            },
            name="/api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login failed: {response.status_code} - {response.text}")
                return
            try:
                self.token = response.json().get("access_token")
            except ValueError:
                response.failure(f"login response not JSON: {response.text}")
                return
            if not self.token:
                response.failure("login response missing access_token")
                return

    def _auth_headers(self) -> dict:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def list_shoes(self):
        self.client.get(
            "/api/shoes",
            params={"skip": 0, "limit": 10},
            name="/api/shoes",
        )

    @task(3)
    def view_shoe(self):
        if self.shoe_id:
            self.client.get(
                f"/api/shoes/{self.shoe_id}",
                name="/api/shoes/[id]",
            )
        else:
            response = self.client.get(
                "/api/shoes",
                params={"skip": 0, "limit": 10},
                name="/api/shoes",
            )
            if response.status_code == 200:
                try:
                    shoes = response.json()
                    if shoes:
                        self.shoe_id = shoes[0]["id"]
                except ValueError:
                    pass

    @task(2)
    def create_shoe(self):
        if not self.token:
            return
        payload = {
            "name": f"Sneakers {random.randint(1, 100000)}",
            "brand": random.choice(["Nike", "Adidas", "Puma", "New Balance"]),
            "size": random.choice(["39", "40", "41", "42", "43"]),
            "color": random.choice(["Black", "White", "Red", "Blue"]),
            "price": round(random.uniform(199, 799), 2),
            "stock": random.randint(1, 20),
            "description": "Load test generated item",
        }
        response = self.client.post(
            "/api/shoes",
            json=payload,
            headers=self._auth_headers(),
            name="/api/shoes/create",
        )
        if response.status_code == 200:
            try:
                self.shoe_id = response.json().get("id")
            except ValueError:
                pass

    @task(2)
    def place_order(self):
        if not self.token:
            return
        if not self.shoe_id:
            return
        self.client.post(
            "/api/orders",
            json={"shoe_id": self.shoe_id, "quantity": random.randint(1, 2)},
            headers=self._auth_headers(),
            name="/api/orders",
        )

    @task(1)
    def get_my_orders(self):
        if not self.token:
            return
        self.client.get(
            "/api/orders",
            headers=self._auth_headers(),
            name="/api/orders/list",
        )

