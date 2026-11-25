"""鲜叶采摘领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PickingService(BaseModuleService):
    MODULE = "picking"
    ENTITY = "采摘批次"
    OPERATION_TERM = "登记批次"
    LIST_FIELDS = ["采摘日期", "采摘人员", "芽叶标准", "鲜叶重量", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["采摘日期", "采摘人员", "芽叶标准"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"登记批次": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
