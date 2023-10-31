from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """自定义Model基类:补充基础字段"""

    part_number = models.CharField(primary_key=True, max_length=255, verbose_name="产品编号")
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


class SynnexGood(BaseModel):
    mfr = models.CharField(max_length=255, default="", verbose_name="Mfr")  # 厂家名称
    mfr_p_n = models.CharField(max_length=255, default="", verbose_name="Mfr.P/N")  # 产品编号 等价于part_number
    # sku = models.CharField(max_length=255, default="", verbose_name="SKU")
    # td_snx = models.CharField(max_length=255, default="", verbose_name="TD SNX#")
    msrp = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="MSRP")  # 建议零售价
    federal_govt_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="联邦政府价格")
    status = models.BooleanField(null=True, default=None, verbose_name="状态")  # True产品存在、False产品不存在、None未爬


class GSAGood(BaseModel):
    # 列表页
    mfr_part_number = models.CharField(max_length=255, default="", verbose_name="mfrPartNumber")  # 产品编号 等价于part_number
    product_name = models.CharField(max_length=255, default="", verbose_name="itemName")  # 产品名称
    mfr = models.CharField(max_length=255, default="", verbose_name="Mfr")  # 厂家名称
    source = models.IntegerField(default=0, verbose_name="source")
    url = models.CharField(max_length=255, default="", verbose_name="url")
    # 详情页
    mas_sin = models.CharField(max_length=255, default="", verbose_name="MAS Schedule/SIN")  # 33411
    coo = models.CharField(max_length=255, default="", verbose_name="原产地")
    description = models.CharField(max_length=2047, default="", verbose_name="产品描述")
    gsa_price_1 = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="GSA优势价格1")
    gsa_price_2 = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="GSA优势价格2")
    gsa_price_3 = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="GSA优势价格3")


class IngramGood(BaseModel):
    vpn = models.CharField(max_length=255, default="", verbose_name="VPN")  # 等价于part_number
    # sku = models.CharField(max_length=255, default="", verbose_name="SKU")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="price")  # 价格 无效则是Not Available
    status = models.BooleanField(null=True, default=None, verbose_name="状态")  # True产品存在、False产品不存在、None未爬
