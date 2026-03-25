# Import Formats

The MVP supports bulk import in `CSV` and `XLSX` for three datasets:

- assets
- elements with zones
- inspections with measurements

## Assets

### CSV

One table with these columns:

- `name` required
- `address`
- `commissioned_year`
- `purpose`
- `responsibility_class`

### XLSX

Single worksheet with the same columns as the CSV file.

## Elements with zones

### CSV

Flat table where each row represents one zone of an element. Element-level fields
are repeated for each zone row.

Required element columns:

- `element_id`
- `element_type`
- `environment_category`
- `section_type`
- `fy_mpa`
- `check_type`
- `demand_value`

Optional element columns:

- `steel_grade`
- `work_scheme`
- `operating_zone`
- `current_service_life_years`
- `gamma_m`
- `stability_factor`
- `demand_growth_factor_per_year`
- all supported section geometry fields:
  - `reference_thickness_mm`
  - `width_mm`
  - `thickness_mm`
  - `height_mm`
  - `flange_width_mm`
  - `web_thickness_mm`
  - `flange_thickness_mm`
  - `leg_horizontal_mm`
  - `leg_vertical_mm`
  - `leg_thickness_mm`
  - `outer_diameter_mm`
  - `wall_thickness_mm`
  - `area0_mm2`
  - `inertia0_mm4`
  - `section_modulus0_mm3`

Required zone columns:

- `zone_id`
- `role`
- `initial_thickness_mm`

Optional zone columns:

- `exposed_surfaces`
- `pitting_factor`
- `pit_loss_mm`

### XLSX

Workbook with two sheets:

- `elements`
- `zones`

`elements` sheet contains one row per element with the same element columns as the CSV format.

`zones` sheet contains:

- `element_id` required
- `zone_id` required
- `role` required
- `initial_thickness_mm` required
- `exposed_surfaces`
- `pitting_factor`
- `pit_loss_mm`

## Inspections with measurements

### CSV

Flat table where each row represents one measurement. Inspection-level fields are
repeated for all measurements of the same inspection.

Required inspection columns:

- `performed_at`
- `method`

Optional inspection columns:

- `inspection_code`
- `executor`
- `findings`

Measurement columns:

- `zone_id`
- `point_id`
- `thickness_mm`
- `error_mm`
- `measured_at`
- `quality`
- `units`
- `comment`

If multiple rows belong to the same inspection, set the same `inspection_code`.

### XLSX

Workbook with:

- `inspections` sheet required
- `measurements` sheet optional

`inspections` sheet columns:

- `inspection_code`
- `performed_at` required
- `method` required
- `executor`
- `findings`

`measurements` sheet columns:

- `inspection_code` required
- `zone_id` required
- `point_id`
- `thickness_mm` required
- `error_mm`
- `measured_at`
- `quality`
- `units`
- `comment`

## Accepted value conventions

- Dates: `YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY`, or `YYYY/MM/DD`
- Numbers: dot or comma decimal separator
- Environment category: `C2`, `C3`, `C4`, `C5`
- Section type: `plate`, `i_section`, `channel`, `angle`, `tube`, `generic_reduced`
- Check type: `axial_tension`, `axial_compression`, `bending_major`
