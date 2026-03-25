const state = {
  assets: [],
  elements: [],
  inspections: [],
  selectedAssetId: null,
  selectedElementId: null,
  selectedInspectionId: null,
  editingAssetId: null,
  editingElementId: null,
  editingInspectionId: null,
  calculation: null,
  reportPreview: null,
  reports: [],
};

const refs = {
  notice: document.getElementById("notice"),
  healthBadge: document.getElementById("healthBadge"),
  selectedAssetBadge: document.getElementById("selectedAssetBadge"),
  selectedElementBadge: document.getElementById("selectedElementBadge"),
  assetSearchInput: document.getElementById("assetSearchInput"),
  assetList: document.getElementById("assetList"),
  elementList: document.getElementById("elementList"),
  inspectionList: document.getElementById("inspectionList"),
  elementCounter: document.getElementById("elementCounter"),
  inspectionCounter: document.getElementById("inspectionCounter"),
  assetForm: document.getElementById("assetForm"),
  elementForm: document.getElementById("elementForm"),
  inspectionForm: document.getElementById("inspectionForm"),
  calculationForm: document.getElementById("calculationForm"),
  reportForm: document.getElementById("reportForm"),
  assetImportForm: document.getElementById("assetImportForm"),
  elementImportForm: document.getElementById("elementImportForm"),
  inspectionImportForm: document.getElementById("inspectionImportForm"),
  assetModePill: document.getElementById("assetModePill"),
  elementModePill: document.getElementById("elementModePill"),
  inspectionModePill: document.getElementById("inspectionModePill"),
  assetHint: document.getElementById("assetHint"),
  elementHint: document.getElementById("elementHint"),
  inspectionHint: document.getElementById("inspectionHint"),
  assetSubmitBtn: document.getElementById("assetSubmitBtn"),
  elementSubmitBtn: document.getElementById("elementSubmitBtn"),
  inspectionSubmitBtn: document.getElementById("inspectionSubmitBtn"),
  newAssetBtn: document.getElementById("newAssetBtn"),
  newElementBtn: document.getElementById("newElementBtn"),
  newInspectionBtn: document.getElementById("newInspectionBtn"),
  previewReportBtn: document.getElementById("previewReportBtn"),
  zoneRows: document.getElementById("zoneRows"),
  measurementRows: document.getElementById("measurementRows"),
  calculationSummary: document.getElementById("calculationSummary"),
  timelineChart: document.getElementById("timelineChart"),
  scenarioTable: document.getElementById("scenarioTable"),
  reportPreview: document.getElementById("reportPreview"),
  reportResults: document.getElementById("reportResults"),
  importResults: document.getElementById("importResults"),
  zoneRowTemplate: document.getElementById("zoneRowTemplate"),
  measurementRowTemplate: document.getElementById("measurementRowTemplate"),
  sectionTypeSelect: document.getElementById("sectionTypeSelect"),
};

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  resetAssetForm();
  resetElementForm();
  resetInspectionForm();
  syncSectionFields();
  renderCalculationResult(null);
  renderReports([]);
  renderReportPreview();
  loadBootData();
});

function bindEvents() {
  document.getElementById("refreshAssetsBtn").addEventListener("click", () => loadAssets());
  document.getElementById("addZoneBtn").addEventListener("click", () => addZoneRow());
  document.getElementById("addMeasurementBtn").addEventListener("click", () => addMeasurementRow());
  refs.newAssetBtn.addEventListener("click", () => resetAssetForm(true));
  refs.newElementBtn.addEventListener("click", () => resetElementForm(true));
  refs.newInspectionBtn.addEventListener("click", () => resetInspectionForm(true));
  refs.previewReportBtn.addEventListener("click", handleReportPreview);
  refs.sectionTypeSelect.addEventListener("change", syncSectionFields);
  refs.assetSearchInput.addEventListener("input", renderAssets);
  refs.assetForm.addEventListener("submit", handleAssetSubmit);
  refs.elementForm.addEventListener("submit", handleElementSubmit);
  refs.inspectionForm.addEventListener("submit", handleInspectionSubmit);
  refs.calculationForm.addEventListener("submit", handleCalculationSubmit);
  refs.reportForm.addEventListener("submit", handleReportSubmit);
  refs.reportForm.addEventListener("input", renderReportPreview);
  refs.reportForm.addEventListener("change", renderReportPreview);
  refs.assetImportForm.addEventListener("submit", (event) => handleImportSubmit(event, "/api/v1/import/assets"));
  refs.elementImportForm.addEventListener("submit", (event) => {
    if (!state.selectedAssetId) {
      event.preventDefault();
      showNotice("Select an asset before importing elements.", "error");
      return;
    }
    handleImportSubmit(event, `/api/v1/assets/${state.selectedAssetId}/import/elements`);
  });
  refs.inspectionImportForm.addEventListener("submit", (event) => {
    if (!state.selectedElementId) {
      event.preventDefault();
      showNotice("Select an element before importing inspections.", "error");
      return;
    }
    handleImportSubmit(event, `/api/v1/elements/${state.selectedElementId}/import/inspections`);
  });
}

async function loadBootData() {
  await Promise.all([checkHealth(), loadAssets()]);
}

async function checkHealth() {
  try {
    const result = await api("/health");
    refs.healthBadge.textContent = result.status;
  } catch {
    refs.healthBadge.textContent = "offline";
  }
}

