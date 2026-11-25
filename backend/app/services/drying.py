"""干燥工序领域服务：控制干燥温度曲线，监控含水率达标，校验上游发酵。"""
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
        # 上游工序校验
        upstream_module = values.get("上游工序")
        upstream_id = values.get("上游记录ID")
        if upstream_module and upstream_id is not None:
            upstream = store.find(upstream_module, int(upstream_id))
            if upstream is None:
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 不存在")
            elif upstream.get("status") != "已确认":
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 未确认，不能进行干燥")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        if action == "记录干燥":
            moisture = store.parse_weight(entry.get("含水率", "0"))
            if not self.is_moisture_standard(moisture):
                entry["moisture_warning"] = "含水率超标，建议复烘"
            upstream_weight = store.parse_weight(entry.get("上游重量", "0"))
            if upstream_weight > 0:
                entry["产出重量"] = round(upstream_weight * (1.0 - moisture / 100.0 * 0.5), 3)
        return True, None

    def is_moisture_standard(self, moisture: float, tea_type: str = "绿茶") -> bool:
        """检查含水率是否达标（绿茶标准≤7%，红茶≤6%，乌龙茶≤5%）。"""
        standards = {"绿茶": 7.0, "红茶": 6.0, "乌龙茶": 5.0}
        return moisture <= standards.get(tea_type, 7.0)

    def get_drying_by_fermentation(self, ferm_entry_id: int) -> list[dict[str, Any]]:
        """获取指定发酵记录之后的干燥记录。"""
        rows = store.rows(self.MODULE)
        return [r for r in rows
                if r.get("上游记录ID") is not None
                and int(r.get("上游记录ID", -1)) == ferm_entry_id
                and r.get("上游工序") == "fermentation"]