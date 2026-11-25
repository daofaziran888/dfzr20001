"""拼配配方领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BlendingService(BaseModuleService):
    MODULE = "blending"
    ENTITY = "拼配批次"
    OPERATION_TERM = "确认配方"
    LIST_FIELDS = ["原料比例", "拼配日期", "口感评分", "香气描述", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["原料比例", "拼配日期", "口感评分"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认配方": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
