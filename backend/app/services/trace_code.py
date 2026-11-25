"""溯源码段领域服务：激活溯源二维码码段，关联批次并校验前置门禁，关联发运单。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class TraceCodeService(BaseModuleService):
    MODULE = "trace_code"
    ENTITY = "码段"
    OPERATION_TERM = "激活码段"
    LIST_FIELDS = ["起始码号", "结束码号", "激活日期", "扫码次数", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["起始码号", "结束码号"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"激活码段": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        start = str(values.get("起始码号", "")).strip()
        end = str(values.get("结束码号", "")).strip()
        if start and end:
            try:
                s_num = int(start.split("-")[-1]) if "-" in start else int(start)
                e_num = int(end.split("-")[-1]) if "-" in end else int(end)
                if s_num >= e_num:
                    errors.append("起始码号必须小于结束码号")
                if e_num - s_num > 100000:
                    errors.append("单次激活码段不得超过100000个码号")
            except (ValueError, IndexError):
                pass

        # 码号范围重叠检查
        existing = store.rows(self.MODULE)
        for r in existing:
            if r.get("id") == values.get("id"):
                continue
            es = str(r.get("起始码号", ""))
            ee = str(r.get("结束码号", ""))
            if es and ee and start and end:
                try:
                    es_n = int(es.split("-")[-1]) if "-" in es else int(es)
                    ee_n = int(ee.split("-")[-1]) if "-" in ee else int(ee)
                    s_n = int(start.split("-")[-1]) if "-" in start else int(start)
                    e_n = int(end.split("-")[-1]) if "-" in end else int(end)
                    if not (e_n < es_n or s_n > ee_n):
                        errors.append(f"码段范围与已有码段 {r['登记编号']} 重叠")
                except (ValueError, IndexError):
                    pass
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """激活码段时检查所有前置门禁条件。"""
        if action == "激活码段":
            # 检查检测报告
            testing_svc = self._get_service("testing")
            if not testing_svc.has_valid_report():
                return False, "缺少已签收的检测报告，不允许激活溯源码段"

            # 检查认证资质
            from app.services.certification import CertificationService
            cert_svc = CertificationService()
            if not cert_svc.has_valid_certification():
                return False, "缺少有效期内的认证资质证书，不允许激活溯源码段"

            # 检查拼配确认
            batch_no = entry.get("批次号", "")
            if batch_no:
                lineage = store.get_batch_lineage_nodes(batch_no)
                has_blending = any(n["module"] == "blending" for n in lineage)
                if has_blending:
                    for n in lineage:
                        if n["module"] == "blending":
                            blend = store.find("blending", n["entry_id"])
                            if blend and blend.get("status") != "已确认":
                                return False, "该批次的拼配配方尚未确认，不能激活溯源码段"
        return True, None

    def _get_service(self, name: str):
        from app.services import service_for
        return service_for(name)

    def get_active_codes(self) -> list[dict[str, Any]]:
        """获取已激活的溯源码段。"""
        return [r for r in store.rows(self.MODULE) if r.get("status") == "已确认"]

    def assign_to_shipment(self, code_entry_id: int, shipment_entry_id: int) -> tuple[bool, str]:
        """将溯源码段分配到发运单。"""
        code_entry = store.find(self.MODULE, code_entry_id)
        if code_entry is None:
            return False, f"溯源码段 {code_entry_id} 不存在"
        if code_entry.get("status") != "已确认":
            return False, f"溯源码段 {code_entry_id} 未激活"

        shipment_entry = store.find("shipment", shipment_entry_id)
        if shipment_entry is None:
            return False, f"发运单 {shipment_entry_id} 不存在"

        code_entry["shipment_id"] = shipment_entry_id
        code_entry["shipment_no"] = shipment_entry.get("登记编号", str(shipment_entry_id))
        store.log_event(self.MODULE, code_entry_id, "assign_to_shipment",
                        {"shipment_id": shipment_entry_id})
        return True, f"溯源码段 {code_entry_id} 已关联到发运单 {shipment_entry_id}"

    def get_codes_by_shipment(self, shipment_entry_id: int) -> list[dict[str, Any]]:
        """获取关联到指定发运单的溯源码段。"""
        rows = store.rows(self.MODULE)
        return [r for r in rows if r.get("shipment_id") == shipment_entry_id]