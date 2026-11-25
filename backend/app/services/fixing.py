"""杀青工序领域服务：记录杀青参数，校验锅温与投叶量范围。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class FixingService(BaseModuleService):
    MODULE = "fixing"
    ENTITY = "杀青记录"
    OPERATION_TERM = "记录杀青"
    LIST_FIELDS = ["锅温设定", "杀青时长", "投叶量", "失重率", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["锅温设定", "杀青时长", "投叶量"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录杀青": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        temp = store.parse_weight(values.get("锅温设定", "0"))
        if temp < 180:
            errors.append("锅温设定不得低于180℃")
        elif temp > 350:
            errors.append("锅温设定不得高于350℃")
        leaf_weight = store.parse_weight(values.get("投叶量", "0"))
        if leaf_weight <= 0:
            errors.append("投叶量必须大于0")
        weight_loss = store.parse_weight(values.get("失重率", "0"))
        if weight_loss < 0 or weight_loss > 50:
            errors.append("杀青失重率应在0-50%之间")
        return errors

    def calc_weight_after_fixing(self, input_weight: float, loss_rate: float) -> float:
        """根据投入重量和失重率计算杀青后重量。"""
        return round(input_weight * (1.0 - loss_rate / 100.0), 3)
