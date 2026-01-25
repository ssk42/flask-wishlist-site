"""Amazon stealth extraction module."""
from services.amazon_stealth.identities import (
    BrowserIdentity, IDENTITY_PROFILES
)
from services.amazon_stealth.identity_manager import IdentityManager
from services.amazon_stealth.extractor import (
    ExtractionResult,
    AmazonFailureType,
    stealth_fetch_amazon,
    stealth_fetch_amazon_sync,
)

__all__ = [
    'BrowserIdentity',
    'IDENTITY_PROFILES',
    'IdentityManager',
    'ExtractionResult',
    'AmazonFailureType',
    'stealth_fetch_amazon',
    'stealth_fetch_amazon_sync',
]
