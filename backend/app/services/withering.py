"""萎凋工序领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class WitheringService(BaseModuleService):
    MODULE = "withering"
    ENTITY = "萎凋记录"
    OPERATION_TERM = "记录萎凋"
    LIST_FIELDS = ["摊晾厚度", "翻动次数", "失水率", "萎凋时长", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["摊晾厚度", "翻动次数", "失水率"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录萎凋": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []
