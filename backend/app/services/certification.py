"""认证资质领域服务：管理资质证书有效期、续期提醒与门禁校验。"""
from __future__ import annotations
from typing import Any
from datetime import datetime
from app.services.base import BaseModuleService
from app.store import store

class CertificationService(BaseModuleService):
    MODULE = "certification"
    ENTITY = "资质证书"
    OPERATION_TERM = "更新资质"
    LIST_FIELDS = ["证书类型", "发证机构", "有效期至", "证书编号", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["证书类型", "发证机构", "有效期至", "证书编号"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"更新资质": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    VALID_CERT_TYPES = ["有机认证", "绿色食品", "地理标志", "ISO9001", "HACCP", "SC生产许可"]

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        cert_type = values.get("证书类型", "")
        if cert_type not in self.VALID_CERT_TYPES:
            pass  # 允许自定义类型
        expiry = str(values.get("有效期至", ""))[:10]
        try:
            dt = datetime.strptime(expiry, "%Y-%m-%d")
            if dt < datetime.now():
                errors.append("证书已过期，请核实有效期")
        except ValueError:
            errors.append("有效期至格式无效，请使用YYYY-MM-DD格式")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """更新资质时，检查是否有关联的过期证书需要替换。"""
        if action == "更新资质":
            cert_type = entry.get("证书类型", "")
            existing = [r for r in store.rows(self.MODULE)
                        if r.get("证书类型") == cert_type
                        and r.get("status") == "已确认"
                        and r.get("id") != entry.get("id")]
            if existing:
                # 保留旧证书记录，新资质独立使用
                pass
        return True, None

    def has_valid_certification(self) -> bool:
        """是否有有效期内的已确认资质证书。"""
        rows = store.rows(self.MODULE)
        for r in rows:
            if r.get("status") == "已确认":
                try:
                    expiry = str(r.get("有效期至", ""))[:10]
                    dt = datetime.strptime(expiry, "%Y-%m-%d")
                    if dt >= datetime.now():
                        return True
                except ValueError:
                    continue
        return False

    def get_valid_certs(self) -> list[dict[str, Any]]:
        """获取所有有效期内的已确认资质证书。"""
        rows = store.rows(self.MODULE)
        valid = []
        for r in rows:
            if r.get("status") == "已确认":
                try:
                    expiry = str(r.get("有效期至", ""))[:10]
                    dt = datetime.strptime(expiry, "%Y-%m-%d")
                    if dt >= datetime.now():
                        valid.append(r)
                except ValueError:
                    continue
        return valid

    def get_certs_about_to_expire(self, days: int = 30) -> list[dict[str, Any]]:
        """获取即将到期的资质证书。"""
        from datetime import timedelta
        rows = store.rows(self.MODULE)
        today = datetime.now()
        threshold = today + timedelta(days=days)
        expiring = []
        for r in rows:
            if r.get("status") == "已确认":
                try:
                    expiry = str(r.get("有效期至", ""))[:10]
                    dt = datetime.strptime(expiry, "%Y-%m-%d")
                    if today <= dt <= threshold:
                        expiring.append(r)
                except ValueError:
                    continue
        return expiring