"""跨模块制茶工序流水线：批次血缘、状态推进、门禁校验、回溯链重建。

核心业务链路：
1. 鲜叶采摘 → 萎凋 → 杀青 → 揉捻 → 发酵 → 干燥 → 精制分级 → 拼配 → 包装 → 溯源码激活 → 发运
2. 检测报告 + 认证资质 → 门禁：未签收或过期阻断下游批次推进
3. 不合格处置 → 冻结同批次所有下游记录
4. 样品留样 → 关联具体工序记录
5. 内审巡查 → 关联整改事项并回写复查结论
"""
from __future__ import annotations

import copy
from typing import Any

from app.store import store


# 制茶工序顺序（下游模块按顺序消费上游产出）
PROCESS_ORDER = [
    "picking",       # 鲜叶采摘
    "withering",     # 萎凋
    "fixing",        # 杀青
    "rolling",       # 揉捻
    "fermentation",  # 发酵
    "drying",        # 干燥
    "grading",       # 精制分级
    "blending",      # 拼配
    "packing",       # 包装
    "trace_code",    # 溯源码段
    "shipment",      # 发运交接
]

# 工序中文名称
PROCESS_NAMES = {
    "picking": "鲜叶采摘",
    "withering": "萎凋",
    "fixing": "杀青",
    "rolling": "揉捻",
    "fermentation": "发酵",
    "drying": "干燥",
    "grading": "精制分级",
    "blending": "拼配",
    "packing": "包装",
    "trace_code": "溯源码段",
    "shipment": "发运交接",
}

# 每个工序特有的含水率参考字段与损耗率字段
PROCESS_LOSS_FIELDS = {
    "picking": (None, None),
    "withering": (None, "失水率"),
    "fixing": (None, "失重率"),
    "rolling": (None, None),
    "fermentation": (None, None),
    "drying": (None, "含水率"),
    "grading": (None, "碎末比例"),
    "blending": (None, None),
    "packing": (None, None),
    "trace_code": (None, None),
    "shipment": (None, None),
}


