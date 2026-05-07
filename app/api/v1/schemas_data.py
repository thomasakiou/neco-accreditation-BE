from pydantic import BaseModel
from typing import Optional, List, Literal

# Zone Schemas
class ZoneBase(BaseModel):
    code: str
    name: str
    zone_email: Optional[str] = None

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    zone_email: Optional[str] = None

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
    ministry_email: Optional[str] = None
    zone_code: str
    status: str = "active"
    is_locked: bool = False

class StateCreate(StateBase):
    pass

class StateUpdate(BaseModel):
    name: Optional[str] = None
    capital: Optional[str] = None
    email: Optional[str] = None
    ministry_email: Optional[str] = None
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

# BECE Custodian Schemas
class BECECustodianBase(BaseModel):
    code: str
    name: str
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    town: Optional[str] = None
    status: str = "active"

class BECECustodianCreate(BECECustodianBase):
    pass

class BECECustodianUpdate(BaseModel):
    name: Optional[str] = None
    state_code: Optional[str] = None
    lga_code: Optional[str] = None
    town: Optional[str] = None
    status: Optional[str] = None

class BECECustodian(BECECustodianBase):
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
    accreditation_type: Optional[str] = None
    accredited_date: Optional[str] = None
    category: Literal["PUB", "PRV", "FED"] = "PUB"
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    approval_status: Optional[str] = None
    gender: Optional[str] = None
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
    accreditation_type: Optional[str] = None
    accredited_date: Optional[str] = None
    category: Optional[Literal["PUB", "PRV", "FED"]] = None
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    approval_status: Optional[str] = None
    gender: Optional[str] = None
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
    accreditation_type: Optional[str] = None
    accredited_date: Optional[str] = None
    category: Literal["PUB", "PRV", "FED"] = "PUB"
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    approval_status: Optional[str] = None
    gender: Optional[str] = None
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
    accreditation_type: Optional[str] = None
    accredited_date: Optional[str] = None
    category: Optional[Literal["PUB", "PRV", "FED"]] = None
    accrd_year: Optional[str] = None
    payment_url: Optional[str] = None
    approval_status: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None

class BECESchool(BECESchoolBase):
    class Config:
        from_attributes = True


class DuplicateForYearResponse(BaseModel):
    message: str
    schools_duplicated: int
    bece_schools_duplicated: int

# Manual Email Trigger Schemas
class ManualEmailSchool(BaseModel):
    code: str
    type: Literal["SSCE", "BECE"]

class ManualEmailRequest(BaseModel):
    schools: List[ManualEmailSchool]
