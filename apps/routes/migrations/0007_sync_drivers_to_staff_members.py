from django.db import migrations

def sync_existing_drivers_to_staff(apps, schema_editor):
    Driver = apps.get_model("routes", "Driver")
    StaffMember = apps.get_model("accounts", "StaffMember")

    for driver in Driver.objects.select_related("user").all():
        if not driver.user:
            continue
        user = driver.user
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        phone = driver.phone_number or getattr(user, "phone_number", "") or ""
        joined_date = user.date_joined.date() if user.date_joined else None

        staff, created = StaffMember.objects.get_or_create(
            user=user,
            defaults={
                "full_name": full_name,
                "phone_number": phone,
                "designation": "Staff Driver",
                "joined_date": joined_date,
                "is_active": driver.is_active,
                "wage_type": "DEFAULT_SLAB",
            }
        )
        if not created:
            if not staff.designation or staff.designation in ["Worker", "Bakery Worker"]:
                staff.designation = "Staff Driver"
                staff.save()

def reverse_sync(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0006_alter_driverexpense_options_and_more'),
        ('accounts', '0003_staffmember_staffpayout_staffattendance'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='driver',
            options={'ordering': ['user__first_name', 'user__username'], 'verbose_name': 'Staff Driver Profile', 'verbose_name_plural': 'Staff Driver Profiles'},
        ),
        migrations.RunPython(sync_existing_drivers_to_staff, reverse_sync),
    ]
