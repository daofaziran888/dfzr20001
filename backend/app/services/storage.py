"""仓储养护领域服务：监控入库环境参数，跟踪陈化周期与翻仓计划。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class StorageService(BaseModuleService):
    MODULE = "storage"
    ENTITY = "养护记录"
    OPERATION_TERM = "记录养护"
    LIST_FIELDS = ["入库温度", "入库湿度", "陈化周期", "翻仓日期", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["入库温度", "入库湿度"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录养护": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        temp = store.parse_weight(values.get("入库温度", "0"))
        if temp < -5:
            errors.append("入库温度不宜低于-5℃")
        elif temp > 35:
            errors.append("入库温度不宜高于35℃（需冷藏保管的茶类请使用冷库）")
        humidity = store.parse_weight(values.get("入库湿度", "0"))
        if humidity <= 0 or humidity > 100:
            errors.append("入库湿度应在1-100%之间")
        return errors

    def is_overdue_turning(self, entry: dict[str, Any]) -> bool:
        """判断是否超过翻仓期限。"""
        from datetime import datetime
        turning_date = entry.get("翻仓日期", "")
        if not turning_date:
            return False
        try:
            dt = datetime.strptime(str(turning_date)[:10], "%Y-%m-%d")
            return dt < datetime.now()
        except ValueError:
            return False

    def get_storage_status(self, batch_no: str) -> dict[str, Any] | None:
        """获取指定批次的最新仓储养护状态。"""
        rows = store.rows(self.MODULE)
        batch_rows = [r for r in rows if r.get("批次号") == batch_no]
        return batch_rows[-1] if batch_rows else None