async function loadAssets() {
  try {
    state.assets = await api("/api/v1/assets");
    if (!state.assets.some((asset) => asset.id === state.selectedAssetId)) {
      state.selectedAssetId = state.assets.length ? state.assets[0].id : null;
    }
    if (state.editingAssetId && !state.assets.some((asset) => asset.id === state.editingAssetId)) {
      resetAssetForm();
    }

    renderAssets();
    updateSelectedBadges();

    if (state.selectedAssetId) {
      await loadElements(state.selectedAssetId);
      return;
    }

    state.elements = [];
    state.inspections = [];
    state.selectedElementId = null;
    state.selectedInspectionId = null;
    if (state.editingElementId) {
      resetElementForm();
    }
    if (state.editingInspectionId) {
      resetInspectionForm();
    }
    renderElements();
    renderInspections();
    clearDerivedOutputs();
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function loadElements(assetId) {
  try {
    state.elements = await api(`/api/v1/assets/${assetId}/elements`);
    refs.elementCounter.textContent = String(state.elements.length);

    if (!state.elements.some((element) => element.id === state.selectedElementId)) {
      state.selectedElementId = state.elements.length ? state.elements[0].id : null;
    }
    if (state.editingElementId && !state.elements.some((element) => element.id === state.editingElementId)) {
      resetElementForm();
    }
    if (!state.selectedElementId) {
      state.inspections = [];
      state.selectedInspectionId = null;
      if (state.editingInspectionId) {
        resetInspectionForm();
      }
    }

    renderElements();
    updateSelectedBadges();

    if (state.selectedElementId) {
      await loadInspections(state.selectedElementId);
      return;
    }

    refs.inspectionCounter.textContent = "0";
    renderInspections();
    clearDerivedOutputs();
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function loadInspections(elementId) {
  try {
    state.inspections = await api(`/api/v1/elements/${elementId}/inspections`);
    refs.inspectionCounter.textContent = String(state.inspections.length);

    if (!state.inspections.some((inspection) => inspection.id === state.selectedInspectionId)) {
      state.selectedInspectionId = state.inspections.length ? state.inspections[0].id : null;
    }
    if (state.editingInspectionId && !state.inspections.some((inspection) => inspection.id === state.editingInspectionId)) {
      resetInspectionForm();
    }

    renderInspections();
    renderReportPreview();
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function selectAsset(assetId, options = {}) {
  const loadForm = options.loadForm !== false;
  state.selectedAssetId = assetId;
  state.selectedElementId = null;
  state.selectedInspectionId = null;
  resetElementForm();
  resetInspectionForm();
  clearDerivedOutputs();
  if (loadForm) {
    const asset = state.assets.find((item) => item.id === assetId);
    if (asset) {
      populateAssetForm(asset);
    }
  }
  renderAssets();
  updateSelectedBadges();
  await loadElements(assetId);
}

async function selectElement(elementId, options = {}) {
  const loadForm = options.loadForm !== false;
  state.selectedElementId = elementId;
  state.selectedInspectionId = null;
  resetInspectionForm();
  clearDerivedOutputs();
  if (loadForm) {
    const element = state.elements.find((item) => item.id === elementId);
    if (element) {
      populateElementForm(element);
    }
  }
  renderElements();
  updateSelectedBadges();
  await loadInspections(elementId);
}

function selectInspection(inspectionId, options = {}) {
  const loadForm = options.loadForm !== false;
  state.selectedInspectionId = inspectionId;
  if (loadForm) {
    const inspection = state.inspections.find((item) => item.id === inspectionId);
    if (inspection) {
      populateInspectionForm(inspection);
    }
  }
  renderInspections();
  renderReportPreview();
}

async function handleAssetSubmit(event) {
  event.preventDefault();
  const form = new FormData(refs.assetForm);
  const payload = compactObject({
    name: form.get("name"),
    address: form.get("address"),
    commissioned_year: numberOrNull(form.get("commissioned_year")),
    purpose: form.get("purpose"),
    responsibility_class: form.get("responsibility_class"),
  });

  const isUpdate = state.editingAssetId !== null;
  const url = isUpdate ? `/api/v1/assets/${state.editingAssetId}` : "/api/v1/assets";

  try {
    const asset = await api(url, {
      method: isUpdate ? "PUT" : "POST",
      json: payload,
    });
    state.selectedAssetId = asset.id;
    showNotice(`Asset "${asset.name}" ${isUpdate ? "updated" : "created"}.`, "info");
    if (isUpdate) {
      await loadAssets();
      const refreshed = state.assets.find((item) => item.id === asset.id) || asset;
      populateAssetForm(refreshed);
      return;
    }
    resetAssetForm();
    await loadAssets();
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleElementSubmit(event) {
  event.preventDefault();
  if (!state.selectedAssetId) {
    showNotice("Create or select an asset before saving an element.", "error");
    return;
  }

  const isUpdate = state.editingElementId !== null;
  const url = isUpdate
    ? `/api/v1/elements/${state.editingElementId}`
    : `/api/v1/assets/${state.selectedAssetId}/elements`;

  try {
    const element = await api(url, {
      method: isUpdate ? "PUT" : "POST",
      json: buildElementPayload(),
    });
    state.selectedElementId = element.id;
    clearDerivedOutputs();
    showNotice(`Element "${element.element_id}" ${isUpdate ? "updated" : "created"}.`, "info");
    if (isUpdate) {
      await loadElements(state.selectedAssetId);
      const refreshed = state.elements.find((item) => item.id === element.id) || element;
      populateElementForm(refreshed);
      return;
    }
    resetElementForm();
    await loadElements(state.selectedAssetId);
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleInspectionSubmit(event) {
  event.preventDefault();
  if (!state.selectedElementId) {
    showNotice("Select an element before saving an inspection.", "error");
    return;
  }

  const isUpdate = state.editingInspectionId !== null;
  const form = new FormData(refs.inspectionForm);
  const payload = compactObject({
    inspection_code: blankToNull(form.get("inspection_code")),
    performed_at: form.get("performed_at"),
    method: form.get("method"),
    executor: blankToNull(form.get("executor")),
    findings: blankToNull(form.get("findings")),
    measurements: collectRows(refs.measurementRows).map((row) => compactObject({
      zone_id: row.zone_id,
      point_id: blankToNull(row.point_id),
      thickness_mm: numberOrNull(row.thickness_mm),
      error_mm: numberOrNull(row.error_mm) ?? 0,
      measured_at: blankToNull(row.measured_at),
      quality: numberOrNull(row.quality) ?? 1,
    })),
  });

  try {
    const inspection = await api(
      isUpdate ? `/api/v1/inspections/${state.editingInspectionId}` : `/api/v1/elements/${state.selectedElementId}/inspections`,
      {
        method: isUpdate ? "PUT" : "POST",
        json: payload,
      },
    );
    state.selectedInspectionId = inspection.id;
    clearDerivedOutputs();
    showNotice(`Inspection ${isUpdate ? "updated" : "saved"}.`, "info");
    if (isUpdate) {
      await loadInspections(state.selectedElementId);
      const refreshed = state.inspections.find((item) => item.id === inspection.id) || inspection;
      populateInspectionForm(refreshed);
      return;
    }
    resetInspectionForm();
    await loadInspections(state.selectedElementId);
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleCalculationSubmit(event) {
  event.preventDefault();
  if (!state.selectedElementId) {
    showNotice("Select an element before running the baseline calculation.", "error");
    return;
  }

  const form = new FormData(refs.calculationForm);
  try {
    state.calculation = await api(`/api/v1/elements/${state.selectedElementId}/calculate/baseline`, {
      method: "POST",
      json: {
        forecast_horizon_years: numberOrNull(form.get("forecast_horizon_years")),
        time_step_years: numberOrNull(form.get("time_step_years")),
      },
    });
    renderCalculationResult(state.calculation);
    renderReportPreview();
    showNotice("Baseline calculation completed.", "info");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleReportPreview() {
  if (!state.selectedElementId) {
    showNotice("Select an element before previewing a report.", "error");
    return;
  }

  const request = readReportRequest();
  try {
    state.reportPreview = await api(`/api/v1/elements/${state.selectedElementId}/calculate/baseline`, {
      method: "POST",
      json: {
        forecast_horizon_years: request.forecast_horizon_years,
        time_step_years: request.time_step_years,
      },
    });
    renderReportPreview();
    showNotice("Report preview refreshed.", "info");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleReportSubmit(event) {
  event.preventDefault();
  if (!state.selectedElementId) {
    showNotice("Select an element before exporting a report.", "error");
    return;
  }

  const request = readReportRequest();
  if (!request.output_formats.length) {
    showNotice("Choose at least one export format.", "error");
    return;
  }

  try {
    const bundle = await api(`/api/v1/elements/${state.selectedElementId}/reports/baseline`, {
      method: "POST",
      json: request,
    });
    state.reports = bundle.artifacts;
    renderReports(bundle.artifacts);
    showNotice("Report bundle generated.", "info");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleImportSubmit(event, url) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const fileInput = formElement.querySelector('input[type="file"]');
  if (!fileInput.files.length) {
    showNotice("Choose a file before uploading.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const summary = await api(url, { method: "POST", formData });
    prependImportSummary(summary);
    formElement.reset();
    clearDerivedOutputs();
    showNotice(`${summary.dataset} import completed.`, "info");
    await loadAssets();
    if (state.selectedElementId) {
      await loadInspections(state.selectedElementId);
    }
  } catch (error) {
    showNotice(error.message, "error");
  }
}

function readReportRequest() {
  const form = new FormData(refs.reportForm);
  const outputFormats = [];
  if (form.get("format_docx")) outputFormats.push("docx");
  if (form.get("format_pdf")) outputFormats.push("pdf");
  return {
    report_title: blankToNull(form.get("report_title")),
    author: blankToNull(form.get("author")),
    forecast_horizon_years: numberOrNull(form.get("forecast_horizon_years")),
    time_step_years: numberOrNull(form.get("time_step_years")),
    output_formats: outputFormats,
  };
}

function buildElementPayload() {
  const form = new FormData(refs.elementForm);
  const section = { section_type: form.get("section_type") };
  [
    "reference_thickness_mm",
    "width_mm",
    "thickness_mm",
    "height_mm",
    "flange_width_mm",
    "web_thickness_mm",
    "flange_thickness_mm",
    "area0_mm2",
    "inertia0_mm4",
    "section_modulus0_mm3",
  ].forEach((field) => {
    const value = numberOrNull(form.get(field));
    if (value !== null) {
      section[field] = value;
    }
  });

  return compactObject({
    element_id: form.get("element_id"),
    element_type: form.get("element_type"),
    steel_grade: blankToNull(form.get("steel_grade")),
    work_scheme: blankToNull(form.get("work_scheme")),
    operating_zone: blankToNull(form.get("operating_zone")),
    environment_category: form.get("environment_category"),
    current_service_life_years: numberOrNull(form.get("current_service_life_years")) ?? 0,
    section,
    zones: collectRows(refs.zoneRows).map((row) => compactObject({
      zone_id: row.zone_id,
      role: row.role,
      initial_thickness_mm: numberOrNull(row.initial_thickness_mm),
      exposed_surfaces: integerOrNull(row.exposed_surfaces) ?? 1,
      pitting_factor: numberOrNull(row.pitting_factor) ?? 0,
      pit_loss_mm: numberOrNull(row.pit_loss_mm) ?? 0,
    })),
    material: {
      fy_mpa: numberOrNull(form.get("fy_mpa")),
      gamma_m: numberOrNull(form.get("gamma_m")) ?? 1,
      stability_factor: numberOrNull(form.get("stability_factor")) ?? 1,
    },
    action: {
      check_type: form.get("check_type"),
      demand_value: numberOrNull(form.get("demand_value")),
      demand_growth_factor_per_year: numberOrNull(form.get("demand_growth_factor_per_year")) ?? 0,
    },
  });
}

function renderAssets() {
  const filter = refs.assetSearchInput.value.trim().toLowerCase();
  const filtered = state.assets.filter((asset) => `${asset.name} ${asset.address || ""} ${asset.purpose || ""}`.toLowerCase().includes(filter));
  if (!filtered.length) {
    refs.assetList.innerHTML = '<div class="muted-state">No assets yet.</div>';
    return;
  }
  refs.assetList.innerHTML = filtered.map((asset) => `
    <article class="registry-item ${asset.id === state.selectedAssetId ? "active" : ""}">
      <button type="button" data-asset-id="${asset.id}">${escapeHtml(asset.name)}</button>
      <div class="registry-meta">${escapeHtml(asset.address || "No address")}<br>${escapeHtml(asset.purpose || "No purpose")}</div>
      <div class="registry-tag">${asset.id === state.editingAssetId ? "Loaded in form" : "Click to edit"}</div>
    </article>
  `).join("");
  refs.assetList.querySelectorAll("[data-asset-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await selectAsset(Number(button.dataset.assetId));
    });
  });
}

function renderElements() {
  refs.elementCounter.textContent = String(state.elements.length);
  if (!state.elements.length) {
    refs.elementList.innerHTML = '<div class="muted-state">No elements for the selected asset.</div>';
    return;
  }
  refs.elementList.innerHTML = state.elements.map((element) => `
    <article class="registry-item ${element.id === state.selectedElementId ? "active" : ""}">
      <button type="button" data-element-id="${element.id}">${escapeHtml(element.element_id)}</button>
      <div class="registry-meta">${escapeHtml(element.element_type)}<br>${escapeHtml(element.environment_category)} | ${formatNumber(element.current_service_life_years, 1)} y</div>
      <div class="registry-tag">${element.id === state.editingElementId ? "Loaded in form" : "Click to edit"}</div>
    </article>
  `).join("");
  refs.elementList.querySelectorAll("[data-element-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await selectElement(Number(button.dataset.elementId));
    });
  });
}

function renderInspections() {
  refs.inspectionCounter.textContent = String(state.inspections.length);
  if (!state.inspections.length) {
    refs.inspectionList.innerHTML = '<div class="muted-state">No inspections for the selected element.</div>';
    return;
  }
  refs.inspectionList.innerHTML = state.inspections.map((inspection) => `
    <article class="registry-item ${inspection.id === state.selectedInspectionId ? "active" : ""}">
      <button type="button" data-inspection-id="${inspection.id}">${escapeHtml(inspection.inspection_code || `inspection-${inspection.id}`)}</button>
      <div class="registry-meta">${escapeHtml(inspection.performed_at)} | ${escapeHtml(inspection.method)}<br>measurements: ${inspection.measurements.length}</div>
      <div class="registry-tag">${inspection.id === state.editingInspectionId ? "Loaded in form" : "Click to edit"}</div>
    </article>
  `).join("");
  refs.inspectionList.querySelectorAll("[data-inspection-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectInspection(Number(button.dataset.inspectionId));
    });
  });
}

function renderCalculationResult(result) {
  if (!result) {
    refs.calculationSummary.innerHTML = "Select an element and run a calculation.";
    refs.calculationSummary.classList.add("empty-block");
    refs.timelineChart.innerHTML = "Timeline chart will appear here.";
    refs.timelineChart.classList.add("empty-block");
    refs.scenarioTable.innerHTML = "Scenario comparison will appear here.";
    refs.scenarioTable.classList.add("empty-block");
    return;
  }

  refs.calculationSummary.classList.remove("empty-block");
  refs.calculationSummary.innerHTML = `
    <article class="summary-card"><span>Environment</span><strong>${escapeHtml(result.environment_category)}</strong></article>
    <article class="summary-card"><span>Scenario Count</span><strong>${result.results.length}</strong></article>
    <article class="summary-card"><span>Exceedance Share</span><strong>${formatNumber(result.risk_profile.exceedance_share, 3)}</strong></article>
    <article class="summary-card"><span>Next Inspection</span><strong>${formatNumber(result.risk_profile.next_inspection_within_years, 2)} y</strong></article>
    <article class="summary-card"><span>Recommendation</span><strong>${escapeHtml(result.risk_profile.recommended_action)}</strong></article>
  `;

  refs.scenarioTable.classList.remove("empty-block");
  refs.scenarioTable.innerHTML = `
    <table class="table">
      <thead><tr><th>Scenario</th><th>Resistance</th><th>Demand</th><th>Margin</th><th>Remaining Life</th><th>State</th></tr></thead>
      <tbody>
        ${result.results.map((row) => `
          <tr>
            <td>${escapeHtml(row.scenario_name)}</td>
            <td>${formatNumber(row.resistance_value, 3)} ${escapeHtml(row.resistance_unit)}</td>
            <td>${formatNumber(row.demand_value, 3)} ${escapeHtml(row.demand_unit)}</td>
            <td>${formatNumber(row.margin_value, 3)}</td>
            <td>${row.remaining_life_years == null ? "-" : `${formatNumber(row.remaining_life_years, 2)} y`}</td>
            <td>${row.limit_state_reached_within_horizon ? "Reached" : "Not reached"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;

  const baseline = result.results[0];
  refs.timelineChart.classList.remove("empty-block");
  refs.timelineChart.innerHTML = renderTimelineChart(baseline.timeline, baseline.resistance_unit);
}

function renderReportPreview() {
  const asset = state.assets.find((item) => item.id === state.selectedAssetId) || null;
  const element = state.elements.find((item) => item.id === state.selectedElementId) || null;
  const previewResult = state.reportPreview || state.calculation;
  const latestInspection = getLatestInspection();
  const request = readReportRequest();
  const reportTitle = request.report_title || "Residual life report";
  const author = request.author || "Engineering team";
  const formats = request.output_formats.length ? request.output_formats.map((item) => item.toUpperCase()).join(", ") : "No format selected";
  const previewNote = state.reportPreview
    ? "Preview synchronized with the report form horizon."
    : state.calculation
      ? "Preview uses the latest baseline calculation already in memory."
      : "Run Preview Report or Baseline to embed scenario tables and recommendation text.";

  if (!element) {
    refs.reportPreview.classList.add("empty-block");
    refs.reportPreview.innerHTML = "Select an element to build a report preview.";
    return;
  }

  const scenarioTable = previewResult
    ? `
      <table class="table">
        <thead><tr><th>Scenario</th><th>Margin</th><th>Remaining Life</th><th>State</th></tr></thead>
        <tbody>
          ${previewResult.results.map((row) => `
            <tr>
              <td>${escapeHtml(row.scenario_name)}</td>
              <td>${formatNumber(row.margin_value, 3)}</td>
              <td>${row.remaining_life_years == null ? "-" : `${formatNumber(row.remaining_life_years, 2)} y`}</td>
              <td>${row.limit_state_reached_within_horizon ? "Reached" : "Not reached"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `
    : '<p class="muted-state">No calculation snapshot is attached to the preview yet.</p>';

  refs.reportPreview.classList.remove("empty-block");
  refs.reportPreview.innerHTML = `
    <div class="preview-cover">
      <p class="eyebrow">Draft Report</p>
      <h3>${escapeHtml(reportTitle)}</h3>
      <p class="preview-text">${escapeHtml(asset ? asset.name : "Asset is not selected")} | ${escapeHtml(element.element_id)} | ${escapeHtml(element.environment_category)}</p>
      <p class="preview-note">${escapeHtml(previewNote)}</p>
    </div>
    <div class="summary-grid">
      <article class="summary-card"><span>Author</span><strong>${escapeHtml(author)}</strong></article>
      <article class="summary-card"><span>Forecast Horizon</span><strong>${formatMaybeNumber(request.forecast_horizon_years, 1)} y</strong></article>
      <article class="summary-card"><span>Time Step</span><strong>${formatMaybeNumber(request.time_step_years, 1)} y</strong></article>
      <article class="summary-card"><span>Formats</span><strong>${escapeHtml(formats)}</strong></article>
      <article class="summary-card"><span>Inspection Base</span><strong>${escapeHtml(latestInspection ? latestInspection.inspection_code || `inspection-${latestInspection.id}` : "No inspections")}</strong></article>
      <article class="summary-card"><span>Recommended Action</span><strong>${escapeHtml(previewResult ? previewResult.risk_profile.recommended_action : "Pending calculation")}</strong></article>
    </div>
    <div class="preview-grid">
      <section class="preview-section">
        <h3>Expected Sections</h3>
        <div class="preview-line"><strong>1.</strong><span>Asset passport and responsibility context.</span></div>
        <div class="preview-line"><strong>2.</strong><span>Element passport with section geometry, material, and zone model.</span></div>
        <div class="preview-line"><strong>3.</strong><span>Inspection log summary with latest measurements and findings.</span></div>
        <div class="preview-line"><strong>4.</strong><span>Baseline scenario comparison and capacity reserve evolution.</span></div>
        <div class="preview-line"><strong>5.</strong><span>Residual life conclusion and next inspection recommendation.</span></div>
      </section>
      <section class="preview-section">
        <h3>Context Snapshot</h3>
        <div class="preview-line"><strong>Asset</strong><span>${escapeHtml(asset ? asset.name : "Not loaded")}</span></div>
        <div class="preview-line"><strong>Element</strong><span>${escapeHtml(element.element_id)} (${escapeHtml(element.element_type)})</span></div>
        <div class="preview-line"><strong>Service Life</strong><span>${formatNumber(element.current_service_life_years, 1)} y</span></div>
        <div class="preview-line"><strong>Zones</strong><span>${element.zones.length}</span></div>
        <div class="preview-line"><strong>Latest Inspection</strong><span>${escapeHtml(latestInspection ? latestInspection.performed_at : "No inspection data")}</span></div>
        <div class="preview-line"><strong>Measurements</strong><span>${latestInspection ? latestInspection.measurements.length : 0}</span></div>
      </section>
    </div>
    <section class="preview-section">
      <h3>Calculation Extract</h3>
      ${scenarioTable}
    </section>
  `;
}

function renderTimelineChart(timeline, unit) {
  if (!timeline.length) {
    return "No timeline data.";
  }
  const width = 760;
  const height = 280;
  const margin = { top: 18, right: 18, bottom: 34, left: 54 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const ages = timeline.map((point) => point.age_years);
  const values = timeline.flatMap((point) => [point.resistance_value, point.demand_value]);
  const minAge = Math.min(...ages);
  const maxAge = Math.max(...ages);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const rangeAge = maxAge - minAge || 1;
  const rangeValue = maxValue - minValue || 1;
  const scaleX = (value) => margin.left + ((value - minAge) / rangeAge) * innerWidth;
  const scaleY = (value) => margin.top + innerHeight - ((value - minValue) / rangeValue) * innerHeight;
  const resistancePoints = timeline.map((point) => `${scaleX(point.age_years)},${scaleY(point.resistance_value)}`).join(" ");
  const demandPoints = timeline.map((point) => `${scaleX(point.age_years)},${scaleY(point.demand_value)}`).join(" ");
  const ticks = 5;
  const gridLines = Array.from({ length: ticks + 1 }, (_, index) => {
    const yValue = minValue + (rangeValue / ticks) * index;
    const y = scaleY(yValue);
    return `<line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="rgba(23,33,38,0.10)" stroke-dasharray="4 6"></line><text x="${margin.left - 10}" y="${y + 4}" text-anchor="end" fill="#5d696f" font-size="11">${formatNumber(yValue, 1)}</text>`;
  }).join("");
  const xTicks = Array.from({ length: ticks + 1 }, (_, index) => {
    const age = minAge + (rangeAge / ticks) * index;
    const x = scaleX(age);
    return `<line x1="${x}" y1="${margin.top}" x2="${x}" y2="${height - margin.bottom}" stroke="rgba(23,33,38,0.06)"></line><text x="${x}" y="${height - margin.bottom + 18}" text-anchor="middle" fill="#5d696f" font-size="11">${formatNumber(age, 1)}</text>`;
  }).join("");
  return `
    <div class="legend">
      <span class="legend-item"><span class="legend-swatch" style="background:#1f6f8b"></span>Resistance (${escapeHtml(unit)})</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#b6542d"></span>Demand (${escapeHtml(unit)})</span>
    </div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Resistance and demand timeline chart">
      ${gridLines}
      ${xTicks}
      <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="#172126" stroke-width="1.2"></line>
      <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="#172126" stroke-width="1.2"></line>
      <polyline fill="none" stroke="#1f6f8b" stroke-width="3" points="${resistancePoints}"></polyline>
      <polyline fill="none" stroke="#b6542d" stroke-width="3" points="${demandPoints}"></polyline>
      <text x="${width / 2}" y="${height - 6}" text-anchor="middle" fill="#5d696f" font-size="12">Age, years</text>
    </svg>
  `;
}

function renderReports(artifacts) {
  if (!artifacts.length) {
    refs.reportResults.innerHTML = "Generated reports will appear here.";
    refs.reportResults.classList.add("empty-block");
    return;
  }
  refs.reportResults.classList.remove("empty-block");
  refs.reportResults.innerHTML = artifacts.map((artifact) => `
    <div class="file-link">
      <div>
        <a href="${artifact.download_url}">${escapeHtml(artifact.filename)}</a>
        <small>${artifact.format.toUpperCase()} | ${formatBytes(artifact.size_bytes)}</small>
      </div>
      <a href="${artifact.download_url}">Download</a>
    </div>
  `).join("");
}

function prependImportSummary(summary) {
  refs.importResults.classList.remove("empty-block");
  const errors = summary.errors && summary.errors.length
    ? `<div class="registry-meta">${summary.errors.map((error) => `${escapeHtml(error.row_reference)}: ${escapeHtml(error.message)}`).join("<br>")}</div>`
    : "";
  refs.importResults.innerHTML = `
    <div class="file-link">
      <div>
        <strong>${escapeHtml(summary.dataset)}</strong>
        <small>${summary.source_format.toUpperCase()} | processed ${summary.rows_processed} | created ${summary.created_count} | updated ${summary.updated_count}</small>
        ${errors}
      </div>
    </div>
  ` + refs.importResults.innerHTML;
}

function resetAssetForm(showNoticeFlag = false) {
  refs.assetForm.reset();
  state.editingAssetId = null;
  refs.assetModePill.textContent = "Create mode";
  refs.assetHint.textContent = "Register a new asset or click an existing one to load it into the form.";
  refs.assetSubmitBtn.textContent = "Create Asset";
  if (showNoticeFlag) {
    showNotice("Asset form reset for a new record.", "info");
  }
}

function populateAssetForm(asset) {
  state.editingAssetId = asset.id;
  setFormValue(refs.assetForm, "name", asset.name);
  setFormValue(refs.assetForm, "address", asset.address);
  setFormValue(refs.assetForm, "commissioned_year", asset.commissioned_year);
  setFormValue(refs.assetForm, "purpose", asset.purpose);
  setFormValue(refs.assetForm, "responsibility_class", asset.responsibility_class);
  refs.assetModePill.textContent = "Update mode";
  refs.assetHint.textContent = `Editing asset #${asset.id}. Save to update the stored passport.`;
  refs.assetSubmitBtn.textContent = "Update Asset";
}

function resetElementForm(showNoticeFlag = false) {
  refs.elementForm.reset();
  refs.zoneRows.innerHTML = "";
  defaultZoneRows().forEach((row) => addZoneRow(row));
  syncSectionFields();
  state.editingElementId = null;
  refs.elementModePill.textContent = "Create mode";
  refs.elementHint.textContent = "Fill the geometry, zones, and action model or load a stored element for editing.";
  refs.elementSubmitBtn.textContent = "Create Element";
  if (showNoticeFlag) {
    showNotice("Element form reset for a new record.", "info");
  }
}

function populateElementForm(element) {
  resetElementForm();
  state.editingElementId = element.id;
  setFormValue(refs.elementForm, "element_id", element.element_id);
  setFormValue(refs.elementForm, "element_type", element.element_type);
  setFormValue(refs.elementForm, "steel_grade", element.steel_grade);
  setFormValue(refs.elementForm, "work_scheme", element.work_scheme);
  setFormValue(refs.elementForm, "operating_zone", element.operating_zone);
  setFormValue(refs.elementForm, "environment_category", element.environment_category);
  setFormValue(refs.elementForm, "current_service_life_years", element.current_service_life_years);
  setFormValue(refs.elementForm, "section_type", element.section.section_type);
  setFormValue(refs.elementForm, "reference_thickness_mm", element.section.reference_thickness_mm);
  setFormValue(refs.elementForm, "width_mm", element.section.width_mm);
  setFormValue(refs.elementForm, "thickness_mm", element.section.thickness_mm);
  setFormValue(refs.elementForm, "height_mm", element.section.height_mm);
  setFormValue(refs.elementForm, "flange_width_mm", element.section.flange_width_mm);
  setFormValue(refs.elementForm, "web_thickness_mm", element.section.web_thickness_mm);
  setFormValue(refs.elementForm, "flange_thickness_mm", element.section.flange_thickness_mm);
  setFormValue(refs.elementForm, "area0_mm2", element.section.area0_mm2);
  setFormValue(refs.elementForm, "inertia0_mm4", element.section.inertia0_mm4);
  setFormValue(refs.elementForm, "section_modulus0_mm3", element.section.section_modulus0_mm3);
  setFormValue(refs.elementForm, "fy_mpa", element.material.fy_mpa);
  setFormValue(refs.elementForm, "gamma_m", element.material.gamma_m);
  setFormValue(refs.elementForm, "stability_factor", element.material.stability_factor);
  setFormValue(refs.elementForm, "check_type", element.action.check_type);
  setFormValue(refs.elementForm, "demand_value", element.action.demand_value);
  setFormValue(refs.elementForm, "demand_growth_factor_per_year", element.action.demand_growth_factor_per_year);
  refs.zoneRows.innerHTML = "";
  element.zones.forEach((zone) => addZoneRow(zone));
  syncSectionFields();
  refs.elementModePill.textContent = "Update mode";
  refs.elementHint.textContent = `Editing element #${element.id}. Save to update geometry, zones, and design action data.`;
  refs.elementSubmitBtn.textContent = "Update Element";
}

function resetInspectionForm(showNoticeFlag = false) {
  refs.inspectionForm.reset();
  refs.measurementRows.innerHTML = "";
  defaultMeasurementRows().forEach((row) => addMeasurementRow(row));
  setFormValue(refs.inspectionForm, "performed_at", todayIso());
  state.editingInspectionId = null;
  refs.inspectionModePill.textContent = "Create mode";
  refs.inspectionHint.textContent = "Store a new inspection or click a saved one to update codes, findings, and measurements.";
  refs.inspectionSubmitBtn.textContent = "Save Inspection";
  if (showNoticeFlag) {
    showNotice("Inspection form reset for a new record.", "info");
  }
}

function populateInspectionForm(inspection) {
  resetInspectionForm();
  state.editingInspectionId = inspection.id;
  setFormValue(refs.inspectionForm, "inspection_code", inspection.inspection_code);
  setFormValue(refs.inspectionForm, "performed_at", inspection.performed_at);
  setFormValue(refs.inspectionForm, "method", inspection.method);
  setFormValue(refs.inspectionForm, "executor", inspection.executor);
  setFormValue(refs.inspectionForm, "findings", inspection.findings);
  refs.measurementRows.innerHTML = "";
  if (inspection.measurements.length) {
    inspection.measurements.forEach((measurement) => addMeasurementRow(measurement));
  } else {
    defaultMeasurementRows().forEach((row) => addMeasurementRow(row));
  }
  refs.inspectionModePill.textContent = "Update mode";
  refs.inspectionHint.textContent = `Editing inspection #${inspection.id}. Save to replace the stored findings and measurements.`;
  refs.inspectionSubmitBtn.textContent = "Update Inspection";
}

function clearDerivedOutputs() {
  state.calculation = null;
  state.reportPreview = null;
  state.reports = [];
  renderCalculationResult(null);
  renderReports([]);
  renderReportPreview();
}

function defaultZoneRows() {
  return [
    { zone_id: "top", role: "top_flange", initial_thickness_mm: 12, exposed_surfaces: 1, pitting_factor: 0, pit_loss_mm: 0 },
    { zone_id: "bottom", role: "bottom_flange", initial_thickness_mm: 12, exposed_surfaces: 1, pitting_factor: 0, pit_loss_mm: 0 },
    { zone_id: "web", role: "web", initial_thickness_mm: 8, exposed_surfaces: 2, pitting_factor: 0, pit_loss_mm: 0 },
  ];
}

function defaultMeasurementRows() {
  return [
    { zone_id: "web", point_id: "W-1", thickness_mm: 7.5, error_mm: 0.1, measured_at: todayIso(), quality: 0.95 },
  ];
}

function addZoneRow(initial = {}) {
  const row = refs.zoneRowTemplate.content.firstElementChild.cloneNode(true);
  fillRow(row, initial);
  attachRow(row, refs.zoneRows);
}

function addMeasurementRow(initial = {}) {
  const row = refs.measurementRowTemplate.content.firstElementChild.cloneNode(true);
  fillRow(row, initial);
  attachRow(row, refs.measurementRows);
}

function fillRow(row, values) {
  row.querySelectorAll("[data-field]").forEach((input) => {
    const value = values[input.dataset.field];
    if (value !== undefined && value !== null) {
      input.value = value;
    }
  });
}

function attachRow(row, target) {
  row.querySelector(".remove-row").addEventListener("click", () => row.remove());
  target.appendChild(row);
}

function collectRows(container) {
  return Array.from(container.querySelectorAll(".data-row")).map((row) => {
    const values = {};
    row.querySelectorAll("[data-field]").forEach((input) => {
      values[input.dataset.field] = input.value;
    });
    return values;
  }).filter((row) => Object.values(row).some((value) => value !== ""));
}

function syncSectionFields() {
  const sectionType = refs.sectionTypeSelect.value;
  document.querySelectorAll(".section-field").forEach((field) => field.classList.remove("visible"));
  document.querySelectorAll(`.${cssClassForSection(sectionType)}`).forEach((field) => field.classList.add("visible"));
}

function cssClassForSection(sectionType) {
  if (sectionType === "plate") return "plate-field";
  if (sectionType === "generic_reduced") return "generic-field";
  return "i-section-field";
}

function getLatestInspection() {
  if (!state.inspections.length) {
    return null;
  }
  const selected = state.inspections.find((item) => item.id === state.selectedInspectionId);
  if (selected) {
    return selected;
  }
  return [...state.inspections].sort((left, right) => String(right.performed_at).localeCompare(String(left.performed_at)))[0];
}

function setFormValue(form, name, value) {
  if (!form.elements[name]) {
    return;
  }
  form.elements[name].value = value ?? "";
}

function updateSelectedBadges() {
  const asset = state.assets.find((item) => item.id === state.selectedAssetId);
  const element = state.elements.find((item) => item.id === state.selectedElementId);
  refs.selectedAssetBadge.textContent = asset ? asset.name : "none";
  refs.selectedElementBadge.textContent = element ? element.element_id : "none";
}

async function api(url, options = {}) {
  const request = { method: options.method || "GET", headers: {} };
  if (options.json) {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(options.json);
  } else if (options.formData) {
    request.body = options.formData;
  }
  const response = await fetch(url, request);
  const body = await safeParseJson(response);
  if (!response.ok) {
    throw new Error(body?.detail || `Request failed with status ${response.status}`);
  }
  return body;
}

async function safeParseJson(response) {
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function showNotice(message, type = "info") {
  refs.notice.textContent = message;
  refs.notice.className = `notice ${type}`;
  window.clearTimeout(showNotice.timer);
  showNotice.timer = window.setTimeout(() => {
    refs.notice.className = "notice hidden";
  }, 4500);
}

function blankToNull(value) {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function compactObject(object) {
  return Object.fromEntries(Object.entries(object).filter(([, value]) => value !== null && value !== undefined && value !== ""));
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(String(value).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function integerOrNull(value) {
  const parsed = numberOrNull(value);
  return parsed == null ? null : Math.trunc(parsed);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatNumber(value, digits) {
  return Number(value).toFixed(digits);
}

function formatMaybeNumber(value, digits) {
  return value == null ? "-" : Number(value).toFixed(digits);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}
