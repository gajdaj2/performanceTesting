from locust import HttpUser, task, constant


class ApiUser(HttpUser):
    wait_time = constant(3)
    host = "http://localhost:8000"

    def on_start(self):
        # Logowanie
        response = self.client.post("/login", json={
            "username": "test",
            "password": "test123"
        })
        if response.status_code != 200:
            print(f"Login error: {response.status_code} - {response.text}")
            return
        try:
            data = response.json()
        except ValueError:
            print(f"Login response is not JSON: {response.status_code} - {response.text}")
            return
        token = data.get("token")
        if not token:
            print(f"Login JSON missing token: {data}")
            return
        self.token = token


    @task
    def get_profile(self):
        if not getattr(self, "token", None):
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.get("/profile", headers=headers) as respo:
            if respo.status_code != 200:
                print(f"Error: {respo.status_code} - {respo.text}")
            else:
                print(f"Success: {respo.json()}")
