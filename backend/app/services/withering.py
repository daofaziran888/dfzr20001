"""萎凋工序领域服务：记录萎凋过程，计算失水率与重量变化。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class WitheringService(BaseModuleService):
    MODULE = "withering"
    ENTITY = "萎凋记录"
    OPERATION_TERM = "记录萎凋"
    LIST_FIELDS = ["摊晾厚度", "翻动次数", "失水率", "萎凋时长", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["摊晾厚度", "萎凋时长", "失水率"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录萎凋": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        thickness = store.parse_weight(values.get("摊晾厚度", "0"))
        if thickness <= 0:
            errors.append("摊晾厚度必须大于0")
        water_loss = store.parse_weight(values.get("失水率", "0"))
        if water_loss <= 0 or water_loss > 80:
            errors.append("失水率应在1-80%之间")
        duration = store.parse_weight(values.get("萎凋时长", "0"))
        if duration <= 0:
            errors.append("萎凋时长必须大于0")
        return errors

    def calc_weight_after_loss(self, input_weight: float, loss_rate: float) -> float:
        """根据投入重量和失水率计算萎凋后重量。"""
        return round(input_weight * (1.0 - loss_rate / 100.0), 3)
