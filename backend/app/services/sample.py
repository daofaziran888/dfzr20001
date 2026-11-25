"""样品留样领域服务：登记留样记录，关联具体工序节点，跟踪保存期限。"""
from __future__ import annotations
from typing import Any
from datetime import datetime
from app.services.base import BaseModuleService
from app.store import store

class SampleService(BaseModuleService):
    MODULE = "sample"
    ENTITY = "留样记录"
    OPERATION_TERM = "登记留样"
    LIST_FIELDS = ["留样编号", "取样节点", "样品形态", "保存期限", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["留样编号", "样品形态", "保存期限"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"登记留样": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        sample_no = str(values.get("留样编号", "")).strip()
        existing = [r for r in store.rows(self.MODULE)
                    if r.get("留样编号") == sample_no]
        if existing:
            errors.append(f"留样编号 {sample_no} 已存在")
        shelf_life = str(values.get("保存期限", ""))[:10]
        try:
            dt = datetime.strptime(shelf_life, "%Y-%m-%d")
            if dt < datetime.now():
                errors.append("保存期限不能早于当前日期")
        except ValueError:
            pass
        return errors

    def is_expired(self, entry: dict[str, Any]) -> bool:
        """判断样品是否超过保存期限。"""
        try:
            shelf_life = str(entry.get("保存期限", ""))[:10]
            return datetime.strptime(shelf_life, "%Y-%m-%d") < datetime.now()
        except ValueError:
            return False

    def get_samples_by_node(self, process_module: str, process_entry_id: int) -> list[dict[str, Any]]:
        """获取关联到指定工序节点的留样记录。"""
        rows = store.rows(self.MODULE)
        node_label = f"{process_module}#{process_entry_id}"
        return [r for r in rows if node_label in str(r.get("取样节点", ""))]
