import requests
import time

class APIClient:
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"token {token}"}
        self.remaining_rate_limit = 5000
        self.rate_limit_reset_time = 0

    def make_request(self, url, params=None):
        """Make an API request with rate limit handling."""
        self._check_rate_limit()
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                self._update_rate_limit(response)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                    self._handle_rate_limit_exceeded()
                    continue
                elif response.status_code == 404:
                    print(f"Resource not found: {url}")
                    return None
                else:
                    retry_count += 1
                    self._handle_retry(retry_count, response)
            except Exception as e:
                retry_count += 1
                self._handle_retry(retry_count, e)

        print(f"Failed after {max_retries} retries")
        return None

    def _check_rate_limit(self):
        """Check if we need to wait for rate limit reset."""
        if self.remaining_rate_limit < 20:
            current_time = time.time()
            if current_time < self.rate_limit_reset_time:
                wait_time = self.rate_limit_reset_time - current_time + 10
                print(f"Rate limit almost reached. Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)

    def _update_rate_limit(self, response):
        """Update rate limit information from response headers."""
        self.remaining_rate_limit = int(response.headers.get('X-RateLimit-Remaining', 0))
        self.rate_limit_reset_time = int(response.headers.get('X-RateLimit-Reset', 0))

    def _handle_rate_limit_exceeded(self):
        """Handle rate limit exceeded scenario."""
        wait_time = self.rate_limit_reset_time - time.time() + 10
        print(f"Rate limit exceeded. Waiting {wait_time:.0f} seconds...")
        time.sleep(wait_time)

    def _handle_retry(self, retry_count, error):
        """Handle retry logic for failed requests."""
        wait_time = 2 ** retry_count
        print(f"Error: {error}. Retrying in {wait_time} seconds...")
        time.sleep(wait_time)