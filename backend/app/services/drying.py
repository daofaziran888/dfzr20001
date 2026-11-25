"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DryingService(BaseModuleService):
    MODULE = "drying"
    ENTITY = "干燥记录"
    OPERATION_TERM = "记录干燥"
    LIST_FIELDS = ["起始温度", "终止温度", "干燥时长", "含水率", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["起始温度", "终止温度", "干燥时长"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录干燥": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
