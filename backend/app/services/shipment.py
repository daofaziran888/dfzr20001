"""发运交接领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ShipmentService(BaseModuleService):
    MODULE = "shipment"
    ENTITY = "发运单"
    OPERATION_TERM = "确认发运"
    LIST_FIELDS = ["收货方", "物流单号", "发运日期", "承运单位", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["收货方", "物流单号", "发运日期"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认发运": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
