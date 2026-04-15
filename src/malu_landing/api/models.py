"""
玛露遮瑕膏落地页 - 数据模型
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class ReservationBase(BaseModel):
    """预约基础模型"""
    name: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., min_length=11, max_length=11)
    email: Optional[str] = None
    shade: str
    message: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v or len(v) != 11:
            raise ValueError('手机号码必须是11位')
        if not v.startswith('1'):
            raise ValueError('手机号码必须以1开头')
        return v
    
    @validator('shade')
    def validate_shade(cls, v):
        if v not in ['light', 'medium', 'dark']:
            raise ValueError('色号必须是 light/medium/dark 之一')
        return v

class ReservationCreate(ReservationBase):
    """创建预约请求"""
    pass

class Reservation(ReservationBase):
    """预约完整信息"""
    id: str
    created_at: datetime
    status: str = "pending"
    
    class Config:
        orm_mode = True
