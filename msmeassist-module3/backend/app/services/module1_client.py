"""
HTTP Client for communicating with Module 1 (Business Profile & Eligibility Engine).
"""
import logging
from typing import Any, Dict, Optional
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Module1Client:
    """Consumes business profile information from Module 1 API on port 8000."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.module1_base_url.rstrip("/")

    async def get_profile(self, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetches the authenticated user's profile from Module 1."""
        if not auth_token:
            return None

        headers = {"Authorization": f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token}
        url = f"{self.base_url}/api/profile/me"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    return res.json()
                logger.warning(f"Module 1 profile fetch returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.warning(f"Failed to connect to Module 1 at {url}: {e}")

        return None
