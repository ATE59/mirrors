# coding=utf-8

from ipaddress import (
    IPv4Network,
    IPv4Address,
)
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Table,
    ForeignKey,
    Boolean,
    DateTime,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from typing import (
    Dict,
    AnyStr,
    Union,
    List,
)

from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_method

from api.utils import get_asn_by_ip
from common.sentry import (
    get_logger,
)

logger = get_logger(__name__)


Base = declarative_base()


class Subnet(Base):
    ___tablename__ = 'subnets'

    id = Column(Integer, nullable=False, primary_key=True)
    subnet = Column(String, nullable=False)


class Url(Base):
    __tablename__ = 'urls'

    id = Column(Integer, nullable=False, primary_key=True)
    url = Column(String, nullable=False)
    type = Column(String, nullable=False)

    def to_dict(self) -> Dict[AnyStr, AnyStr]:
        return {
           self.type: self.url,
        }


mirrors_urls = Table(
    'mirrors_urls',
    Base.metadata,
    Column(
        'mirror_id', Integer, ForeignKey(
            'mirrors.id',
            ondelete='CASCADE',
        ),
    ),
    Column(
        'url_id', Integer, ForeignKey(
            'urls.id',
            ondelete='CASCADE',
        )
    ),
)


mirrors_subnets = Table(
    'mirrors_subnets',
    Base.metadata,
    Column(
        'mirror_id', Integer, ForeignKey(
            'mirrors.id',
            ondelete='CASCADE',
        ),
    ),
    Column(
        'subnet_id', Integer, ForeignKey(
            'subnets.id',
            ondelete='CASCADE',
        )
    ),
)


class Mirror(Base):
    __tablename__ = 'mirrors'

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    continent = Column(String, nullable=False)
    country = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_expired = Column(Boolean, nullable=False, default=False)
    update_frequency = Column(DateTime, nullable=False)
    sponsor_name = Column(String, nullable=False)
    sponsor_url = Column(String, nullable=False)
    email = Column(String, nullable=False)
    asn = Column(String, nullable=True)
    urls = relationship(
        'Url',
        secondary=mirrors_urls,
        passive_deletes=True,
    )
    subnets = relationship(
        'Subnet',
        secondary=mirrors_subnets,
        passive_deletes=True,
    )

    @hybrid_method
    def is_in_any_subnet(self, ip_address: Union[IPv4Address, AnyStr]):
        if isinstance(ip_address, str):
            ip_address = IPv4Address(ip_address)
        return any(ip_address in IPv4Network(subnet.subnet)
                   for subnet in self.subnets)

    @is_in_any_subnet.expression
    def is_in_any_subnet(self, ip_address: Union[IPv4Address, AnyStr]):
        if isinstance(ip_address, str):
            ip_address = IPv4Address(ip_address)
        return func.any(ip_address in IPv4Network(subnet.subnet)
                        for subnet in self.subnets)

    @hybrid_method
    def is_in_same_asn(self, ip_address: Union[IPv4Address, AnyStr]):
        if isinstance(ip_address, IPv4Address):
            ip_address = str(ip_address)
        asn = get_asn_by_ip(ip_address)
        return self.asn == asn.autonomous_system_number

    @is_in_same_asn.expression
    def is_in_same_asn(self, ip_address: Union[IPv4Address, AnyStr]):
        if isinstance(ip_address, IPv4Address):
            ip_address = str(ip_address)
        asn = get_asn_by_ip(ip_address)
        return self.asn == asn.autonomous_system_number

    @hybrid_method
    def conditional_distance(self, lon: float, lat: float):
        """
        Calculate conditional distance between this mirror and some point
        This method is used like instance-method
        """
        return abs(self.longitude - lon) + abs(self.latitude - lat)

    @conditional_distance.expression
    def conditional_distance(self, lon: float, lat: float):
        """
        Calculate conditional distance between this mirror and some point
        This method is used like class-method
        """
        return func.abs(self.longitude - lon) + func.abs(self.latitude - lat)

    def to_dict(self) -> Dict[AnyStr, Union[AnyStr, float, Dict, List]]:
        return {
            'name': self.name,
            'continent': self.continent,
            'country': self.country,
            'ip': self.ip,
            'location': {
                'lat': self.latitude,
                'lon': self.longitude,
            },
            'is_expired': self.is_expired,
            'update_frequency': self.update_frequency.strftime('%H'),
            'sponsor_name': self.sponsor_name,
            'sponsor_url': self.sponsor_url,
            'email': self.email,
            'urls': {url.type: url.url for url in self.urls},
        }
