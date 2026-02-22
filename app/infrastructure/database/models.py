from sqlalchemy import Column, String, ForeignKey, Enum, Boolean, Integer
from sqlalchemy.orm import relationship
from app.infrastructure.database.session import Base
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    HQ = "hq"
    STATE = "state"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.STATE.value)
    state_code = Column(String, ForeignKey("states.code"), nullable=True)
    is_active = Column(Boolean, default=True)

    state = relationship("State", back_populates="users")

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
    status = Column(String, default="active", server_default="active") # active/inactive
    is_locked = Column(Boolean, default=False, server_default="false")

    zone = relationship("Zone", back_populates="states")
    lgas = relationship("LGA", back_populates="state")
    custodians = relationship("Custodian", back_populates="state")
    schools = relationship("School", back_populates="state")
    bece_schools = relationship("BECESchool", back_populates="state")
    users = relationship("User", back_populates="state")

class LGA(Base):
    __tablename__ = "lgas"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    state_code = Column(String, ForeignKey("states.code"))

    state = relationship("State", back_populates="lgas")
    custodians = relationship("Custodian", back_populates="lga")
    schools = relationship("School", back_populates="lga")
    bece_schools = relationship("BECESchool", back_populates="lga")

class Custodian(Base):
    __tablename__ = "custodians"
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    state_code = Column(String, ForeignKey("states.code"))
    lga_code = Column(String, ForeignKey("lgas.code"))
    town = Column(String)
    status = Column(String, default="active", server_default="active")

    state = relationship("State", back_populates="custodians")
    lga = relationship("LGA", back_populates="custodians")
    schools = relationship("School", back_populates="custodian")
    bece_schools = relationship("BECESchool", back_populates="custodian")

class AccreditationStatus(enum.Enum):
    ACCREDITED = "Accredited"
    UNACCREDITED = "Unaccredited"

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
    status = Column(String, default="active", server_default="active")

    state = relationship("State", back_populates="bece_schools")
    lga = relationship("LGA", back_populates="bece_schools")
    custodian = relationship("Custodian", back_populates="bece_schools")
