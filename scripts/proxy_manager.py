#!/usr/bin/env python3
"""
Proxy Manager for rotating proxies
Supports: HTTP, HTTPS, SOCKS5 proxies
"""

import random
import aiohttp
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy rotation for API requests"""
    
    def __init__(self, proxy_file: str = None):
        self.proxies = []
        self.current_index = 0
        
        if proxy_file:
            self.load_proxies(proxy_file)
    
    def load_proxies(self, file_path: str):
        """Load proxies from file"""
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.proxies.append(line)
            logger.info(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            logger.warning(f"Proxy file not found: {file_path}")
    
    async def get_proxy(self) -> Optional[str]:
        """Get next available proxy"""
        
        if not self.proxies:
            return None
        
        # Rotate through proxies
        proxy = self.proxies[self.current_index % len(self.proxies)]
        self.current_index += 1
        
        # Verify proxy works
        if await self._verify_proxy(proxy):
            return proxy
        else:
            # Try other proxies
            for p in self.proxies:
                if await self._verify_proxy(p):
                    return p
            
            logger.warning("All proxies failed verification")
            return None
    
    async def _verify_proxy(self, proxy: str) -> bool:
        """Verify proxy is working"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://httpbin.org/ip',
                    proxy=proxy,
                    timeout=5
                ) as response:
                    return response.status == 200
        except:
            return False
    
    def add_proxy(self, proxy: str):
        """Add a new proxy"""
        self.proxies.append(proxy)
        logger.info(f"Added proxy: {proxy}")
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random proxy"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
