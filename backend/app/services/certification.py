"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CertificationService(BaseModuleService):
    MODULE = "certification"
    ENTITY = "资质证书"
    OPERATION_TERM = "更新资质"
    LIST_FIELDS = ["证书类型", "发证机构", "有效期至", "证书编号", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["证书类型", "发证机构", "有效期至"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"更新资质": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
