"""揉捻工序领域服务：记录揉捻参数，评估成条率与碎茶比例，校验上游杀青。"""
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
        # 上游工序校验
        upstream_module = values.get("上游工序")
        upstream_id = values.get("上游记录ID")
        if upstream_module and upstream_id is not None:
            upstream = store.find(upstream_module, int(upstream_id))
            if upstream is None:
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 不存在")
            elif upstream.get("status") != "已确认":
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 未确认，不能进行揉捻")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        if action == "记录揉捻":
            batch_no = entry.get("批次号", "")
            if batch_no:
                lineage = store.get_lineage(batch_no)
                weight_from_upstream = store.parse_weight(entry.get("上游重量", "0"))
                if weight_from_upstream > 0:
                    debris = store.parse_weight(entry.get("碎茶比例", "0")) / 100.0
                    entry["产出重量"] = round(weight_from_upstream * (1.0 - debris), 3)
        return True, None

    def evaluate_quality(self, twig_rate: float, debris_rate: float) -> str:
        """根据成条率和碎茶率评估揉捻质量等级。"""
        if twig_rate >= 90 and debris_rate <= 5:
            return "优"
        elif twig_rate >= 75 and debris_rate <= 15:
            return "良"
        else:
            return "需改进"