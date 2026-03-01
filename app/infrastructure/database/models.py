from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime, Text
from sqlalchemy.orm import relationship
from app.infrastructure.database.session import Base
from datetime import datetime
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    HQ = "hq"
    STATE = "state"
    SCHOOL = "school"
    VIEWER = "viewer"

class AccreditationStatus(enum.Enum):
    ACCREDITED = "Accredited"
    UNACCREDITED = "Unaccredited"
    PENDING = "Pending"
    RE_ACCREDITATION = "Re-accreditation"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # admin, hq, state, school
    state_code = Column(String, ForeignKey("states.code"), nullable=True)
    is_active = Column(Boolean, default=True)

class Zone(Base):
    __tablename__ = "zones"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    
    states = relationship("State", back_populates="zone")

class State(Base):
    __tablename__ = "states"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    capital = Column(String, nullable=True)
    email = Column(String, nullable=True)
    zone_code = Column(String, ForeignKey("zones.code"))
    status = Column(String, default="active", server_default="active")
    is_locked = Column(Boolean, default=False, server_default="false")

    zone = relationship("Zone", back_populates="states")
    lgas = relationship("LGA", back_populates="state")
    custodians = relationship("Custodian", back_populates="state")
    schools = relationship("School", back_populates="state")
    bece_schools = relationship("BECESchool", back_populates="state")

class LGA(Base):
    __tablename__ = "lgas"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    state_code = Column(String, ForeignKey("states.code"), nullable=False)

    state = relationship("State", back_populates="lgas")
    custodians = relationship("Custodian", back_populates="lga")
    schools = relationship("School", back_populates="lga")
    bece_schools = relationship("BECESchool", back_populates="lga")

class Custodian(Base):
    __tablename__ = "custodians"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    state_code = Column(String, ForeignKey("states.code"), nullable=True)
    lga_code = Column(String, ForeignKey("lgas.code"), nullable=True)
    town = Column(String)
    status = Column(String, default="active", server_default="active")

    state = relationship("State", back_populates="custodians")
    lga = relationship("LGA", back_populates="custodians")
    schools = relationship("School", back_populates="custodian")
    bece_schools = relationship("BECESchool", back_populates="custodian")

class School(Base):
    __tablename__ = "schools"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    state_code = Column(String, ForeignKey("states.code"))
    lga_code = Column(String, ForeignKey("lgas.code"))
    custodian_code = Column(String, ForeignKey("custodians.code"))
    email = Column(String, nullable=True)
    accreditation_status = Column(String, default=AccreditationStatus.UNACCREDITED.value, server_default=AccreditationStatus.UNACCREDITED.value)
    accredited_date = Column(String, nullable=True) # ISO format date
    category = Column(String, default="PUB", server_default="PUB") # PUB/PRV
    accrd_year = Column(String, nullable=True)
    payment_url = Column(String, nullable=True)
    status = Column(String, default="active", server_default="active")

    state = relationship("State", back_populates="schools")
    lga = relationship("LGA", back_populates="schools")
    custodian = relationship("Custodian", back_populates="schools")

class BECESchool(Base):
    __tablename__ = "bece_schools"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    state_code = Column(String, ForeignKey("states.code"))
    lga_code = Column(String, ForeignKey("lgas.code"))
    custodian_code = Column(String, ForeignKey("custodians.code"))
    email = Column(String, nullable=True)
    accreditation_status = Column(String, default=AccreditationStatus.UNACCREDITED.value, server_default=AccreditationStatus.UNACCREDITED.value)
    accredited_date = Column(String, nullable=True) # ISO format date
    category = Column(String, default="PUB", server_default="PUB") # PUB/PRV
    accrd_year = Column(String, nullable=True)
    payment_url = Column(String, nullable=True)
    status = Column(String, default="active", server_default="active")

    state = relationship("State", back_populates="bece_schools")
    lga = relationship("LGA", back_populates="bece_schools")
    custodian = relationship("Custodian", back_populates="bece_schools")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_role = Column(String, nullable=False)  # admin, hq, state, viewer
    action = Column(String, nullable=False)  # CREATE, READ, UPDATE, DELETE, EXPORT, etc.
    resource_type = Column(String, nullable=False)  # SCHOOL, STATE, CUSTODIAN, ZONE, LGA, etc.
    resource_id = Column(String, nullable=True)  # ID of the resource
    details = Column(Text, nullable=True)  # Additional details in JSON or text format
    timestamp = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    ip_address = Column(String, nullable=True)  # Client IP address
    
    user = relationship("User", foreign_keys=[user_id])
