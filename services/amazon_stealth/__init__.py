"""Amazon stealth extraction module."""
from services.amazon_stealth.identities import BrowserIdentity, IDENTITY_PROFILES
from services.amazon_stealth.identity_manager import IdentityManager

__all__ = ['BrowserIdentity', 'IDENTITY_PROFILES', 'IdentityManager']
