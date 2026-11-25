"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FixingService(BaseModuleService):
    MODULE = "fixing"
    ENTITY = "杀青记录"
    OPERATION_TERM = "记录杀青"
    LIST_FIELDS = ["锅温设定", "杀青时长", "投叶量", "失重率", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["锅温设定", "杀青时长", "投叶量"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录杀青": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
