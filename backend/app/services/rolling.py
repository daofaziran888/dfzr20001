"""揉捻工序领域服务：记录揉捻参数，评估成条率与碎茶比例。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class RollingService(BaseModuleService):
    MODULE = "rolling"
    ENTITY = "揉捻记录"
    OPERATION_TERM = "记录揉捻"
    LIST_FIELDS = ["压力档位", "揉捻时长", "成条率", "碎茶比例", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["压力档位", "揉捻时长", "成条率"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录揉捻": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        twig_rate = store.parse_weight(values.get("成条率", "0"))
        if twig_rate <= 0 or twig_rate > 100:
            errors.append("成条率应在1-100%之间")
        debris = store.parse_weight(values.get("碎茶比例", "0"))
        if debris < 0 or debris > 50:
            errors.append("碎茶比例应在0-50%之间")
        return errors

    def evaluate_quality(self, twig_rate: float, debris_rate: float) -> str:
        """根据成条率和碎茶率评估揉捻质量等级。"""
        if twig_rate >= 90 and debris_rate <= 5:
            return "优"
        elif twig_rate >= 75 and debris_rate <= 15:
            return "良"
        else:
            return "需改进"
