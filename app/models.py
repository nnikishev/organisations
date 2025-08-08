import uuid

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates

Base = declarative_base()


organization_phone = Table(
    "organization_phone",
    Base.metadata,
    Column("organization_id", UUID(as_uuid=True), ForeignKey("organizations.uuid")),
    Column("phone_id", Integer, ForeignKey("phones.id")),
)

organization_activity = Table(
    "organization_activity",
    Base.metadata,
    Column("organization_id", UUID(as_uuid=True), ForeignKey("organizations.uuid")),
    Column("activity_id", UUID(as_uuid=True), ForeignKey("activity.uuid")),
)


class Phone(Base):
    __tablename__ = "phones"

    id = Column(Integer, primary_key=True)
    number = Column(String(50), nullable=False, unique=True)


class Organization(Base):
    __tablename__ = "organizations"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)

    building_uuid = Column(
        UUID(as_uuid=True), ForeignKey("buildings.uuid"), nullable=True
    )
    building = relationship("Building", back_populates="organizations", lazy="selectin")

    phones = relationship("Phone", secondary=organization_phone, lazy="selectin")
    activities = relationship(
        "Activity",
        secondary=organization_activity,
        back_populates="organizations",
        lazy="selectin",
    )


class Building(Base):
    __tablename__ = "buildings"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    organizations = relationship("Organization", back_populates="building")


class Activity(Base):
    __tablename__ = "activity"

    MAX_DEPTH = 3

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    parent_uuid = Column(UUID(as_uuid=True), ForeignKey("activity.uuid"), nullable=True)

    parent = relationship("Activity", remote_side=[uuid], backref="children")

    organizations = relationship(
        "Organization", secondary=organization_activity, back_populates="activities"
    )

    @property
    def depth(self):
        return 1 + (self.parent.depth if self.parent else 0)

    @validates("parent")
    def _validate_parent(self, key, parent):
        if parent and parent.depth + 1 > self.MAX_DEPTH:
            raise ValueError(f"Нельзя вложить более чем {self.MAX_DEPTH} уровней")
        return parent
