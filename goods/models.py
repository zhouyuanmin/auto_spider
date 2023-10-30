from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """自定义Model基类:补充基础字段"""

    create_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    delete_at = models.DateTimeField(null=True, default=None, verbose_name="删除时间")
    refresh_at = models.DateTimeField(default=timezone.now, verbose_name="刷新时间")  # 数据最新采集时间
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="备注")

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.pk)

    def set_delete(self):
        """软删除"""
        self.delete_at = timezone.now()
        self.save()
