from locust import HttpUser, between, task


class SmokeTest(HttpUser):
    wait_time = between(1, 2)

    @task
    def health_check(self):
        self.client.get("/health")

    @task
    def get_home(self):
        self.client.get("/")
