"""鲜叶采摘领域服务：登记采摘批次、关联茶园地块、计算采摘效率。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class PickingService(BaseModuleService):
    MODULE = "picking"
    ENTITY = "采摘批次"
    OPERATION_TERM = "登记批次"
    LIST_FIELDS = ["采摘日期", "采摘人员", "芽叶标准", "鲜叶重量", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["采摘日期", "采摘人员", "芽叶标准", "鲜叶重量"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"登记批次": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        weight = store.parse_weight(values.get("鲜叶重量", "0"))
        if weight <= 0:
            errors.append("鲜叶重量必须大于0")
        elif weight > 5000:
            errors.append("单批鲜叶重量不得超过5000kg")
        bud_spec = values.get("芽叶标准", "")
        valid_specs = ["单芽", "一芽一叶", "一芽二叶", "一芽三叶", "对夹叶"]
        if bud_spec and bud_spec not in valid_specs:
            pass  # 允许自定义标准
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """采摘批次确认时，校验是否有关联的已确认茶园地块。"""
        if action == "登记批次":
            gardens = store.rows("tea_garden")
            confirmed_gardens = [g for g in gardens if g.get("status") == "已确认"]
            if not confirmed_gardens:
                return False, "没有已认证的茶园地块，请先认证地块后再登记采摘批次"
        return True, None

    def get_picking_by_date(self, date_str: str) -> list[dict[str, Any]]:
        """按日期获取采摘批次。"""
        rows = store.rows(self.MODULE)
        return [r for r in rows if str(r.get("采摘日期", "")) == date_str and r.get("status") == "已确认"]
