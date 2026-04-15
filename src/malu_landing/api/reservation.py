"""
玛露遮瑕膏落地页 - 后端 API

功能：
- 预约创建接口
- 预约查询接口
- 数据验证
- 错误处理
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import uuid

app = FastAPI(
    title="玛露遮瑕膏预约系统",
    description="Issue #12 - 落地页商业化压力测试",
    version="1.0.0"
)

# 数据模型
class ReservationCreate(BaseModel):
    """创建预约请求"""
    name: str = Field(..., min_length=2, max_length=50, description="姓名")
    phone: str = Field(..., min_regex="^1[3-9]\\d{9}$", description="手机号码")
    email: Optional[str] = Field(None, description="邮箱")
    shade: str = Field(..., description="色号")
    message: Optional[str] = Field(None, max_length=500, description="留言")
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v or len(v) != 11:
            raise ValueError('手机号码格式不正确')
        if not v.startswith('1'):
            raise ValueError('手机号码格式不正确')
        return v
    
    @validator('shade')
    def validate_shade(cls, v):
        if v not in ['light', 'medium', 'dark']:
            raise ValueError('色号选择无效')
        return v

class Reservation(ReservationCreate):
    """预约完整信息"""
    id: str = Field(..., description="预约编号")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    status: str = Field(default="pending", description="状态")

# 模拟数据库
reservations_db = {}

@app.post("/api/reservation", 
          response_model=Reservation,
          status_code=status.HTTP_201_CREATED,
          summary="创建预约")
async def create_reservation(reservation: ReservationCreate):
    """
    创建新的预约
    
    - **name**: 姓名（2-50字符）
    - **phone**: 手机号码（11位，1开头）
    - **email**: 邮箱（可选）
    - **shade**: 色号（light/medium/dark）
    - **message**: 留言（可选，最多500字符）
    """
    try:
        # 生成预约编号
        reservation_id = f"ML{uuid.uuid4().hex[:12].upper()}"
        
        # 创建预约对象
        new_reservation = Reservation(
            id=reservation_id,
            **reservation.dict()
        )
        
        # 保存到模拟数据库
        reservations_db[reservation_id] = new_reservation
        
        return new_reservation
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建预约失败: {str(e)}"
        )

@app.get("/api/reservation/{reservation_id}",
         response_model=Reservation,
         summary="查询预约")
async def get_reservation(reservation_id: str):
    """
    根据预约编号查询预约信息
    
    - **reservation_id**: 预约编号
    """
    if reservation_id not in reservations_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"预约编号 {reservation_id} 不存在"
        )
    
    return reservations_db[reservation_id]

@app.get("/api/health",
         summary="健康检查")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "reservations_count": len(reservations_db)
    }

@app.on_event("startup")
async def startup_event():
    """启动事件"""
    print("✅ 玛露遮瑕膏预约系统启动成功")
    print(f"📖 API 文档: http://localhost:8001/docs")
    print(f"💚 健康检查: http://localhost:8001/api/health")

@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    print("👋 玛露遮瑕膏预约系统关闭")
