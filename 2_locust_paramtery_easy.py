from locust import HttpUser, task, constant


class ApiUser(HttpUser):
    wait_time = constant(3)
    host = "https://localhost:8000"

    def on_start(self):
        # Logowanie
        response = self.client.post("/login", json={
        "username": "test",
        "password": "test123"
        })
        self.token = response.json()["token"]


    @task
    def get_profile(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/profile", headers=headers)