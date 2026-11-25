"""杀青工序领域服务：记录杀青参数，校验锅温与投叶量范围，校验上游萎凋。"""
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
        # 上游工序校验
        upstream_module = values.get("上游工序")
        upstream_id = values.get("上游记录ID")
        if upstream_module and upstream_id is not None:
            upstream = store.find(upstream_module, int(upstream_id))
            if upstream is None:
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 不存在")
            elif upstream.get("status") != "已确认":
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 未确认，不能进行杀青")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """杀青确认后计算重量和产出。"""
        if action == "记录杀青":
            upstream_weight = store.parse_weight(entry.get("上游重量", "0"))
            loss_rate = store.parse_weight(entry.get("失重率", "0")) / 100.0
            if upstream_weight > 0 and loss_rate > 0:
                entry["产出重量"] = round(upstream_weight * (1.0 - loss_rate), 3)
        return True, None

    def calc_weight_after_fixing(self, input_weight: float, loss_rate: float) -> float:
        """根据投入重量和失重率计算杀青后重量。"""
        return round(input_weight * (1.0 - loss_rate / 100.0), 3)

    def get_upstream_withering(self, entry_id: int) -> dict[str, Any] | None:
        """获取杀青记录的上游萎凋记录。"""
        row = store.find(self.MODULE, entry_id)
        if row is None:
            return None
        upstream_module = row.get("上游工序")
        upstream_id = row.get("上游记录ID")
        if upstream_module and upstream_id is not None:
            return store.find(upstream_module, int(upstream_id))
        return None