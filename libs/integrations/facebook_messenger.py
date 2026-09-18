"""Facebook Messenger adapter (dry-run). Credential env: FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN."""
from .base import Adapter


class FacebookMessengerAdapter(Adapter):
    name = "facebook_messenger"
    required_env = ["FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"]
