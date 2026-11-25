"""干燥工序领域服务：控制干燥温度曲线，监控含水率达标。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class DryingService(BaseModuleService):
    MODULE = "drying"
    ENTITY = "干燥记录"
    OPERATION_TERM = "记录干燥"
    LIST_FIELDS = ["起始温度", "终止温度", "干燥时长", "含水率", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["起始温度", "终止温度", "干燥时长", "含水率"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录干燥": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        start_temp = store.parse_weight(values.get("起始温度", "0"))
        end_temp = store.parse_weight(values.get("终止温度", "0"))
        if start_temp <= 0 or end_temp <= 0:
            errors.append("干燥温度必须大于0")
        if start_temp > end_temp:
            errors.append("起始温度不应高于终止温度")
        moisture = store.parse_weight(values.get("含水率", "0"))
        if moisture <= 0:
            errors.append("必须记录含水率")
        elif moisture > 7:
            pass  # 记录但放行，不同茶类要求不同
        return errors

    def is_moisture_standard(self, moisture: float, tea_type: str = "绿茶") -> bool:
        """检查含水率是否达标（绿茶标准≤7%，红茶≤6%，乌龙茶≤5%）。"""
        standards = {"绿茶": 7.0, "红茶": 6.0, "乌龙茶": 5.0}
        return moisture <= standards.get(tea_type, 7.0)
