"""Paperclip 协同 API 路由器 - 外部企业管理系统双向接口"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/paperclip", tags=["paperclip"])


class BudgetRequest(BaseModel):
    """预算指令请求模型"""
    department: str = Field(..., description="部门名称", example="玛露美妆销售部")
    target_budget: float = Field(..., description="目标预算金额", example=100000.0)


class BudgetResponse(BaseModel):
    """预算指令响应模型"""
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="响应消息")
    department: str = Field(..., description="部门名称")
    target_budget: float = Field(..., description="目标预算")
    timestamp: str = Field(..., description="时间戳")
    request_id: str = Field(..., description="请求ID")


class CallbackData(BaseModel):
    """Webhook 回调数据模型"""
    roi: float = Field(..., description="投资回报率", example=2.5)
    token_used: int = Field(..., description="消耗的 Token 数量", example=50000)
    timestamp: str = Field(..., description="执行时间戳", example="2026-03-25T23:15:00Z")
    department: Optional[str] = Field(None, description="部门名称（可选）")


class CallbackResponse(BaseModel):
    """回调响应模型"""
    status: str = Field(..., description="接收状态")
    message: str = Field(..., description="确认消息")
    received_at: str = Field(..., description="接收时间")


# 模拟存储（实际应连接到数据库或消息队列）
_budget_store = {}
_callback_store = []


@router.post("/budget", response_model=BudgetResponse)
async def receive_budget_instruction(request: BudgetRequest) -> BudgetResponse:
    """
    接收目标预算指令
    
    **测试用例**: 玛露美妆品牌销售部
    
    **请求示例**:
    ```json
    {
      "department": "玛露美妆销售部",
      "target_budget": 100000
    }
    ```
    
    **功能**:
    - 接收来自外部企业管理系统的预算目标
    - 触发 Agent 系统的预算执行流程
    - 返回确认信息和请求ID
    """
    try:
        # 生成请求ID
        request_id = f"budget_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.department) % 10000:04d}"
        
        # 存储预算指令（模拟）
        _budget_store[request_id] = {
            "department": request.department,
            "target_budget": request.target_budget,
            "received_at": datetime.now().isoformat(),
            "status": "accepted"
        }
        
        # 构建响应
        return BudgetResponse(
            status="accepted",
            message=f"预算指令已接收，部门：{request.department}，目标预算：¥{request.target_budget:,.2f}",
            department=request.department,
            target_budget=request.target_budget,
            timestamp=datetime.now().isoformat(),
            request_id=request_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理预算指令失败: {str(e)}"
        )


@router.post("/callback", response_model=CallbackResponse)
async def receive_execution_callback(data: CallbackData) -> CallbackResponse:
    """
    接收执行结果回调（Webhook 推送）
    
    **数据格式**:
    ```json
    {
      "roi": 2.5,
      "token_used": 50000,
      "timestamp": "2026-03-25T23:15:00Z",
      "department": "玛露美妆销售部"
    }
    ```
    
    **功能**:
    - 接收 Agent 系统执行结果的 ROI 和 Token 消耗数据
    - 回传给外部企业管理系统
    - 记录执行指标供分析
    """
    try:
        # 存储回调数据（模拟）
        callback_record = {
            "roi": data.roi,
            "token_used": data.token_used,
            "timestamp": data.timestamp,
            "department": data.department,
            "received_at": datetime.now().isoformat()
        }
        _callback_store.append(callback_record)
        
        # 计算效率指标
        efficiency = data.roi / (data.token_used / 1000) if data.token_used > 0 else 0
        
        # 构建响应
        return CallbackResponse(
            status="received",
            message=f"执行结果已接收 - ROI: {data.roi}x, Token: {data.token_used:,}, 效率: {efficiency:.2f} ROI/1K tokens",
            received_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理回调数据失败: {str(e)}"
        )


@router.get("/budgets")
async def list_budgets():
    """查询所有预算指令（调试用）"""
    return {
        "total": len(_budget_store),
        "budgets": _budget_store
    }


@router.get("/callbacks")
async def list_callbacks():
    """查询所有回调记录（调试用）"""
    return {
        "total": len(_callback_store),
        "callbacks": _callback_store
    }


__all__ = ["router"]
