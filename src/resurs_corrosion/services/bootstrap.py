from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ..domain import (
    ActionInput,
    AssetCreate,
    CheckType,
    ElementCreate,
    EnvironmentCategory,
    InspectionCreate,
    MaterialInput,
    SectionDefinition,
    SectionType,
    ThicknessMeasurement,
    ZoneDefinition,
)
from ..models import AssetModel
from ..storage import (
    create_asset,
    create_element,
    create_inspection,
    get_element_by_asset_and_code,
    get_inspection_by_element_and_code,
    list_assets,
)

DEMO_ASSET_NAME = "Демонстрационный объект"
DEMO_ELEMENT_CODE = "BEAM-DEMO-01"


def seed_demo_workspace_if_empty(session_factory: sessionmaker) -> bool:
    with session_factory() as session:
        demo_asset = session.scalars(select(AssetModel).where(AssetModel.name == DEMO_ASSET_NAME)).first()
        if demo_asset is None and list_assets(session):
            return False

        seeded = False
        asset = demo_asset
        if asset is None:
            asset = create_asset(
                session,
                AssetCreate(
                    name=DEMO_ASSET_NAME,
                    address="Московская область",
                    commissioned_year=2006,
                    purpose="Промышленная рама",
                    responsibility_class="КС-2",
                ),
            )
            seeded = True

        element = get_element_by_asset_and_code(session, asset.id, DEMO_ELEMENT_CODE)
        if element is None:
            element = create_element(
                session,
                asset.id,
                ElementCreate(
                    element_id=DEMO_ELEMENT_CODE,
                    element_type="Балка покрытия",
                    steel_grade="C255",
                    work_scheme="Изгиб",
                    operating_zone="Кромка покрытия",
                    environment_category=EnvironmentCategory.C4,
                    current_service_life_years=20.0,
                    section=SectionDefinition(
                        section_type=SectionType.I_SECTION,
                        height_mm=300.0,
                        flange_width_mm=150.0,
                        web_thickness_mm=8.0,
                        flange_thickness_mm=12.0,
                    ),
                    zones=[
                        ZoneDefinition(
                            zone_id="top",
                            role="top_flange",
                            initial_thickness_mm=12.0,
                            exposed_surfaces=1,
                            pitting_factor=0.05,
                            pit_loss_mm=0.2,
                        ),
                        ZoneDefinition(
                            zone_id="bottom",
                            role="bottom_flange",
                            initial_thickness_mm=12.0,
                            exposed_surfaces=1,
                            pitting_factor=0.08,
                            pit_loss_mm=0.3,
                        ),
                        ZoneDefinition(
                            zone_id="web",
                            role="web",
                            initial_thickness_mm=8.0,
                            exposed_surfaces=2,
                            pitting_factor=0.12,
                            pit_loss_mm=0.4,
                        ),
                    ],
                    material=MaterialInput(
                        fy_mpa=245.0,
                        gamma_m=1.05,
                        stability_factor=0.9,
                    ),
                    action=ActionInput(
                        check_type=CheckType.BENDING_MAJOR,
                        demand_value=110.0,
                        demand_growth_factor_per_year=0.005,
                    ),
                ),
            )
            seeded = True

        inspections = [
            InspectionCreate(
                inspection_code="DEMO-2024",
                performed_at=date(2024, 3, 25),
                method="Ультразвуковая толщинометрия",
                executor="Лаборатория А",
                findings="Умеренная коррозия стенки и нижнего пояса.",
                measurements=[
                    ThicknessMeasurement(
                        zone_id="top",
                        point_id="T-1",
                        thickness_mm=11.6,
                        error_mm=0.1,
                        measured_at=date(2024, 3, 25),
                        quality=0.94,
                        units="mm",
                        comment="Локальная деградация защитного покрытия.",
                    ),
                    ThicknessMeasurement(
                        zone_id="bottom",
                        point_id="B-1",
                        thickness_mm=11.3,
                        error_mm=0.1,
                        measured_at=date(2024, 3, 25),
                        quality=0.95,
                        units="mm",
                    ),
                    ThicknessMeasurement(
                        zone_id="web",
                        point_id="W-1",
                        thickness_mm=7.5,
                        error_mm=0.1,
                        measured_at=date(2024, 3, 25),
                        quality=0.92,
                        units="mm",
                    ),
                ],
            ),
            InspectionCreate(
                inspection_code="DEMO-2026",
                performed_at=date(2026, 3, 25),
                method="Ультразвуковая толщинометрия",
                executor="Лаборатория Б",
                findings="Отмечено развитие коррозии в зоне стенки.",
                measurements=[
                    ThicknessMeasurement(
                        zone_id="top",
                        point_id="T-2",
                        thickness_mm=11.3,
                        error_mm=0.1,
                        measured_at=date(2026, 3, 25),
                        quality=0.95,
                        units="mm",
                    ),
                    ThicknessMeasurement(
                        zone_id="bottom",
                        point_id="B-2",
                        thickness_mm=10.9,
                        error_mm=0.1,
                        measured_at=date(2026, 3, 25),
                        quality=0.95,
                        units="mm",
                    ),
                    ThicknessMeasurement(
                        zone_id="web",
                        point_id="W-2",
                        thickness_mm=7.0,
                        error_mm=0.1,
                        measured_at=date(2026, 3, 25),
                        quality=0.93,
                        units="mm",
                    ),
                ],
            ),
        ]

        for inspection in inspections:
            existing = get_inspection_by_element_and_code(session, element.id, inspection.inspection_code)
            if existing is None:
                create_inspection(session, element.id, inspection)
                seeded = True

        return seeded
