import requests
import keyring
import logging
from config import SERVER_URL, KEYRING_SERVICE, KEYRING_USERNAME

logger = logging.getLogger(__name__)


class FontDockAPI:
    def __init__(self):
        self.server_url = SERVER_URL
        self.token = None
        self.load_token()
    
    def load_token(self):
        self.token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    
    def save_token(self, token):
        self.token = token
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
    
    def clear_token(self):
        self.token = None
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except keyring.errors.PasswordDeleteError:
            pass
    
    def get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def login(self, username, password):
        logger.info(f"Attempting login for user: {username}")
        try:
            response = requests.post(
                f"{self.server_url}/auth/login",
                data={"username": username, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            self.save_token(data["access_token"])
            logger.info("Login successful")
            return data
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
    
    def get_me(self):
        response = requests.get(
            f"{self.server_url}/auth/me",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_clients(self, page_size=100):
        logger.info(f"Fetching clients (page_size={page_size})")
        try:
            response = requests.get(
                f"{self.server_url}/api/clients",
                params={"limit": page_size, "is_active": None},
                headers=self.get_headers()
            )
            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data.get('items', []))} clients")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch clients: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_collections(self, page_size=100):
        logger.info(f"Fetching collections (page_size={page_size})")
        try:
            response = requests.get(
                f"{self.server_url}/api/collections",
                params={"limit": page_size},
                headers=self.get_headers()
            )
            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data.get('items', []))} collections")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch collections: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_fonts(self, page_size=1000):
        logger.info(f"Fetching fonts (page_size={page_size})")
        try:
            response = requests.get(
                f"{self.server_url}/api/fonts",
                params={"page_size": page_size},
                headers=self.get_headers()
            )
            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data.get('items', []))} fonts")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch fonts: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_collection_fonts(self, collection_id):
        response = requests.get(
            f"{self.server_url}/api/collections/{collection_id}/fonts",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def download_font(self, font_id):
        response = requests.get(
            f"{self.server_url}/api/fonts/{font_id}/download",
            headers=self.get_headers(),
            stream=True
        )
        response.raise_for_status()
        return response.content
