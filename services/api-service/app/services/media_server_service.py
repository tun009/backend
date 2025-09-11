import httpx
import logging
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.redis_client import redis_client

# Cấu hình logging
logger = logging.getLogger(__name__)

class MediaServerService:
    def __init__(self):
        self.base_url = settings.MEDIA_SERVER_URL
        self.username = settings.MEDIA_SERVER_USERNAME
        self.password = settings.MEDIA_SERVER_PASSWORD
        self.token_key = "media_server_access_token"

    async def _login_and_cache_token(self) -> str:
        """Đăng nhập vào media server và cache token vào Redis."""
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Attempting to log in to media server at {self.base_url}")
                response = await client.post(
                    f"{self.base_url}/v1/auth/login",
                    json={"username": self.username, "password": self.password},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                token = data.get("access_token")
                if not token:
                    logger.error("Media server login failed: no token in response")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Media server login failed: no token")
                
                # Cache token với thời gian hết hạn là 55 phút (để an toàn)
                await redis_client.set(self.token_key, token, ttl=3300)
                logger.info("Successfully logged in and cached media server token.")
                return token
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error while logging in to media server: {e}")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not log in to media server: {e.response.status_code}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during media server login: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during media server login")

    async def get_token(self) -> str:
        """Lấy token từ cache, nếu không có thì login lại."""
        token = await redis_client.get(self.token_key)
        if token:
            logger.debug("Retrieved media server token from cache.")
            return token
        return await self._login_and_cache_token()

    async def get_video_files(self, device_no: str, start_time: str, end_time: str) -> list:
        """Lấy danh sách file video, tự động refresh token nếu cần."""
        token = await self.get_token()
        
        async def _fetch_with_token(auth_token: str, page: int = 1):
            params = {
                "device_no": device_no,
                "taken_at_1": start_time,
                "taken_at_2": end_time,
                "media_type": 3,
                "page": page,
                "limit": 1000  # Lấy tối đa 1000 file mỗi lần
            }
            headers = {"Authorization": f"Bearer {auth_token}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/v1/file-info", params=params, headers=headers)
                return response

        all_files = []
        current_page = 1
        while True:
            response = await _fetch_with_token(token, current_page)
            
            if response.status_code == 401:  # Token hết hạn
                logger.warning("Media server token expired. Re-logging in.")
                token = await self._login_and_cache_token() # Lấy token mới
                response = await _fetch_with_token(token, current_page) # Thử lại

            response.raise_for_status()
            files_on_page = response.json().get("data", [])
            if not files_on_page:
                break
            all_files.extend(files_on_page)
            current_page += 1
            
        return all_files


    async def get_latest_video_info(self, device_no: str) -> dict | None:
        """Fetches the most recent video/image file info for a device."""
        token = await self.get_token()

        async def _fetch_with_token(auth_token: str):
            params = {
                "device_no": device_no,
                "media_type": 3, # Assuming 3 is for videos/images with thumbnails
                "page": 1,
                "limit": 1,
                "order_by": "taken_at-desc"            }
            headers = {"Authorization": f"Bearer {auth_token}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/v1/file-info", params=params, headers=headers)
                return response

        response = await _fetch_with_token(token)

        if response.status_code == 401:
            logger.warning("Media server token expired. Re-logging in.")
            token = await self._login_and_cache_token()
            response = await _fetch_with_token(token)

        response.raise_for_status()
        data = response.json().get("data", [])

        if not data:
            return None
        return data[0]

# Tạo một instance để sử dụng trong các routes
media_server_service = MediaServerService()

