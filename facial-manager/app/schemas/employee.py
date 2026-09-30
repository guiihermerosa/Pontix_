"""
Schemas Pydantic para funcionários.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EmployeeBase(BaseModel):
    userid: str = Field(..., description="ID único no dispositivo")
    name: str = Field(default="", description="Nome completo")
    department: int = Field(default=0)
    schedule: int = Field(default=0, description="ID do turno/jornada")
    role: int = Field(default=0, description="0=usuário, 1=admin")
    access_card_number: str = Field(default="")
    id_number: str = Field(default="")
    person_period: int = Field(default=0)
    pass_times: int = Field(default=-1, description="-1 = ilimitado")
    pass_date: str = Field(default="0")


class EmployeeCreate(EmployeeBase):
    userpassword: str = Field(default="", description="Senha do usuário no device")


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[int] = None
    schedule: Optional[int] = None
    role: Optional[int] = None
    access_card_number: Optional[str] = None
    id_number: Optional[str] = None
    person_period: Optional[int] = None
    pass_times: Optional[int] = None
    pass_date: Optional[str] = None
    userpassword: Optional[str] = None


class EmployeeRead(EmployeeBase):
    id: int
    has_face: bool
    has_fingerprint: bool
    has_palm: bool
    device_synced: bool
    sync_status: str
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    items: list[EmployeeRead]
    total: int
    page: int
    page_size: int
    pages: int


# Payload exato enviado ao dispositivo (POST /insertEmployee e /updateEmployee)
class DeviceEmployeePayload(BaseModel):
    userid: str
    name: str = ""
    access_card_number: str = ""
    userpassword: str = ""
    department: int = 0
    schedule: int = 0
    role: int = 0
    person_period: int = 0
    pass_times: int = -1
    pass_date: str = "0"
    pass_time: str = "[null,null,null]"
    # Arquivos biométricos — strings base64 ou vazio; nunca fabricados
    pic_large: str = ""
    featureFile: str = ""
    fingerFile: str = ""
    palm1File: str = ""
    palm2File: str = ""
