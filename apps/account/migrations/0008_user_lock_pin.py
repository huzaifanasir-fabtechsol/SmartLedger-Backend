from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0007_letterhead'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='lock_pin',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
