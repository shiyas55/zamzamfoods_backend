from django.db import migrations, models

def set_existing_drivers_role_type_staff(apps, schema_editor):
    StaffMember = apps.get_model("accounts", "StaffMember")
    # Set any staff with linked user or driver designation to STAFF
    for staff in StaffMember.objects.all():
        if staff.user or "driver" in (staff.designation or "").lower():
            staff.role_type = "STAFF"
            staff.save()

def reverse_noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_staffmember_staffpayout_staffattendance'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffmember',
            name='role_type',
            field=models.CharField(
                choices=[('STAFF', 'Staff (Driver / Management)'), ('MEMBER', 'Member (Bakery / Worker)')],
                db_index=True,
                default='MEMBER',
                help_text='Role classification: STAFF (Driver / Management) or MEMBER (Bakery Worker)',
                max_length=20,
            ),
        ),
        migrations.RunPython(set_existing_drivers_role_type_staff, reverse_noop),
    ]
