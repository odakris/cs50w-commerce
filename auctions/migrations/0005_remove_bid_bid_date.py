# Generated by Django 4.2.7 on 2023-12-21 14:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0004_rename_starting_bid_auction_bid'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bid',
            name='bid_date',
        ),
    ]
