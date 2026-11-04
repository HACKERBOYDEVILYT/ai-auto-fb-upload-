#!/usr/bin/env python3
"""
Proxy Manager for rotating proxies
Supports: HTTP, HTTPS, SOCKS5 proxies
"""

import random
import aiohttp
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy rotation for API requests"""
    
    def __init__(self, proxy_file: str = None):
        self.proxies: List[str] = []
        self.current_index = 0
        
        if proxy_file:
            self.load_proxies(proxy_file)
    
    def load_proxies(self, file_path: str):
        """Load proxies from file and ensure proper URL scheme"""
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # aiohttp requires http:// or socks5:// prefix
                        if not line.startswith(("http://", "https://", "socks5://", "socks4://")):
                            line = f"http://{line}"
                        self.proxies.append(line)
            logger.info(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            logger.warning(f"Proxy file not found: {file_path}")
    
    async def _verify_proxy(self, proxy: str, session: aiohttp.ClientSession) -> bool:
        """Verify proxy with strict timeout"""
        try:
            # Short timeout to avoid hanging the process on dead proxies
            async with session.get(
                'https://httpbin.org/ip',
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                return response.status == 200
        except Exception:
            return False

    async def get_proxy(self, verify: bool = False) -> Optional[str]:
        """
        Get next proxy.
        Set verify=True if you want real-time verification (slower).
        Set verify=False to fast-rotate without blocking.
        """
        if not self.proxies:
            return None
        
        if not verify:
            proxy = self.proxies[self.current_index % len(self.proxies)]
            self.current_index += 1
            return proxy

        # Verification enabled mode
        async with aiohttp.ClientSession() as session:
            total_proxies = len(self.proxies)
            for _ in range(total_proxies):
                proxy = self.proxies[self.current_index % total_proxies]
                self.current_index += 1
                
                if await self._verify_proxy(proxy, session):
                    return proxy
            
            logger.warning("All proxies failed verification")
            return None

    def get_random_proxy(self) -> Optional[str]:
        """Get a random proxy immediately"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def add_proxy(self, proxy: str):
        """Add a new proxy"""
        if not proxy.startswith(("http://", "https://", "socks5://", "socks4://")):
            proxy = f"http://{proxy}"
        self.proxies.append(proxy)
        logger.info(f"Added proxy: {proxy}")
