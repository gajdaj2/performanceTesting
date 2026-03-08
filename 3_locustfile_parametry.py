from locust import HttpUser, task

class ApiUser(HttpUser):
    def on_start(self):
        response = self.client.post("/login", json={
            "username": "test",
            "password": "test123",
        })
        response.raise_for_status()
        self.token = response.json()["token"]

    @task
    def get_profile(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/profile", headers=headers)

