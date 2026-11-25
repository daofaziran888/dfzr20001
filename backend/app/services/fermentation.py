"""发酵工序领域服务：监控发酵环境参数，控制堆高与翻堆周期。"""
from __future__ import annotations
from typing import Any
from app.services.base import BaseModuleService
from app.store import store

class FermentationService(BaseModuleService):
    MODULE = "fermentation"
    ENTITY = "发酵记录"
    OPERATION_TERM = "记录发酵"
    LIST_FIELDS = ["环境温度", "环境湿度", "堆高尺寸", "翻堆间隔", "登记编号", "负责人", "生效版本", "备注说明"]
    REQUIRED_FIELDS = ["环境温度", "环境湿度", "堆高尺寸"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"记录发酵": "已确认", "提交确认": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def validate_entry(self, values: dict[str, Any]) -> list[str]:
        errors = []
        temp = store.parse_weight(values.get("环境温度", "0"))
        if temp < 15:
            errors.append("发酵环境温度不宜低于15℃")
        elif temp > 45:
            errors.append("发酵环境温度不宜高于45℃")
        humidity = store.parse_weight(values.get("环境湿度", "0"))
        if humidity < 60:
            errors.append("发酵环境湿度不宜低于60%")
        elif humidity > 98:
            errors.append("发酵环境湿度不宜高于98%")
        heap = store.parse_weight(values.get("堆高尺寸", "0"))
        if heap <= 0:
            errors.append("堆高尺寸必须大于0")
        return errors

    def is_fermentation_normal(self, temp: float, humidity: float) -> bool:
        """判断发酵条件是否正常。"""
        return 22 <= temp <= 35 and 75 <= humidity <= 95