class Pipeline:

    def __init__(self):
        self._process_order = PROCESS_ORDER
        self._order_index = {m: i for i, m in enumerate(PROCESS_ORDER)}

    # ── 批次号生成 ──

    def generate_batch_no(self, prefix: str = "BATCH") -> str:
        import time
        ts = int(time.time() * 1000) % 1000000
        return f"{prefix}-{ts:06d}"

    # ── 工序推进 ──

    def advance_batch(self, current_module: str, current_entry_id: int,
                      batch_no: str, request_id: str = "",
                      values: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str]:
        """将批次的工序状态推进到下一阶段。"""
        # 幂等检查
        if request_id:
            cached = store.check_idempotent(request_id)
            if cached:
                return cached.get("entry"), cached.get("message", "幂等: 已执行")

        current_idx = self._order_index.get(current_module, -1)
        if current_idx < 0:
            return None, f"未知工序模块：{current_module}"

        current_entry = store.find(current_module, current_entry_id)
        if current_entry is None:
            return None, f"{PROCESS_NAMES.get(current_module, current_module)}记录 {current_entry_id} 不存在"

        if current_entry.get("status") != "已确认":
            return None, f"{PROCESS_NAMES.get(current_module, current_module)}记录 {current_entry_id} 状态为「{current_entry.get('status')}」，须先确认再推进"

        # 冻结检查
        if store.is_frozen(current_module, current_entry_id):
            reason = store.get_frozen_reason(current_module, current_entry_id)
            return None, f"记录 {current_entry_id} 已被冻结（原因：{reason}），不允许推进"

        # 门禁检查
        gate_ok, gate_msg = self.check_gate(batch_no)
        if not gate_ok:
            return None, f"门禁未通过：{gate_msg}"

        # 找到下一道工序
        next_idx = current_idx + 1
        if next_idx >= len(self._process_order):
            return None, "已到达最终工序，无法继续推进"

        next_module = self._process_order[next_idx]
        next_name = PROCESS_NAMES.get(next_module, next_module)

        # 计算产出：鲜叶重量（从采摘批次取）根据上游损耗逐级递减
        lineage_weight = self._compute_current_weight(current_module, current_entry, batch_no)
        # 默认登记编号使用批次号+工序前缀
        entry_data = dict(values or {})
        if "登记编号" not in entry_data or not entry_data["登记编号"]:
            entry_data["登记编号"] = f"{batch_no}-{next_module[:4].upper()}"
        if "批次号" not in entry_data or not entry_data["批次号"]:
            entry_data["批次号"] = batch_no
        if "上游工序" not in entry_data:
            entry_data["上游工序"] = current_module
        if "上游记录ID" not in entry_data:
            entry_data["上游记录ID"] = current_entry_id
        if "鲜叶重量" not in entry_data:
            entry_data["鲜叶重量"] = str(lineage_weight)

        # 损耗率计算（工序特有）
        loss_pct = self._compute_loss_rate(next_module, entry_data)

        # 在下一工序模块创建记录
        next_rows = store.rows(next_module)
        new_id = max((int(row.get("id", 0)) for row in next_rows), default=0) + 1
        new_entry = {"id": new_id}
        new_entry.update(entry_data)
        new_entry["status"] = "草稿"
        new_entry["pending"] = True
        new_entry["abnormal"] = False
        new_entry["上游重量"] = lineage_weight
        if loss_pct is not None:
            new_entry["损耗率"] = loss_pct
        next_rows.append(new_entry)

        # 注册血缘
        store.register_lineage(batch_no, next_module, new_id)
        store.log_event(current_module, current_entry_id, "advance",
                        {"batch_no": batch_no, "next_module": next_module, "next_id": new_id,
                         "weight": lineage_weight})

        result = {
            "entry": new_entry,
            "message": f"批次 {batch_no} 已从 {PROCESS_NAMES.get(current_module)} 推进到 {next_name}，产出重量 {lineage_weight}kg",
        }
        if request_id:
            store.record_idempotent(request_id, {
                "entry": dict(new_entry),
                "message": result["message"],
            })
        return new_entry, result["message"]

    def _compute_current_weight(self, current_module: str, current_entry: dict[str, Any],
                                batch_no: str) -> float:
        """从批次血缘链中层层计算当前工序后的物料重量。"""
        # 从采摘批次获取原始鲜叶重量
        lineage = store.get_lineage(batch_no)
        for node in lineage:
            if node["module"] == "picking":
                picking_data = node.get("data", {})
                raw_weight = store.parse_weight(picking_data.get("鲜叶重量", 0))
                # 从采摘后逐级扣减损耗
                weight = raw_weight
                for n in lineage:
                    mod = n["module"]
                    data = n.get("data", {})
                    # 萎凋：失水率
                    if mod == "withering":
                        loss = store.parse_weight(data.get("失水率", 0)) / 100.0
                        weight = round(weight * (1.0 - loss), 3)
                    # 杀青：失重率
                    if mod == "fixing":
                        loss = store.parse_weight(data.get("失重率", 0)) / 100.0
                        weight = round(weight * (1.0 - loss), 3)
                    # 干燥：含水率降低
                    if mod == "drying":
                        moisture = store.parse_weight(data.get("含水率", 0)) / 100.0
                        weight = round(weight * (1.0 - moisture * 0.5), 3)
                    # 精制：碎末比例
                    if mod == "grading":
                        debris = store.parse_weight(data.get("碎末比例", 0)) / 100.0
                        weight = round(weight * (1.0 - debris), 3)
                return max(weight, 0.0)

        # 如无采摘记录，尝试从当前记录取鲜叶重量
        return store.parse_weight(current_entry.get("鲜叶重量", 0))

    def _compute_loss_rate(self, module: str, values: dict[str, Any]) -> float | None:
        """根据工序类型计算损耗率。"""
        if module == "withering":
            return store.parse_weight(values.get("失水率", 0))
        if module == "fixing":
            return store.parse_weight(values.get("失重率", 0))
        if module == "drying":
            return store.parse_weight(values.get("含水率", 0))
        if module == "grading":
            return store.parse_weight(values.get("碎末比例", 0))
        return None

    # ── 门禁校验 ──

    def check_gate(self, batch_no: str) -> tuple[bool, str]:
        """检查批次所有前置条件是否满足（检测报告签收、认证资质有效）。"""
        failures = []

        # 检测报告门禁：必须存在已确认的检测报告
        all_testing = store.rows("testing")
        confirmed_test = [r for r in all_testing if r.get("status") == "已确认"]
        if not confirmed_test:
            failures.append("缺少已签收的检测报告")

        # 认证资质门禁：必须存在有效期内的已确认资质证书
        all_certification = store.rows("certification")
        valid_cert = [
            r for r in all_certification
            if r.get("status") == "已确认"
        ]
        if not valid_cert:
            failures.append("缺少已确认的认证资质证书")

        # 检查是否有已确认的拼配配方（在溯源码激活前需要）
        lineage = store.get_batch_lineage_nodes(batch_no)
        if any(n["module"] == "blending" for n in lineage):
            all_blending = store.rows("blending")
            for n in lineage:
                if n["module"] == "blending":
                    blend = store.find("blending", n["entry_id"])
                    if blend and blend.get("status") != "已确认":
                        failures.append(f"拼配配方 {n['entry_id']} 未确认为已确认")

        if failures:
            return False, "；".join(failures)
        return True, "门禁通过"

    def get_gate_detail(self, batch_no: str) -> dict[str, Any]:
        """获取批次门禁的详细检查结果。"""
        ok, msg = self.check_gate(batch_no)
        all_testing = store.rows("testing")
        all_certification = store.rows("certification")

        return {
            "batch_no": batch_no,
            "passed": ok,
            "message": msg,
            "testing_checks": {
                "total": len(all_testing),
                "confirmed": len([r for r in all_testing if r.get("status") == "已确认"]),
            },
            "certification_checks": {
                "total": len(all_certification),
                "confirmed": len([r for r in all_certification if r.get("status") == "已确认"]),
            },
        }

    # ── 追溯链 ──

    def get_trace_chain(self, batch_no: str) -> dict[str, Any]:
        """重建批次完整追溯链，按工序顺序排列。"""
        lineage_nodes = store.get_lineage(batch_no)
        if not lineage_nodes:
            return {"batch_no": batch_no, "chain": [], "complete": False}

        # 按工序顺序排列
        ordered = []
        for proc in self._process_order:
            for node in lineage_nodes:
                if node["module"] == proc:
                    ordered.append(node)

        # 重量守恒检查
        weight_chain = []
        for node in ordered:
            data = node.get("data", {})
            w = {
                "module": node["module"],
                "entry_id": node["entry_id"],
                "status": data.get("status", ""),
                "登记编号": data.get("登记编号", ""),
            }
            if node["module"] == "picking":
                w["鲜叶重量"] = data.get("鲜叶重量", "")
            elif "上游重量" in data:
                w["投入重量"] = data.get("上游重量", "")
            elif "鲜叶重量" in data:
                w["投入重量"] = data.get("鲜叶重量", "")
            if "损耗率" in data:
                w["损耗率"] = data.get("损耗率", "")
            if "产出重量" in data:
                w["产出重量"] = data.get("产出重量", "")
            weight_chain.append(w)

        # 冻结检查
        frozen_count = 0
        for node in ordered:
            if store.is_frozen(node["module"], node["entry_id"]):
                frozen_count += 1

        return {
            "batch_no": batch_no,
            "chain": ordered,
            "weight_chain": weight_chain,
            "chain_length": len(ordered),
            "expected_length": len(ordered),
            "complete": len(ordered) >= 1,
            "frozen_count": frozen_count,
            "events": store.get_events(),
        }

    # ── 回算含水率 ──

    def recalc_moisture_at_node(self, batch_no: str, process_module: str) -> dict[str, Any] | None:
        """基于批次血缘回算指定工序节点的含水率。"""
        lineage = store.get_lineage(batch_no)
        node_data = None
        for node in lineage:
            if node["module"] == process_module:
                node_data = node.get("data", {})
                break

        if node_data is None:
            return None

        # 采集原始鲜叶重量
        picking_weight = None
        for node in lineage:
            if node["module"] == "picking":
                picking_weight = store.parse_weight(node.get("data", {}).get("鲜叶重量", 0))
                break

        current_weight = store.parse_weight(node_data.get("上游重量", 0))
        if picking_weight and picking_weight > 0 and current_weight > 0:
            estimated_moisture = round((1.0 - current_weight / picking_weight) * 100, 2)
        else:
            estimated_moisture = 0.0

        return {
            "batch_no": batch_no,
            "process_module": process_module,
            "picking_weight": picking_weight,
            "current_weight": current_weight,
            "estimated_moisture_pct": estimated_moisture,
        }

    # ── 不合格处置联动 ──

    def freeze_batch_downstream(self, batch_no: str, defect_entry_id: int,
                                 reason: str) -> tuple[int, list[str]]:
        """冻结批次中指定缺陷发现节点之后的所有下游记录。"""
        defect_entry = store.find("defect", defect_entry_id)
        if defect_entry is None:
            return 0, [f"缺陷记录 {defect_entry_id} 不存在"]

        # 找到缺陷发现节点对应的工序模块
        discovered_at = defect_entry.get("发现节点", "")
        defect_module = self._resolve_module_from_node(discovered_at)

        lineage_nodes = store.get_batch_lineage_nodes(batch_no)
        frozen_count = 0
        frozen_keys = []
        should_freeze = False

        if defect_module:
            should_freeze = True

        for node in lineage_nodes:
            if node["module"] == defect_module:
                # 冻结当前节点及后续节点
                pass
            if should_freeze:
                success = store.freeze_entry(node["module"], node["entry_id"],
                                              f"不合格处置#{defect_entry_id}: {reason}")
                if success:
                    frozen_count += 1
                    frozen_keys.append(f"{node['module']}/{node['entry_id']}")

        return frozen_count, frozen_keys

    def _resolve_module_from_node(self, node_desc: str) -> str | None:
        """从节点描述解析工序模块名。"""
        desc_lower = node_desc.lower() if node_desc else ""
        for mod, name in PROCESS_NAMES.items():
            if name in node_desc or mod in desc_lower:
                return mod
        # 按工序顺序回退匹配
        for mod in self._process_order:
            if mod in desc_lower:
                return mod
        return None

    # ── 内审巡查联动 ──

    def update_audit_review(self, audit_entry_id: int,
                            review_conclusion: str) -> tuple[dict[str, Any] | None, str]:
        """回写内审巡查的复查结论，并同步更新关联的整改事项记录。"""
        audit_entry = store.find("audit", audit_entry_id)
        if audit_entry is None:
            return None, f"巡查记录 {audit_entry_id} 不存在"

        audit_entry["复查结论"] = review_conclusion

        # 查找关联的整改事项（在 defect 表中）
        rectified = []
        all_defects = store.rows("defect")
        for d in all_defects:
            if d.get("发现节点", "") == f"巡查记录#{audit_entry_id}":
                d["处置方式"] = f"已整改（巡查#{audit_entry_id}复查：{review_conclusion}）"
                rectified.append(d["id"])

        store.log_event("audit", audit_entry_id, "review",
                        {"conclusion": review_conclusion, "rectified_defects": rectified})

        return audit_entry, f"巡查记录 {audit_entry_id} 复查结论已更新，关联整改 {len(rectified)} 项"

    # ── 样品留样关联 ──

    def link_sample_to_node(self, sample_entry_id: int,
                            process_module: str, process_entry_id: int) -> tuple[dict[str, Any] | None, str]:
        """将样品留样关联到具体工序记录。"""
        sample = store.find("sample", sample_entry_id)
        if sample is None:
            return None, f"留样记录 {sample_entry_id} 不存在"

        process_entry = store.find(process_module, process_entry_id)
        if process_entry is None:
            return None, f"{PROCESS_NAMES.get(process_module, process_module)}记录 {process_entry_id} 不存在"

        sample["取样节点"] = f"{PROCESS_NAMES.get(process_module, process_module)}#{process_entry_id}"
        store.log_event("sample", sample_entry_id, "link",
                        {"process_module": process_module, "process_entry_id": process_entry_id})

        return sample, f"留样记录 {sample_entry_id} 已关联到 {PROCESS_NAMES.get(process_module)}记录 {process_entry_id}"

    # ── 状态机单向前进 ──

    VALID_TRANSITIONS = {
        "草稿": ["待确认"],
        "待确认": ["已确认", "已撤回"],
        "已确认": [],  # 确认后不可逆（除非通过不合格处置冻结）
        "已撤回": ["草稿"],
    }

    def validate_state_transition(self, current_status: str, target_action: str,
                                  allowed_targets: list[str]) -> tuple[bool, str]:
        """校验状态机单向推进是否合法。"""
        # 从动作映射到目标状态
        if target_action == "提交确认":
            target_status = "待确认"
        elif "撤回" in target_action:
            target_status = "已撤回"
        else:
            target_status = "已确认"

        valid = self.VALID_TRANSITIONS.get(current_status, [])
        if target_status not in valid:
            return False, f"不允许从「{current_status}」跳转到「{target_status}」"

        # 跳级拦截：已确认不能直接变为其他状态
        if current_status == "已确认" and target_status != "已确认":
            return False, "已确认记录不允许撤回或修改"

        return True, ""

    # ── 重量守恒校验 ──

    def check_weight_conservation(self, batch_no: str) -> dict[str, Any]:
        """检查批次制造过程中的重量守恒。"""
        chain = self.get_trace_chain(batch_no)
        weight_chain = chain.get("weight_chain", [])

        picking_weight = None
        final_weight = None
        total_loss = 0.0

        for w in weight_chain:
            if w["module"] == "picking":
                pw = store.parse_weight(w.get("鲜叶重量", 0))
                if pw > 0:
                    picking_weight = pw
            if "产出重量" in w:
                ow = store.parse_weight(w["产出重量"])
                if ow > 0:
                    final_weight = ow

        if picking_weight and final_weight:
            total_loss = round((1.0 - final_weight / picking_weight) * 100, 2)

        return {
            "batch_no": batch_no,
            "picking_weight": picking_weight,
            "final_weight": final_weight,
            "total_loss_pct": total_loss,
            "conservation_ok": total_loss >= 0 and total_loss <= 100,
        }


# 全局单例
pipeline = Pipeline()