# Generated by Django 4.2.7 on 2023-12-21 12:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0003_auction_bid_counter'),
    ]

    operations = [
        migrations.RenameField(
            model_name='auction',
            old_name='starting_bid',
            new_name='bid',
        ),
    ]
