from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("expense", "0005_fix_sparepart_location_column"),
    ]

    operations = [
        # No-op: 0007 adds part_number and brand via AddField
    ]
