"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PackingService(BaseModuleService):
    MODULE = "packing"
    ENTITY = "包装批"
    OPERATION_TERM = "确认包装"
    LIST_FIELDS = ["包装形式", "净含量", "标签文案", "封口方式", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["包装形式", "净含量", "标签文案"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认包装": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
