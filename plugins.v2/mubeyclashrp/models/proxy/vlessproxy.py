from pydantic import Field, field_validator
from typing import Optional, Literal

from .proxybase import ProxyBase
from .tlsmixin import TLSMixin
from .networkmixin import NetworkMixin


class VlessProxy(ProxyBase, TLSMixin, NetworkMixin):
    type: Literal['vless'] = 'vless'
    uuid: str
    flow: Optional[str] = None
    packet_addr: Optional[bool] = Field(None, alias='packet-addr')
    xudp: Optional[bool] = None
    packet_encoding: Optional[Literal['packetaddr', 'xudp']] = Field(None, alias='packet-encoding')
    encryption: Optional[str] = None

    @field_validator('packet_encoding', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty string to None for packet_encoding"""
        if v == '':
            return None
        return v
