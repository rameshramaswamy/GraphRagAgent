from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize Limiter
# storage_uri can point to Redis ("redis://...") for distributed limiting
# For now, memory storage is fine for single-node API
limiter = Limiter(key_func=get_remote_address)