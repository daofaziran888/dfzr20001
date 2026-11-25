"""精制分级领域服务：按筛号规格分选、碎末比例控制、等级判定。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class GradingService(BaseModuleService):
    MODULE = "grading"
    ENTITY = "分级结果"
    OPERATION_TERM = "确认分级"
    LIST_FIELDS = ["筛号规格", "碎末比例", "等级判定", "评审人员", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["筛号规格", "碎末比例", "等级判定", "评审人员"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认分级": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    VALID_GRADES = ["特级", "一级", "二级", "三级", "四级", "等外"]

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        grade = values.get("等级判定", "")
        if grade not in self.VALID_GRADES:
            errors.append(f"等级判定须为{', '.join(self.VALID_GRADES)}之一")
        debris = store.parse_weight(values.get("碎末比例", "100"))
        if debris < 0 or debris > 100:
            errors.append("碎末比例格式无效")
        return errors

    def auto_grade(self, debris_rate: float, sieve: str) -> str:
        """根据碎末率和筛号规格自动判定等级。"""
        if debris_rate <= 2:
            return "特级"
        elif debris_rate <= 5:
            return "一级"
        elif debris_rate <= 10:
            return "二级"
        elif debris_rate <= 20:
            return "三级"
        else:
            return "等外"

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """分级确认后更新批次产出重量。"""
        if action == "确认分级":
            debris = store.parse_weight(entry.get("碎末比例", "0"))
            input_weight = store.parse_weight(entry.get("上游重量", "0"))
            if input_weight > 0:
                entry["产出重量"] = round(input_weight * (1.0 - debris / 100.0), 3)
        return True, None
