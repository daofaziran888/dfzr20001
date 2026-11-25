"""仓储养护领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class StorageService(BaseModuleService):
    MODULE = "storage"
    ENTITY = "养护记录"
    OPERATION_TERM = "记录养护"
    LIST_FIELDS = ["入库温度", "入库湿度", "陈化周期", "翻仓日期", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["入库温度", "入库湿度", "陈化周期"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录养护": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
