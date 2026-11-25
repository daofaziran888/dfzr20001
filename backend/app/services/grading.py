"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class GradingService(BaseModuleService):
    MODULE = "grading"
    ENTITY = "分级结果"
    OPERATION_TERM = "确认分级"
    LIST_FIELDS = ["筛号规格", "碎末比例", "等级判定", "评审人员", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["筛号规格", "碎末比例", "等级判定"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认分级": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
