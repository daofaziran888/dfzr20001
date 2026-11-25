"""萎凋工序领域服务：记录萎凋过程，计算失水率与重量变化，校验上游采摘。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class WitheringService(BaseModuleService):
    MODULE = "withering"
    ENTITY = "萎凋记录"
    OPERATION_TERM = "记录萎凋"
    LIST_FIELDS = ["摊晾厚度", "翻动次数", "失水率", "萎凋时长", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["摊晾厚度", "萎凋时长", "失水率"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录萎凋": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        thickness = store.parse_weight(values.get("摊晾厚度", "0"))
        if thickness <= 0:
            errors.append("摊晾厚度必须大于0")
        water_loss = store.parse_weight(values.get("失水率", "0"))
        if water_loss <= 0 or water_loss > 80:
            errors.append("失水率应在1-80%之间")
        duration = store.parse_weight(values.get("萎凋时长", "0"))
        if duration <= 0:
            errors.append("萎凋时长必须大于0")
        # 上游工序校验
        upstream_module = values.get("上游工序")
        upstream_id = values.get("上游记录ID")
        if upstream_module and upstream_id is not None:
            upstream = store.find(upstream_module, int(upstream_id))
            if upstream is None:
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 不存在")
            elif upstream.get("status") != "已确认":
                errors.append(f"上游记录 {upstream_module}/{upstream_id} 未确认，不能进行萎凋")
        return errors

    def on_confirm(self, entry: dict[str, Any], action: str) -> tuple[bool, str | None]:
        """萎凋确认后计算重量变化。"""
        if action == "记录萎凋":
            batch_no = entry.get("批次号", "")
            if batch_no:
                lineage = store.get_lineage(batch_no)
                for node in lineage:
                    if node["module"] == "picking":
                        picking_data = node.get("data", {})
                        raw_weight = store.parse_weight(picking_data.get("鲜叶重量", 0))
                        loss_rate = store.parse_weight(entry.get("失水率", "0")) / 100.0
                        entry["产出重量"] = round(raw_weight * (1.0 - loss_rate), 3)
                        break
        return True, None

    def calc_weight_after_loss(self, input_weight: float, loss_rate: float) -> float:
        """根据投入重量和失水率计算萎凋后重量。"""
        return round(input_weight * (1.0 - loss_rate / 100.0), 3)

    def get_downstream_steps(self, entry_id: int) -> list[dict[str, Any]]:
        """获取当前萎凋记录后的下游工序（杀青、揉捻、发酵、干燥等）。"""
        batch_no = None
        for row in store.rows(self.MODULE):
            if row["id"] == entry_id:
                batch_no = row.get("批次号")
                break
        if not batch_no:
            return []
        result = []
        lineage = store.get_lineage(batch_no)
        downstream_modules = ["fixing", "rolling", "fermentation", "drying", "grading",
                              "blending", "packing", "trace_code", "shipment"]
        for node in lineage:
            if node["module"] in downstream_modules:
                row = store.find(node["module"], node["entry_id"])
                if row:
                    result.append({"module": node["module"], "entry_id": node["entry_id"],
                                   "status": row.get("status", ""), "data": dict(row)})
        return result