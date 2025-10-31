import logging
import ipaddress
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class IPWhitelist:
    """Manage IP whitelist for restricting access (e.g., nginx only)."""
    def __init__(self, whitelist: Optional[List[str]] = None):
        self.enabled = False
        self.whitelist: List[ipaddress.IPv4Network | ipaddress.IPv4Address] = []
        if whitelist:
            self.enabled = len(whitelist) > 0
            for ip_str in whitelist:
                try:
                    if '/' in ip_str:
                        self.whitelist.append(ipaddress.IPv4Network(ip_str))
                        logger.info("Added CIDR network to whitelist: %s", ip_str)
                    else:
                        self.whitelist.append(ipaddress.IPv4Address(ip_str))
                        logger.info("Added IP to whitelist: %s", ip_str)
                except ValueError as e:
                    logger.warning("Invalid IP/CIDR '%s': %s", ip_str, e)

    def is_allowed(self, client_ip: str) -> bool:
        if not self.enabled:
            return True
        try:
            ip = ipaddress.IPv4Address(client_ip)
            for allowed in self.whitelist:
                if isinstance(allowed, ipaddress.IPv4Network) and ip in allowed:
                    return True
                if isinstance(allowed, ipaddress.IPv4Address) and ip == allowed:
                    return True
            return False
        except ValueError:
            logger.warning("Invalid client IP format: %s", client_ip)
            return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "count": len(self.whitelist),
            "whitelist": [str(ip) for ip in self.whitelist]
        }
