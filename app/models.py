import uuid
from sqlalchemy import (
    Table, Column, Integer, String, ForeignKey, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

organization_activity_association = Table(
    'organization_activity',
    Base.metadata,
    Column('organization_uuid', UUID(as_uuid=True), ForeignKey('organizations.uuid')),
    Column('activity_uuid', UUID(as_uuid=True), ForeignKey('activities.uuid'))
)


class Organization(Base):
    __tablename__ = 'organizations'
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    phones = Column(String(50), nullable=False, unique=True)

    building_uuid = Column(Integer, ForeignKey('buildings.uuid'))
    building = relationship("Building", back_populates="organizations")
    activities = relationship("Activity", secondary=organization_activity_association)

class Building(Base):
    __tablename__ = 'buildings'
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    organizations = relationship("Organization", back_populates="building")


class Activity(Base):
    __tablename__ = 'activity'
    
    MAX_DEPTH = 3

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name      = Column(String, nullable=False)
    parent_uuid = Column(Integer, ForeignKey('activity.uuid'))
    parent    = relationship('Activity', remote_side=[id], backref='children')

    @property
    def depth(self):
        return 1 + (self.parent.depth if self.parent else 0)
    
    @validates('parent')
    def _validate_parent(self, key, parent):
        if parent and parent.depth + 1 > Activity.MAX_DEPTH:
            raise ValueError(f"Нельзя вложить более чем {Activity.MAX_DEPTH} уровней")
        return parent