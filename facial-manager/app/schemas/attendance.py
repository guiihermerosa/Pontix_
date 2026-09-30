"""
Schemas Pydantic para presença/marcações.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AttendanceRecordRead(BaseModel):
    id: int
    userid: str
    employee_name: str
    attendance_date: str
    attendance_time: str
    record_type: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceListResponse(BaseModel):
    items: list[AttendanceRecordRead]
    total: int
    page: int
    page_size: int
    pages: int


class AttendanceFilter(BaseModel):
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    userid: Optional[str] = None
    department: Optional[int] = None
    record_type: Optional[str] = None
    page: int = 1
    page_size: int = 50


# Representa um dia de um funcionário retornado por /getAttendTable
class AttendanceDay(BaseModel):
    att_date: str
    att_week: str
    shift_t1: str = ""
    shift_t2: str = ""
    shift_t3: str = ""
    shift_t4: str = ""
    shift_t5: str = ""
    shift_t6: str = ""
    att_standard: str = "0.0"
    att_actual: str = "0.0"
    att_over: str = "0.0"
    att_late: str = "0"
    att_early: str = "0"


class AttendanceSummaryItem(BaseModel):
    userid: str
    employee_name: str
    department: str
    att_standard: str
    att_actual: str
    late_num: str
    late_min: str
    early_num: str
    early_min: str
    over_standard: str
    over_actual: str
    work_days: str
    absent_days: str


# Quem passou hoje — visão consolidada para o dashboard
class TodayStatus(BaseModel):
    userid: str
    name: str
    passed: bool
    last_time: Optional[str] = None   # horário da última marcação hoje
