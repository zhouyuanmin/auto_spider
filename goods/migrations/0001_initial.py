# Generated by Django 3.2.15 on 2023-11-01 11:18

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GSAGood',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('delete_at', models.DateTimeField(default=None, null=True, verbose_name='删除时间')),
                ('refresh_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='刷新时间')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('part_number', models.CharField(max_length=255, verbose_name='产品编号')),
                ('mfr_part_number', models.CharField(default='', max_length=255, verbose_name='mfrPartNumber')),
                ('product_name', models.CharField(default='', max_length=255, verbose_name='itemName')),
                ('mfr', models.CharField(default='', max_length=255, verbose_name='Mfr')),
                ('source', models.IntegerField(default=0, verbose_name='source')),
                ('url', models.CharField(default='', max_length=255, verbose_name='url')),
                ('mas_sin', models.CharField(default='', max_length=255, verbose_name='MAS Schedule/SIN')),
                ('coo', models.CharField(default='', max_length=255, verbose_name='原产地')),
                ('description', models.CharField(default='', max_length=2047, verbose_name='产品描述')),
                ('gsa_price_1', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='GSA优势价格1')),
                ('gsa_price_2', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='GSA优势价格2')),
                ('gsa_price_3', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='GSA优势价格3')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IngramGood',
            fields=[
                ('part_number', models.CharField(max_length=255, primary_key=True, serialize=False, verbose_name='产品编号')),
                ('create_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('delete_at', models.DateTimeField(default=None, null=True, verbose_name='删除时间')),
                ('refresh_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='刷新时间')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('vpn', models.CharField(default='', max_length=255, verbose_name='VPN')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='price')),
                ('status', models.BooleanField(default=None, null=True, verbose_name='状态')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SynnexGood',
            fields=[
                ('part_number', models.CharField(max_length=255, primary_key=True, serialize=False, verbose_name='产品编号')),
                ('create_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('delete_at', models.DateTimeField(default=None, null=True, verbose_name='删除时间')),
                ('refresh_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='刷新时间')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('mfr', models.CharField(default='', max_length=255, verbose_name='Mfr')),
                ('mfr_p_n', models.CharField(default='', max_length=255, verbose_name='Mfr.P/N')),
                ('msrp', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='MSRP')),
                ('federal_govt_price', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='联邦政府价格')),
                ('status', models.BooleanField(default=None, null=True, verbose_name='状态')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
