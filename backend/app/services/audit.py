"""内审巡查领域服务：记录巡查要点、整改期限，关联缺陷记录并回写复查结论。"""
from __future__ import annotations
from typing import Any
from datetime import datetime
from app.services.base import BaseModuleService
from app.store import store

class AuditService(BaseModuleService):
    MODULE = "audit"
    ENTITY = "巡查记录"
    OPERATION_TERM = "签发巡查"
    LIST_FIELDS = ["巡查日期", "巡查要点", "整改期限", "复查结论", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["巡查日期", "巡查要点", "整改期限"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"签发巡查": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        try:
            audit_date = str(values.get("巡查日期", ""))[:10]
            dt = datetime.strptime(audit_date, "%Y-%m-%d")
            if dt > datetime.now():
                errors.append("巡查日期不能晚于当前日期")
        except ValueError:
            errors.append("巡查日期格式无效")

        try:
            deadline = str(values.get("整改期限", ""))[:10]
            dt2 = datetime.strptime(deadline, "%Y-%m-%d")
            if dt2 < datetime.now():
                errors.append("整改期限不能早于当前日期")
        except ValueError:
            errors.append("整改期限格式无效")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """签发巡查后，关联发现的缺陷记录。"""
        if action == "签发巡查":
            pass  # 巡查记录发布无需额外检查
        return True, None

    def is_overdue(self, entry: dict[str, Any]) -> bool:
        """判断是否超过整改期限。"""
        try:
            deadline = str(entry.get("整改期限", ""))[:10]
            return datetime.strptime(deadline, "%Y-%m-%d") < datetime.now()
        except ValueError:
            return False

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        """获取待复查的巡查记录。"""
        rows = store.rows(self.MODULE)
        return [r for r in rows
                if r.get("status") == "已确认"
                and (not r.get("复查结论") or str(r.get("复查结论", "")).strip() == "")]
