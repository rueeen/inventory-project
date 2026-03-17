from decimal import Decimal
from openpyxl import load_workbook

from ..models import Equipment, Supply, StorageLocation, Career, Subject, EquipmentCode


def split_values(text, separator=","):
    if not text:
        return []
    return [item.strip() for item in str(text).split(separator) if item and str(item).strip()]


def split_lines(text):
    if not text:
        return []
    return [item.strip() for item in str(text).splitlines() if item and str(item).strip()]


def import_equipment_excel(file_obj):
    wb = load_workbook(file_obj)
    ws = wb.active

    result = {
        "created": 0,
        "updated": 0,
        "errors": [],
    }

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        try:
            inventory_codes = row[0]
            name = row[1]
            detailed_spec = row[2]
            careers_text = row[3]
            subjects_text = row[4]
            location_name = row[5]
            total_existing = row[6] or 0
            quantity_needed = row[7] or 0
            good_count = row[9] or 0
            repairable_count = row[10] or 0
            bad_count = row[11] or 0
            unit_value_uf = row[12]
            observations = row[14] or ""

            if not name:
                continue

            location, _ = StorageLocation.objects.get_or_create(
                name=str(location_name).strip() if location_name else "Sin ubicación"
            )

            equipment, created = Equipment.objects.update_or_create(
                name=str(name).strip(),
                storage_location=location,
                defaults={
                    "detailed_spec": str(detailed_spec).strip() if detailed_spec else "",
                    "total_existing": int(total_existing),
                    "quantity_needed": int(quantity_needed),
                    "good_count": int(good_count),
                    "repairable_count": int(repairable_count),
                    "bad_count": int(bad_count),
                    "unit_value_uf": Decimal(str(unit_value_uf)) if unit_value_uf not in (None, "") else None,
                    "observations": str(observations).strip(),
                }
            )

            if created:
                result["created"] += 1
            else:
                result["updated"] += 1

            career_names = split_values(careers_text)
            equipment.careers.clear()
            for career_name in career_names:
                career, _ = Career.objects.get_or_create(name=career_name)
                equipment.careers.add(career)

            subject_codes = split_values(subjects_text)
            equipment.subjects.clear()
            for subject_code in subject_codes:
                subject, _ = Subject.objects.get_or_create(
                    code=subject_code,
                    defaults={"name": ""}
                )
                equipment.subjects.add(subject)

            codes = split_lines(inventory_codes)
            existing_codes = set(equipment.codes.values_list("code", flat=True))
            for code in codes:
                if code not in existing_codes:
                    EquipmentCode.objects.get_or_create(
                        equipment=equipment,
                        code=code,
                        defaults={"code_type": "inventory"}
                    )

        except Exception as e:
            result["errors"].append(f"Fila {row_num}: {str(e)}")

    return result


def import_supply_excel(file_obj):
    wb = load_workbook(file_obj)
    ws = wb.active

    result = {
        "created": 0,
        "updated": 0,
        "errors": [],
    }

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        try:
            name = row[0]
            detailed_spec = row[1]
            location_name = row[2]
            total_existing = row[3] or 0
            observations = row[4] or ""

            if not name:
                continue

            location, _ = StorageLocation.objects.get_or_create(
                name=str(location_name).strip() if location_name else "Sin ubicación"
            )

            _, created = Supply.objects.update_or_create(
                name=str(name).strip(),
                storage_location=location,
                defaults={
                    "detailed_spec": str(detailed_spec).strip() if detailed_spec else "",
                    "total_existing": int(total_existing),
                    "observations": str(observations).strip(),
                }
            )

            if created:
                result["created"] += 1
            else:
                result["updated"] += 1

        except Exception as e:
            result["errors"].append(f"Fila {row_num}: {str(e)}")

    return result