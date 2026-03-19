from decimal import Decimal
from openpyxl import load_workbook

from ..models import AcademicArea, Equipment, Supply, StorageLocation, Career, Subject


def split_values(text, separator=","):
    if not text:
        return []
    return [item.strip() for item in str(text).split(separator) if item and str(item).strip()]


def normalize_code(value):
    if value is None:
        return ""
    return str(value).replace('"', "").replace("'", "").replace("\n", "").replace("\r", "").strip()


def extract_codes(value):
    if not value:
        return []

    raw = str(value).replace("\r", "\n")
    parts = raw.split("\n")

    codes = []
    for part in parts:
        cleaned = normalize_code(part)
        if cleaned:
            codes.append(cleaned)

    # quita duplicados manteniendo orden
    return list(dict.fromkeys(codes))


def resolve_condition(good_count, repairable_count, bad_count):
    good_count = int(good_count or 0)
    repairable_count = int(repairable_count or 0)
    bad_count = int(bad_count or 0)

    if bad_count > 0:
        return "bad"
    if repairable_count > 0:
        return "repairable"
    return "good"


def import_equipment_excel(file_obj):
    wb = load_workbook(file_obj, data_only=True)
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
            good_count = row[9] or 0
            repairable_count = row[10] or 0
            bad_count = row[11] or 0
            unit_value_uf = row[12]
            observations = row[14] or ""
            academic_area_name = row[15]

            if not name:
                continue

            codes = extract_codes(inventory_codes)
            if not codes:
                result["errors"].append(
                    f"Fila {row_num}: no se encontró un código de inventario válido.")
                continue

            location, _ = StorageLocation.objects.get_or_create(
                name=str(location_name).strip(
                ) if location_name else "Sin ubicación"
            )

            condition = resolve_condition(
                good_count, repairable_count, bad_count)

            career_names = split_values(careers_text)
            subject_codes = split_values(subjects_text)

            academic_area, _ = AcademicArea.objects.get_or_create(
                name=str(academic_area_name).strip()
            )

            career_objects = []
            for career_name in career_names:
                career, _ = Career.objects.get_or_create(name=career_name)
                career_objects.append(career)

            subject_objects = []
            for subject_code in subject_codes:
                subject, _ = Subject.objects.get_or_create(
                    code=subject_code,
                    defaults={"name": ""}
                )
                subject_objects.append(subject)

            for code in codes:
                equipment, created = Equipment.objects.update_or_create(
                    inventory_code=code,
                    defaults={
                        "name": str(name).strip(),
                        "detailed_spec": str(detailed_spec).strip() if detailed_spec else "",
                        "academic_area": academic_area,
                        "storage_location": location,
                        "condition": condition,
                        "unit_value_uf": Decimal(str(unit_value_uf)) if unit_value_uf not in (None, "") else None,
                        "observations": str(observations).strip(),
                    }
                )

                equipment.careers.set(career_objects)
                equipment.subjects.set(subject_objects)

                if created:
                    result["created"] += 1
                else:
                    result["updated"] += 1

        except Exception as e:
            result["errors"].append(f"Fila {row_num}: {str(e)}")

    return result


def import_supply_excel(file_obj):
    wb = load_workbook(file_obj, data_only=True)
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