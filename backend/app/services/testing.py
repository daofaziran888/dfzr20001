"""检测报告领域服务：签收检测报告，作为后续工序推进门禁。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class TestingService(BaseModuleService):
    MODULE = "testing"
    ENTITY = "检测报告"
    OPERATION_TERM = "签收报告"
    LIST_FIELDS = ["农残项目", "检测机构", "报告编号", "签发日期", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["农残项目", "检测机构", "报告编号", "签发日期"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"签收报告": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        report_no = values.get("报告编号", "")
        existing = [r for r in store.rows(self.MODULE)
                    if r.get("报告编号") == report_no and r.get("id") != int(values.get("id", -1))]
        if existing:
            errors.append(f"报告编号 {report_no} 已存在，请勿重复录入")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """签收报告后，关联到相关批次。"""
        if action == "签收报告":
            try:
                from datetime import datetime
                issue_date = str(entry.get("签发日期", ""))[:10]
                dt = datetime.strptime(issue_date, "%Y-%m-%d")
                if dt > datetime.now():
                    return False, "签发日期不能晚于当前日期"
            except ValueError:
                pass
        return True, None

    def has_valid_report(self) -> bool:
        """是否有已签收的有效检测报告。"""
        rows = store.rows(self.MODULE)
        return any(r.get("status") == "已确认" for r in rows)

    def get_confirmed_reports(self) -> list[dict[str, Any]]:
        """获取所有已签收的检测报告。"""
        return [r for r in store.rows(self.MODULE) if r.get("status") == "已确认"]
