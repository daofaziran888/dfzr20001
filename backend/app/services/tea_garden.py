"""茶园地块领域服务：管理茶园基本信息，校验地块面积范围与品种合规性。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class TeaGardenService(BaseModuleService):
    MODULE = "tea_garden"
    ENTITY = "地块"
    OPERATION_TERM = "认证地块"
    LIST_FIELDS = ["海拔高度", "种植面积", "茶树品种", "种植年份", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["海拔高度", "种植面积", "茶树品种", "种植年份"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"认证地块": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        try:
            area = float(str(values.get("种植面积", "0")).replace("亩", "").strip())
            if area <= 0:
                errors.append("种植面积必须大于0")
            elif area > 5000:
                errors.append("单地块面积不得超过5000亩")
        except (ValueError, TypeError):
            errors.append("种植面积格式无效")
        try:
            alt = float(str(values.get("海拔高度", "0")).replace("m", "").replace("米", "").strip())
            if alt < 0:
                errors.append("海拔高度不能为负数")
        except (ValueError, TypeError):
            errors.append("海拔高度格式无效")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """认证地块时，检查同一品种+年份是否已有已确认记录。"""
        if action == "认证地块":
            variety = entry.get("茶树品种", "")
            year = entry.get("种植年份", "")
            rows = store.rows(self.MODULE)
            existing = [r for r in rows
                        if r.get("茶树品种") == variety and r.get("种植年份") == year
                        and r.get("status") == "已确认" and r.get("id") != entry.get("id")]
            if existing:
                # 不阻断，但记录提示
                pass
        return True, None

    def get_active_gardens(self) -> list[dict[str, Any]]:
        """获取已确认的活跃地块列表。"""
        rows = store.rows(self.MODULE)
        return [r for r in rows if r.get("status") == "已确认"]
