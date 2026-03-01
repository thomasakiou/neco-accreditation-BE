from pydantic import BaseModel
from typing import Optional, List

# Zone Schemas
class ZoneBase(BaseModel):
    code: str
    name: str

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(BaseModel):
    name: Optional[str] = None

class Zone(ZoneBase):
    class Config:
        from_attributes = True

# LGA Schemas
class LGABase(BaseModel):
    code: str
    name: str
    state_code: Optional[str] = None

class LGACreate(LGABase):
    pass

class LGAUpdate(BaseModel):
    name: Optional[str] = None
    state_code: Optional[str] = None

class LGA(LGABase):
    class Config:
        from_attributes = True

# State Schemas
class StateBase(BaseModel):
    code: str
    name: str
    capital: Optional[str] = None
    email: Optional[str] = None
    zone_code: str
    status: str = "active"
    is_locked: bool = False

class StateCreate(StateBase):
    pass

class StateUpdate(BaseModel):
    name: Optional[str] = None
    capital: Optional[str] = None
    email: Optional[str] = None
    zone_code: Optional[str] = None
    status: Optional[str] = None
    is_locked: Optional[bool] = None

class State(StateBase):
    class Config:
        from_attributes = True

# Custodian Schemas
class CustodianBase(BaseModel):
    code: str
    name: str
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    town: Optional[str] = None
    status: str = "active"

class CustodianCreate(CustodianBase):
    pass

class CustodianUpdate(BaseModel):
    name: Optional[str] = None
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    town: Optional[str] = None
    status: Optional[str] = None

class Custodian(CustodianBase):
    class Config:
        from_attributes = True

# School Schemas
class SchoolBase(BaseModel):
    code: str
    name: str
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    custodian_code: Optional[str] = None
    email: Optional[str] = None
    accreditation_status: str = "Unaccredited"
    accredited_date: Optional[str] = None
    category: str = "PUB"
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    status: str = "active"

class SchoolCreate(SchoolBase):
    state_code: str
    custodian_code: str

class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    custodian_code: Optional[str] = None
    email: Optional[str] = None
    accreditation_status: Optional[str] = None
    accredited_date: Optional[str] = None
    category: Optional[str] = None
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    status: Optional[str] = None

class School(SchoolBase):
    class Config:
        from_attributes = True

# BECE School Schemas
class BECESchoolBase(BaseModel):
    code: str
    name: str
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    custodian_code: Optional[str] = None
    email: Optional[str] = None
    accreditation_status: str = "Unaccredited"
    accredited_date: Optional[str] = None
    category: str = "PUB"
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    status: str = "active"

class BECESchoolCreate(BECESchoolBase):
    state_code: str
    custodian_code: str

class BECESchoolUpdate(BaseModel):
    name: Optional[str] = None
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    custodian_code: Optional[str] = None
    email: Optional[str] = None
    accreditation_status: Optional[str] = None
    accredited_date: Optional[str] = None
    category: Optional[str] = None
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    status: Optional[str] = None

class BECESchool(BECESchoolBase):
    class Config:
        from_attributes = True
