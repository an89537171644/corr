from __future__ import annotations

import pytest

from resurs_corrosion.domain import SectionDefinition, SectionType, ZoneDefinition, ZoneState
from resurs_corrosion.services.sections import evaluate_effective_section


@pytest.mark.parametrize(
    ("section", "zones", "intact_states", "corroded_states"),
    [
        (
            SectionDefinition(section_type=SectionType.PLATE, width_mm=200.0, thickness_mm=10.0),
            [ZoneDefinition(zone_id="z1", role="plate", initial_thickness_mm=10.0)],
            [ZoneState(zone_id="z1", role="plate", corrosion_loss_mm=0.0, effective_thickness_mm=10.0)],
            [ZoneState(zone_id="z1", role="plate", corrosion_loss_mm=2.0, effective_thickness_mm=8.0)],
        ),
        (
            SectionDefinition(
                section_type=SectionType.I_SECTION,
                height_mm=300.0,
                flange_width_mm=150.0,
                web_thickness_mm=8.0,
                flange_thickness_mm=12.0,
            ),
            [
                ZoneDefinition(zone_id="top", role="top_flange", initial_thickness_mm=12.0),
                ZoneDefinition(zone_id="bottom", role="bottom_flange", initial_thickness_mm=12.0),
                ZoneDefinition(zone_id="web", role="web", initial_thickness_mm=8.0, exposed_surfaces=2),
            ],
            [
                ZoneState(zone_id="top", role="top_flange", corrosion_loss_mm=0.0, effective_thickness_mm=12.0),
                ZoneState(zone_id="bottom", role="bottom_flange", corrosion_loss_mm=0.0, effective_thickness_mm=12.0),
                ZoneState(zone_id="web", role="web", corrosion_loss_mm=0.0, effective_thickness_mm=8.0),
            ],
            [
                ZoneState(zone_id="top", role="top_flange", corrosion_loss_mm=1.0, effective_thickness_mm=11.0),
                ZoneState(zone_id="bottom", role="bottom_flange", corrosion_loss_mm=1.0, effective_thickness_mm=11.0),
                ZoneState(zone_id="web", role="web", corrosion_loss_mm=1.5, effective_thickness_mm=6.5),
            ],
        ),
        (
            SectionDefinition(
                section_type=SectionType.CHANNEL,
                height_mm=280.0,
                flange_width_mm=90.0,
                web_thickness_mm=7.0,
                flange_thickness_mm=11.0,
            ),
            [
                ZoneDefinition(zone_id="top", role="top_flange", initial_thickness_mm=11.0),
                ZoneDefinition(zone_id="bottom", role="bottom_flange", initial_thickness_mm=11.0),
                ZoneDefinition(zone_id="web", role="web", initial_thickness_mm=7.0),
            ],
            [
                ZoneState(zone_id="top", role="top_flange", corrosion_loss_mm=0.0, effective_thickness_mm=11.0),
                ZoneState(zone_id="bottom", role="bottom_flange", corrosion_loss_mm=0.0, effective_thickness_mm=11.0),
                ZoneState(zone_id="web", role="web", corrosion_loss_mm=0.0, effective_thickness_mm=7.0),
            ],
            [
                ZoneState(zone_id="top", role="top_flange", corrosion_loss_mm=1.3, effective_thickness_mm=9.7),
                ZoneState(zone_id="bottom", role="bottom_flange", corrosion_loss_mm=1.5, effective_thickness_mm=9.5),
                ZoneState(zone_id="web", role="web", corrosion_loss_mm=1.8, effective_thickness_mm=5.2),
            ],
        ),
        (
            SectionDefinition(
                section_type=SectionType.ANGLE,
                leg_horizontal_mm=100.0,
                leg_vertical_mm=80.0,
                leg_thickness_mm=10.0,
            ),
            [ZoneDefinition(zone_id="leg", role="angle_leg", initial_thickness_mm=10.0)],
            [ZoneState(zone_id="leg", role="angle_leg", corrosion_loss_mm=0.0, effective_thickness_mm=10.0)],
            [ZoneState(zone_id="leg", role="angle_leg", corrosion_loss_mm=2.0, effective_thickness_mm=8.0)],
        ),
        (
            SectionDefinition(section_type=SectionType.TUBE, outer_diameter_mm=120.0, wall_thickness_mm=6.0),
            [ZoneDefinition(zone_id="tube", role="tube_wall", initial_thickness_mm=6.0)],
            [ZoneState(zone_id="tube", role="tube_wall", corrosion_loss_mm=0.0, effective_thickness_mm=6.0)],
            [ZoneState(zone_id="tube", role="tube_wall", corrosion_loss_mm=1.0, effective_thickness_mm=5.0)],
        ),
    ],
)
def test_reducers_are_monotone_for_corroded_sections(section, zones, intact_states, corroded_states) -> None:
    intact = evaluate_effective_section(section, zones, intact_states).properties
    corroded = evaluate_effective_section(section, zones, corroded_states).properties

    assert corroded.area_mm2 <= intact.area_mm2
    assert corroded.inertia_mm4 <= intact.inertia_mm4
    assert corroded.section_modulus_mm3 <= intact.section_modulus_mm3
