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
      showNotice("Перед импортом элементов выберите объект.", "error");
      return;
    }
    handleImportSubmit(event, `/api/v1/assets/${state.selectedAssetId}/import/elements`);
  });
  refs.inspectionImportForm.addEventListener("submit", (event) => {
    if (!state.selectedElementId) {
      event.preventDefault();
      showNotice("Перед импортом обследований выберите элемент.", "error");
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
    refs.healthBadge.textContent = result.status === "ok" ? "доступен" : result.status;
  } catch {
    refs.healthBadge.textContent = "офлайн";
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
    showNotice(`Объект "${asset.name}" ${isUpdate ? "обновлен" : "создан"}.`, "info");
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
    showNotice("Перед сохранением элемента создайте или выберите объект.", "error");
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
    showNotice(`Элемент "${element.element_id}" ${isUpdate ? "обновлен" : "создан"}.`, "info");
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
    showNotice("Перед сохранением обследования выберите элемент.", "error");
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
    showNotice(`Обследование ${isUpdate ? "обновлено" : "сохранено"}.`, "info");
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
    showNotice("Перед запуском расчета выберите элемент.", "error");
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
    showNotice("Инженерный расчет выполнен.", "info");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleReportPreview() {
  if (!state.selectedElementId) {
    showNotice("Перед предпросмотром отчета выберите элемент.", "error");
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
    showNotice("Предварительный просмотр отчета обновлен.", "info");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleReportSubmit(event) {
  event.preventDefault();
  if (!state.selectedElementId) {
    showNotice("Перед экспортом отчета выберите элемент.", "error");
    return;
  }

  const request = readReportRequest();
  if (!request.output_formats.length) {
    showNotice("Выберите хотя бы один формат экспорта.", "error");
    return;
  }

  try {
    const bundle = await api(`/api/v1/elements/${state.selectedElementId}/reports/baseline`, {
      method: "POST",
      json: request,
    });
    state.reports = bundle.artifacts;
    renderReports(bundle.artifacts);
    showNotice("Комплект отчетов сформирован.", "info");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function handleImportSubmit(event, url) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const fileInput = formElement.querySelector('input[type="file"]');
  if (!fileInput.files.length) {
    showNotice("Перед загрузкой выберите файл.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const summary = await api(url, { method: "POST", formData });
    prependImportSummary(summary);
    formElement.reset();
    clearDerivedOutputs();
    showNotice(`Импорт набора "${translateDatasetName(summary.dataset)}" завершен.`, "info");
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
  if (form.get("format_html")) outputFormats.push("html");
  if (form.get("format_md")) outputFormats.push("md");
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
      axial_force_kind: blankToNull(form.get("axial_force_kind")),
      axial_force_value: numberOrNull(form.get("axial_force_value")),
      bending_moment_value: numberOrNull(form.get("bending_moment_value")),
      effective_length_mm: numberOrNull(form.get("effective_length_mm")),
      effective_length_factor: numberOrNull(form.get("effective_length_factor")),
      support_condition: blankToNull(form.get("support_condition")),
      moment_amplification_factor: numberOrNull(form.get("moment_amplification_factor")),
      demand_growth_factor_per_year: numberOrNull(form.get("demand_growth_factor_per_year")) ?? 0,
    },
  });
}

function renderAssets() {
  const filter = refs.assetSearchInput.value.trim().toLowerCase();
  const filtered = state.assets.filter((asset) => `${asset.name} ${asset.address || ""} ${asset.purpose || ""}`.toLowerCase().includes(filter));
  if (!filtered.length) {
    refs.assetList.innerHTML = '<div class="muted-state">Объекты пока не добавлены.</div>';
    return;
  }
  refs.assetList.innerHTML = filtered.map((asset) => `
    <article class="registry-item ${asset.id === state.selectedAssetId ? "active" : ""}">
      <button type="button" data-asset-id="${asset.id}">${escapeHtml(asset.name)}</button>
      <div class="registry-meta">${escapeHtml(asset.address || "Адрес не указан")}<br>${escapeHtml(asset.purpose || "Назначение не указано")}</div>
      <div class="registry-tag">${asset.id === state.editingAssetId ? "Загружен в форму" : "Нажмите для редактирования"}</div>
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
    refs.elementList.innerHTML = '<div class="muted-state">Для выбранного объекта элементы отсутствуют.</div>';
    return;
  }
  refs.elementList.innerHTML = state.elements.map((element) => `
    <article class="registry-item ${element.id === state.selectedElementId ? "active" : ""}">
      <button type="button" data-element-id="${element.id}">${escapeHtml(element.element_id)}</button>
      <div class="registry-meta">${escapeHtml(element.element_type)}<br>${escapeHtml(element.environment_category)} | ${formatNumber(element.current_service_life_years, 1)} лет</div>
      <div class="registry-tag">${element.id === state.editingElementId ? "Загружен в форму" : "Нажмите для редактирования"}</div>
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
    refs.inspectionList.innerHTML = '<div class="muted-state">Для выбранного элемента обследования отсутствуют.</div>';
    return;
  }
  refs.inspectionList.innerHTML = state.inspections.map((inspection) => `
    <article class="registry-item ${inspection.id === state.selectedInspectionId ? "active" : ""}">
      <button type="button" data-inspection-id="${inspection.id}">${escapeHtml(inspection.inspection_code || `обследование-${inspection.id}`)}</button>
      <div class="registry-meta">${escapeHtml(inspection.performed_at)} | ${escapeHtml(inspection.method)}<br>замеров: ${inspection.measurements.length}</div>
      <div class="registry-tag">${inspection.id === state.editingInspectionId ? "Загружено в форму" : "Нажмите для редактирования"}</div>
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
    refs.calculationSummary.innerHTML = "Выберите элемент и выполните расчет.";
    refs.calculationSummary.classList.add("empty-block");
    refs.timelineChart.innerHTML = "Здесь появится график изменения показателей.";
    refs.timelineChart.classList.add("empty-block");
    refs.scenarioTable.innerHTML = "Здесь появится сравнение сценариев.";
    refs.scenarioTable.classList.add("empty-block");
    return;
  }

  const selectedElement = getSelectedElement();
  refs.calculationSummary.classList.remove("empty-block");
  refs.calculationSummary.innerHTML = `
    <article class="summary-card"><span>Среда</span><strong>${escapeHtml(result.environment_category)}</strong></article>
    <article class="summary-card"><span>Профиль сечения</span><strong>${selectedElement ? escapeHtml(translateSectionType(selectedElement.section.section_type)) : "-"}</strong></article>
    <article class="summary-card"><span>Режим прогноза</span><strong>${renderStatusPill(translateForecastMode(result.forecast_mode), toneForForecastMode(result.forecast_mode))}</strong></article>
    <article class="summary-card"><span>Количество сценариев</span><strong>${result.results.length}</strong></article>
    <article class="summary-card"><span>Доля превышений</span><strong>${formatNumber(result.risk_profile.exceedance_share, 3)}</strong></article>
    <article class="summary-card"><span>Класс уверенности</span><strong>${renderStatusPill(`Класс ${escapeHtml(result.engineering_confidence_level)}`, toneForConfidence(result.engineering_confidence_level))}</strong></article>
    <article class="summary-card"><span>Режим сопротивления</span><strong>${renderStatusPill(translateResistanceMode(result.resistance_mode), toneForResistanceMode(result.resistance_mode))}</strong></article>
    <article class="summary-card"><span>Режим редьюсера</span><strong>${renderStatusPill(translateReducerMode(result.reducer_mode), toneForReducerMode(result.reducer_mode))}</strong></article>
    <article class="summary-card"><span>Оценка скорости</span><strong>${renderStatusPill(translateRateFitMode(result.rate_fit_mode), toneForRateFitMode(result.rate_fit_mode))}</strong></article>
    <article class="summary-card"><span>Режим ML</span><strong>${renderStatusPill(translateMlMode(result.ml_mode), toneForMlMode(result.ml_mode))}</strong></article>
    <article class="summary-card"><span>Режим риска</span><strong>${renderStatusPill(translateRiskMode(result.risk_mode), toneForRiskMode(result.risk_mode))}</strong></article>
    <article class="summary-card"><span>Уровень uncertainty</span><strong>${renderStatusPill(translateUncertaintyLevel(result.uncertainty_level), toneForUncertaintyLevel(result.uncertainty_level))}</strong></article>
    <article class="summary-card"><span>Источник uncertainty</span><strong>${escapeHtml(translateUncertaintySource(result.uncertainty_source))}</strong></article>
    <article class="summary-card"><span>Интервал ресурса</span><strong>${formatLifeInterval(result.life_interval_years)}</strong></article>
    <article class="summary-card"><span>Поиск предельного состояния</span><strong>${escapeHtml(translateCrossingMode(result.crossing_search_mode))}</strong></article>
    <article class="summary-card"><span>Статус уточнения</span><strong>${escapeHtml(translateRefinementStatus(result.refinement_diagnostics?.status))}</strong></article>
    <article class="summary-card"><span>ML metadata</span><strong>${result.ml_candidate_count} | ${escapeHtml(result.ml_blend_mode || "-")}</strong></article>
    <article class="summary-card"><span>Использовано данных</span><strong>${result.used_inspection_count} обслед. / ${result.used_measurement_count} замеров</strong></article>
    <article class="summary-card"><span>Следующее обследование</span><strong>${formatNumber(result.risk_profile.next_inspection_within_years, 2)} лет</strong></article>
    <article class="summary-card"><span>Рекомендация</span><strong>${escapeHtml(result.risk_profile.recommended_action)}</strong></article>
    <article class="summary-card"><span>Fallback-статус</span><strong>${renderFallbackOverview(result.fallback_flags)}</strong></article>
    <article class="summary-card summary-card-wide"><span>Основания uncertainty band</span><strong>${escapeHtml((result.uncertainty_basis || []).join("; ") || "-")}</strong></article>
    ${renderWarningCard("Ограничения и предупреждения", result.warnings, result.fallback_flags, "Явные warning/fallback-флаги не зарегистрированы.")}
    ${renderWarningCard("Неопределенность и риск", result.uncertainty_warnings, [], "Дополнительные uncertainty warnings не зарегистрированы.")}
    ${renderDiagnosticCard(result, selectedElement)}
  `;

  refs.scenarioTable.classList.remove("empty-block");
  refs.scenarioTable.innerHTML = `
    <table class="table">
      <thead><tr><th>Сценарий</th><th>Несущая способность</th><th>Воздействие</th><th>Запас</th><th>Остаточный ресурс</th><th>Поиск</th><th>Режимы</th><th>Предупреждения</th><th>Состояние</th></tr></thead>
      <tbody>
        ${result.results.map((row) => `
          <tr>
            <td>${escapeHtml(row.scenario_name)}</td>
            <td>${formatNumber(row.resistance_value, 3)} ${escapeHtml(row.resistance_unit)}</td>
            <td>${formatNumber(row.demand_value, 3)} ${escapeHtml(row.demand_unit)}</td>
            <td>${formatNumber(row.margin_value, 3)}</td>
            <td>${renderLifeCell(row)}</td>
            <td>${escapeHtml(translateCrossingMode(row.crossing_search_mode))}<br><small>${escapeHtml(translateRefinementStatus(row.refinement_diagnostics?.status))} | ${row.crossing_refinement_iterations || 0} ит.</small></td>
            <td>${renderScenarioModes(row)}</td>
            <td>${renderScenarioWarnings(row)}</td>
            <td>${row.limit_state_reached_within_horizon ? "Достигнуто" : "Не достигнуто"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;

  const baseline = result.results[0];
  refs.timelineChart.classList.remove("empty-block");
  refs.timelineChart.innerHTML = renderTimelineChart(baseline.uncertainty_trajectories || baseline.timeline, baseline.resistance_unit);
}

function renderReportPreview() {
  const asset = state.assets.find((item) => item.id === state.selectedAssetId) || null;
  const element = state.elements.find((item) => item.id === state.selectedElementId) || null;
  const previewResult = state.reportPreview || state.calculation;
  const latestInspection = getLatestInspection();
  const request = readReportRequest();
  const reportTitle = request.report_title || "Отчет по остаточному ресурсу";
  const author = request.author || "Инженерная группа";
  const formats = request.output_formats.length ? request.output_formats.map((item) => item.toUpperCase()).join(", ") : "Формат не выбран";
  const previewNote = state.reportPreview
    ? "Предпросмотр синхронизирован с параметрами формы отчета."
    : state.calculation
      ? "Предпросмотр использует последний расчет, уже загруженный в память."
      : "Запустите предпросмотр отчета или инженерный расчет, чтобы добавить таблицы сценариев и рекомендации.";

  if (!element) {
    refs.reportPreview.classList.add("empty-block");
    refs.reportPreview.innerHTML = "Выберите элемент для формирования предварительного просмотра отчета.";
    return;
  }

  const scenarioTable = previewResult
    ? `
      <table class="table">
        <thead><tr><th>Сценарий</th><th>Запас</th><th>Остаточный ресурс</th><th>Поиск</th><th>Состояние</th></tr></thead>
        <tbody>
          ${previewResult.results.map((row) => `
            <tr>
              <td>${escapeHtml(row.scenario_name)}</td>
              <td>${formatNumber(row.margin_value, 3)}</td>
              <td>${renderLifeCell(row)}</td>
              <td>${escapeHtml(translateCrossingMode(row.crossing_search_mode))}</td>
              <td>${row.limit_state_reached_within_horizon ? "Достигнуто" : "Не достигнуто"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `
    : '<p class="muted-state">К предпросмотру еще не привязан расчетный снимок.</p>';

  refs.reportPreview.classList.remove("empty-block");
  refs.reportPreview.innerHTML = `
    <div class="preview-cover">
      <p class="eyebrow">Черновик отчета</p>
      <h3>${escapeHtml(reportTitle)}</h3>
      <p class="preview-text">${escapeHtml(asset ? asset.name : "Объект не выбран")} | ${escapeHtml(element.element_id)} | ${escapeHtml(element.environment_category)}</p>
      <p class="preview-note">${escapeHtml(previewNote)}</p>
    </div>
    <div class="summary-grid">
      <article class="summary-card"><span>Автор</span><strong>${escapeHtml(author)}</strong></article>
      <article class="summary-card"><span>Горизонт прогноза</span><strong>${formatMaybeNumber(request.forecast_horizon_years, 1)} лет</strong></article>
      <article class="summary-card"><span>Шаг по времени</span><strong>${formatMaybeNumber(request.time_step_years, 1)} лет</strong></article>
      <article class="summary-card"><span>Форматы</span><strong>${escapeHtml(formats)}</strong></article>
      <article class="summary-card"><span>База обследований</span><strong>${escapeHtml(latestInspection ? latestInspection.inspection_code || `обследование-${latestInspection.id}` : "Обследования отсутствуют")}</strong></article>
      <article class="summary-card"><span>Рекомендованное действие</span><strong>${escapeHtml(previewResult ? previewResult.risk_profile.recommended_action : "Расчет еще не выполнен")}</strong></article>
      <article class="summary-card"><span>Класс уверенности</span><strong>${previewResult ? renderStatusPill(`Класс ${escapeHtml(previewResult.engineering_confidence_level)}`, toneForConfidence(previewResult.engineering_confidence_level)) : "Ожидает расчет"}</strong></article>
      <article class="summary-card"><span>Режим риска</span><strong>${previewResult ? renderStatusPill(translateRiskMode(previewResult.risk_mode), toneForRiskMode(previewResult.risk_mode)) : "Ожидает расчет"}</strong></article>
      <article class="summary-card"><span>Уровень uncertainty</span><strong>${previewResult ? renderStatusPill(translateUncertaintyLevel(previewResult.uncertainty_level), toneForUncertaintyLevel(previewResult.uncertainty_level)) : "Ожидает расчет"}</strong></article>
      <article class="summary-card"><span>Интервал ресурса</span><strong>${previewResult ? formatLifeInterval(previewResult.life_interval_years) : "Ожидает расчет"}</strong></article>
      <article class="summary-card"><span>Режимы</span><strong>${previewResult ? renderModeStack([
        { label: translateForecastMode(previewResult.forecast_mode), tone: toneForForecastMode(previewResult.forecast_mode) },
        { label: translateResistanceMode(previewResult.resistance_mode), tone: toneForResistanceMode(previewResult.resistance_mode) },
        { label: translateReducerMode(previewResult.reducer_mode), tone: toneForReducerMode(previewResult.reducer_mode) },
      ]) : "Ожидает расчет"}</strong></article>
    </div>
    <div class="preview-grid">
      <section class="preview-section">
        <h3>Ожидаемые разделы</h3>
        <div class="preview-line"><strong>1.</strong><span>Паспорт объекта и контекст ответственности.</span></div>
        <div class="preview-line"><strong>2.</strong><span>Паспорт элемента с геометрией сечения, материалом и моделью зон.</span></div>
        <div class="preview-line"><strong>3.</strong><span>Сводка по обследованиям с последними замерами и выводами.</span></div>
        <div class="preview-line"><strong>4.</strong><span>Сравнение сценариев и изменение запаса несущей способности.</span></div>
        <div class="preview-line"><strong>5.</strong><span>Ограничения применимости, warning-флаги и fallback-режимы.</span></div>
        <div class="preview-line"><strong>6.</strong><span>Вывод по остаточному ресурсу и срок следующего обследования.</span></div>
      </section>
      <section class="preview-section">
        <h3>Снимок контекста</h3>
        <div class="preview-line"><strong>Объект</strong><span>${escapeHtml(asset ? asset.name : "Не загружен")}</span></div>
        <div class="preview-line"><strong>Элемент</strong><span>${escapeHtml(element.element_id)} (${escapeHtml(element.element_type)})</span></div>
        <div class="preview-line"><strong>Срок службы</strong><span>${formatNumber(element.current_service_life_years, 1)} лет</span></div>
        <div class="preview-line"><strong>Зоны</strong><span>${element.zones.length}</span></div>
        <div class="preview-line"><strong>Последнее обследование</strong><span>${escapeHtml(latestInspection ? latestInspection.performed_at : "Данные обследований отсутствуют")}</span></div>
        <div class="preview-line"><strong>Замеры</strong><span>${latestInspection ? latestInspection.measurements.length : 0}</span></div>
      </section>
      <section class="preview-section">
        <h3>Инженерная интерпретация</h3>
        <div class="preview-line"><strong>Режим прогноза</strong><span>${previewResult ? escapeHtml(translateForecastMode(previewResult.forecast_mode)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Режим сопротивления</strong><span>${previewResult ? escapeHtml(translateResistanceMode(previewResult.resistance_mode)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Режим редьюсера</strong><span>${previewResult ? escapeHtml(translateReducerMode(previewResult.reducer_mode)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Оценка скорости</strong><span>${previewResult ? escapeHtml(translateRateFitMode(previewResult.rate_fit_mode)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Режим ML</strong><span>${previewResult ? escapeHtml(translateMlMode(previewResult.ml_mode)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Поиск предельного состояния</strong><span>${previewResult ? escapeHtml(translateCrossingMode(previewResult.crossing_search_mode)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Статус уточнения</strong><span>${previewResult ? escapeHtml(translateRefinementStatus(previewResult.refinement_diagnostics?.status)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Источник uncertainty</strong><span>${previewResult ? escapeHtml(translateUncertaintySource(previewResult.uncertainty_source)) : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>Основания uncertainty band</strong><span>${previewResult ? escapeHtml((previewResult.uncertainty_basis || []).join("; ") || "-") : "Ожидает расчет"}</span></div>
        <div class="preview-line"><strong>История данных</strong><span>${previewResult ? `${previewResult.used_inspection_count} обслед. / ${previewResult.used_measurement_count} замеров` : "Ожидает расчет"}</span></div>
      </section>
    </div>
    <section class="preview-section">
      <h3>Фрагмент расчета</h3>
      ${scenarioTable}
    </section>
    <section class="preview-section">
      <h3>Ограничения и предупреждения</h3>
      ${previewResult
        ? renderWarningPanel(previewResult.warnings, previewResult.fallback_flags, "В текущем снимке явные warning/fallback-флаги не зафиксированы.")
        : '<p class="muted-state">После расчета здесь появятся ограничения применимости и предупреждения stage 2.</p>'}
    </section>
    <section class="preview-section">
      <h3>Неопределенность и риск</h3>
      ${previewResult
        ? renderWarningPanel(previewResult.uncertainty_warnings, [], "Дополнительные uncertainty warnings не зарегистрированы.")
        : '<p class="muted-state">После расчета здесь появятся замечания по uncertainty band и интервалу ресурса.</p>'}
    </section>
  `;
}

function renderLifeCell(row) {
  const interval = formatLifeInterval(row.life_interval_years);
  const nominal = formatMaybeNumber(row.remaining_life_nominal_years, 2);
  const conservative = formatMaybeNumber(row.remaining_life_conservative_years, 2);
  const upper = formatMaybeNumber(row.life_interval_years?.upper_years, 2);
  if (interval === "-" && nominal === "-" && conservative === "-" && upper === "-") {
    return "-";
  }
  return `${interval}<br><small>ном. ${nominal} / конс. ${conservative} / верх. ${upper}</small>`;
}

function renderScenarioModes(row) {
  return renderModeStack([
    { label: `Класс ${row.engineering_confidence_level}`, tone: toneForConfidence(row.engineering_confidence_level) },
    { label: `UQ ${translateUncertaintyLevel(row.uncertainty_level)}`, tone: toneForUncertaintyLevel(row.uncertainty_level) },
    { label: translateResistanceMode(row.resistance_mode), tone: toneForResistanceMode(row.resistance_mode) },
    { label: translateReducerMode(row.reducer_mode), tone: toneForReducerMode(row.reducer_mode) },
  ]);
}

function renderScenarioWarnings(row) {
  const items = [
    ...(row.warnings || []).map((warning) => `Предупреждение: ${warning}`),
    ...(row.uncertainty_warnings || []).map((warning) => `Uncertainty: ${warning}`),
    ...((row.refinement_diagnostics?.warnings || []).map((warning) => `Refinement: ${warning}`)),
    ...((row.fallback_flags || []).map((flag) => `Fallback: ${translateFallbackFlag(flag)}`)),
  ];
  if (!items.length) {
    return '<span class="muted-state">Без специальных предупреждений</span>';
  }
  return `<div class="scenario-note">${items.map((item) => escapeHtml(item)).join("<br>")}</div>`;
}

function renderWarningCard(title, warnings, fallbackFlags, emptyText) {
  return `
    <article class="summary-card summary-card-wide">
      <span>${escapeHtml(title)}</span>
      ${renderWarningPanel(warnings, fallbackFlags, emptyText)}
    </article>
  `;
}

function renderWarningPanel(warnings, fallbackFlags, emptyText) {
  const items = [
    ...((warnings || []).map((warning) => `Предупреждение: ${warning}`)),
    ...((fallbackFlags || []).map((flag) => `Fallback: ${translateFallbackFlag(flag)}`)),
  ];
  if (!items.length) {
    return `<p class="warning-empty">${escapeHtml(emptyText)}</p>`;
  }
  return `<ul class="warning-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderDiagnosticCard(result, element) {
  const profileItems = buildProfileLimitationItems(result, element);
  return `
    <article class="summary-card summary-card-wide">
      <span>Расширенная диагностика</span>
      <div class="diagnostic-stack">
        ${renderDiagnosticPanel("Rate fit и источники данных", buildRateFitDiagnosticItems(result), true)}
        ${renderDiagnosticPanel("Uncertainty band и refinement", buildUncertaintyDiagnosticItems(result))}
        ${renderDiagnosticPanel("Профиль, reducer и применимость", profileItems)}
      </div>
    </article>
  `;
}

function renderDiagnosticPanel(title, items, open = false) {
  const body = items.length
    ? `<ul class="diagnostic-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : '<p class="warning-empty">Дополнительная диагностика для этого блока не требуется.</p>';
  return `<details class="diagnostic-panel"${open ? " open" : ""}><summary>${escapeHtml(title)}</summary>${body}</details>`;
}

function buildRateFitDiagnosticItems(result) {
  return (result.zone_observations || []).map((observation) => {
    const warnings = observation.warnings?.length ? `; warnings: ${observation.warnings.join(" | ")}` : "";
    return `${observation.zone_id}: ${translateRateFitMode(observation.rate_fit_mode)}, source=${observation.source}, n=${observation.fit_sample_size || observation.used_points_count || 0}, span=${formatMaybeNumber(observation.history_span_years, 2)} y${warnings}`;
  });
}

function buildUncertaintyDiagnosticItems(result) {
  const items = [
    `uncertainty source: ${translateUncertaintySource(result.uncertainty_source)}`,
    `uncertainty level: ${translateUncertaintyLevel(result.uncertainty_level)}`,
    `refinement status: ${translateRefinementStatus(result.refinement_diagnostics?.status)}`,
    `crossing mode: ${translateCrossingMode(result.crossing_search_mode)}`,
    `life interval: ${formatLifeInterval(result.life_interval_years)}`,
  ];
  if (result.refinement_diagnostics?.bracket_width_years != null) {
    items.push(`bracket width: ${formatMaybeNumber(result.refinement_diagnostics.bracket_width_years, 2)} years`);
  }
  if (result.uncertainty_basis?.length) {
    items.push(`basis: ${result.uncertainty_basis.join(" | ")}`);
  }
  if (result.refinement_diagnostics?.warnings?.length) {
    items.push(`refinement warnings: ${result.refinement_diagnostics.warnings.join(" | ")}`);
  }
  return items;
}

function buildProfileLimitationItems(result, element) {
  const items = [];
  if (element?.section?.section_type) {
    items.push(`profile: ${translateSectionType(element.section.section_type)}`);
  }
  items.push(`reducer mode: ${translateReducerMode(result.reducer_mode)}`);
  items.push(`resistance mode: ${translateResistanceMode(result.resistance_mode)}`);
  items.push(`confidence: class ${result.engineering_confidence_level}`);
  if (result.fallback_flags?.length) {
    items.push(`fallback flags: ${result.fallback_flags.map((flag) => translateFallbackFlag(flag)).join(" | ")}`);
  }
  if (element?.section?.section_type === "angle") {
    items.push("angle reducer remains an engineering composite and is not a thin-walled torsional solver");
  }
  if (result.reducer_mode === "generic_fallback") {
    items.push("generic_reduced is an explicit fallback and should not be interpreted as a direct normative reducer");
  }
  return items;
}

function renderFallbackOverview(fallbackFlags) {
  if (!fallbackFlags || !fallbackFlags.length) {
    return renderStatusPill("fallback нет", "ok");
  }
  const visible = fallbackFlags.slice(0, 2).map((flag) => translateFallbackFlag(flag));
  const suffix = fallbackFlags.length > 2 ? ` +${fallbackFlags.length - 2}` : "";
  return `${renderStatusPill("fallback active", "danger")}<br><small>${escapeHtml(visible.join("; "))}${escapeHtml(suffix)}</small>`;
}

function renderModeStack(items) {
  return `<span class="meta-stack">${items.filter(Boolean).map((item) => renderStatusPill(item.label, item.tone)).join("")}</span>`;
}

function renderStatusPill(label, tone = "neutral") {
  return `<span class="status-pill ${tone}">${escapeHtml(label)}</span>`;
}

function translateForecastMode(mode) {
  if (mode === "baseline") return "Базовый";
  if (mode === "observed") return "По наблюдениям";
  if (mode === "hybrid") return "Гибридный";
  return mode || "-";
}

function translateResistanceMode(mode) {
  if (mode === "direct") return "Прямой";
  if (mode === "approximate") return "Приближенный";
  if (mode === "compression_enhanced") return "Сжатие enhanced";
  if (mode === "combined_basic") return "Комбинированный basic";
  if (mode === "combined_enhanced") return "Комбинированный enhanced";
  return mode || "-";
}

function translateReducerMode(mode) {
  if (mode === "direct") return "Прямой редьюсер";
  if (mode === "generic_fallback") return "Только fallback generic_reduced";
  return mode || "-";
}

function translateRateFitMode(mode) {
  if (mode === "robust_history_fit") return "Робастная история";
  if (mode === "robust_history_fit_low_confidence") return "Робастная история (low confidence)";
  if (mode === "two_point") return "Две точки";
  if (mode === "single_observation") return "Одно обследование";
  if (mode === "baseline_fallback") return "Базовый fallback";
  return mode || "-";
}

function translateRiskMode(mode) {
  if (mode === "engineering_uncertainty_band") return "Инженерный uncertainty band";
  if (mode === "scenario_risk") return "Сценарный риск";
  return mode || "-";
}

function translateUncertaintyLevel(level) {
  if (level === "low") return "Низкий";
  if (level === "moderate") return "Умеренный";
  if (level === "high") return "Высокий";
  if (level === "very_high") return "Очень высокий";
  return level || "-";
}

function translateUncertaintySource(source) {
  if (source === "scenario_library_only") return "Только сценарная библиотека";
  if (source === "inspection_history_band") return "Полоса по данным обследований";
  if (source === "inspection_history_limited") return "Ограниченная история обследований";
  if (source === "inspection_history_with_baseline_fallback") return "История с baseline fallback";
  return source || "-";
}

function translateCrossingMode(mode) {
  if (mode === "no_timeline") return "Нет временной диаграммы";
  if (mode === "already_reached") return "Уже достигнуто";
  if (mode === "coarse_bracket_linear") return "Линейная интерполяция";
  if (mode === "coarse_bracket_refined") return "Уточненный поиск";
  if (mode === "no_crossing_within_horizon") return "В горизонте не найдено";
  if (mode === "coarse_only") return "Грубая оценка";
  return mode || "-";
}

function translateRefinementStatus(status) {
  if (status === "no_timeline") return "Нет временной диаграммы";
  if (status === "already_reached") return "Уже достигнуто";
  if (status === "bracketed_crossing") return "Устойчивый интервал";
  if (status === "numerically_uncertain_crossing") return "Численно чувствительный интервал";
  if (status === "near_flat_no_crossing") return "Почти плоская кривая";
  if (status === "no_crossing_within_horizon") return "В горизонте не найдено";
  return status || "-";
}

function translateMlMode(mode) {
  if (mode === "trained") return "Обученный ансамбль";
  if (mode === "heuristic") return "Эвристика";
  if (mode === "fallback") return "Резервный fallback";
  return mode || "-";
}

function translateFallbackFlag(flag) {
  if (flag === "generic_reduced") {
    return "Эффективное сечение получено через generic_reduced как явный fallback-режим.";
  }
  if (flag && flag.startsWith("forecast_source:") && flag.endsWith(":baseline")) {
    const parts = flag.split(":");
    return `Зона ${parts[1]}: прогноз продолжен по baseline-модели.`;
  }
  if (flag && flag.startsWith("resistance_mode:")) {
    return `Режим сопротивления: ${translateResistanceMode(flag.split(":")[1])}.`;
  }
  return flag || "-";
}

function toneForConfidence(level) {
  if (level === "A") return "ok";
  if (level === "B") return "neutral";
  if (level === "C") return "warn";
  return "danger";
}

function toneForForecastMode(mode) {
  if (mode === "hybrid") return "ok";
  if (mode === "observed") return "neutral";
  return "warn";
}

function toneForResistanceMode(mode) {
  if (mode === "direct") return "ok";
  if (mode === "compression_enhanced") return "neutral";
  if (mode === "combined_enhanced") return "neutral";
  if (mode === "combined_basic") return "warn";
  if (mode === "approximate") return "warn";
  return "danger";
}

function toneForReducerMode(mode) {
  if (mode === "direct") return "ok";
  if (mode === "generic_fallback") return "danger";
  return "warn";
}

function toneForRateFitMode(mode) {
  if (mode === "robust_history_fit") return "ok";
  if (mode === "robust_history_fit_low_confidence") return "warn";
  if (mode === "two_point") return "neutral";
  if (mode === "single_observation") return "warn";
  return "danger";
}

function toneForRiskMode(mode) {
  if (mode === "engineering_uncertainty_band") return "warn";
  if (mode === "scenario_risk") return "neutral";
  return "neutral";
}

function toneForUncertaintyLevel(level) {
  if (level === "low") return "ok";
  if (level === "moderate") return "neutral";
  if (level === "high") return "warn";
  return "danger";
}

function toneForMlMode(mode) {
  if (mode === "trained") return "ok";
  if (mode === "heuristic") return "neutral";
  return "warn";
}

function renderTimelineChart(trajectoryInput, unit) {
  const trajectories = Array.isArray(trajectoryInput)
    ? { central: trajectoryInput, conservative: trajectoryInput, upper: trajectoryInput }
    : {
        central: trajectoryInput?.central || [],
        conservative: trajectoryInput?.conservative || trajectoryInput?.central || [],
        upper: trajectoryInput?.upper || trajectoryInput?.central || [],
      };
  const timeline = trajectories.central || [];
  if (!timeline.length) {
    return "Данные временной диаграммы отсутствуют.";
  }
  const width = 760;
  const height = 280;
  const margin = { top: 18, right: 18, bottom: 34, left: 54 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const ages = timeline.map((point) => point.age_years);
  const conservativeValues = (trajectories.conservative || []).map((point) => point.resistance_value);
  const upperValues = (trajectories.upper || []).map((point) => point.resistance_value);
  const values = timeline.flatMap((point) => [point.resistance_value, point.demand_value]).concat(conservativeValues, upperValues);
  const minAge = Math.min(...ages);
  const maxAge = Math.max(...ages);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const rangeAge = maxAge - minAge || 1;
  const rangeValue = maxValue - minValue || 1;
  const scaleX = (value) => margin.left + ((value - minAge) / rangeAge) * innerWidth;
  const scaleY = (value) => margin.top + innerHeight - ((value - minValue) / rangeValue) * innerHeight;
  const resistancePoints = timeline.map((point) => `${scaleX(point.age_years)},${scaleY(point.resistance_value)}`).join(" ");
  const conservativePoints = (trajectories.conservative || []).map((point) => `${scaleX(point.age_years)},${scaleY(point.resistance_value)}`).join(" ");
  const upperPoints = (trajectories.upper || []).map((point) => `${scaleX(point.age_years)},${scaleY(point.resistance_value)}`).join(" ");
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
      <span class="legend-item"><span class="legend-swatch" style="background:#1f6f8b"></span>R central (${escapeHtml(unit)})</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#4d9968"></span>R conservative (${escapeHtml(unit)})</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#7a5cc2"></span>R upper (${escapeHtml(unit)})</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#b6542d"></span>Воздействие (${escapeHtml(unit)})</span>
    </div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="График изменения инженерных траекторий сопротивления и воздействия">
      ${gridLines}
      ${xTicks}
      <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="#172126" stroke-width="1.2"></line>
      <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="#172126" stroke-width="1.2"></line>
      <polyline fill="none" stroke="#1f6f8b" stroke-width="3" points="${resistancePoints}"></polyline>
      <polyline fill="none" stroke="#4d9968" stroke-width="2.5" stroke-dasharray="8 6" points="${conservativePoints}"></polyline>
      <polyline fill="none" stroke="#7a5cc2" stroke-width="2.5" stroke-dasharray="3 5" points="${upperPoints}"></polyline>
      <polyline fill="none" stroke="#b6542d" stroke-width="3" points="${demandPoints}"></polyline>
      <text x="${width / 2}" y="${height - 6}" text-anchor="middle" fill="#5d696f" font-size="12">Возраст, лет</text>
    </svg>
  `;
}

function renderReports(artifacts) {
  if (!artifacts.length) {
    refs.reportResults.innerHTML = "Здесь появятся сформированные файлы отчета.";
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
      <a href="${artifact.download_url}">Скачать</a>
    </div>
  `).join("");
}

function prependImportSummary(summary) {
  refs.importResults.classList.remove("empty-block");
  const warnings = renderImportIssueList(summary.warning_details, "warning");
  const errors = renderImportIssueList(summary.errors, "error");
  refs.importResults.innerHTML = `
    <div class="file-link">
      <div>
        <strong>${escapeHtml(translateDatasetName(summary.dataset))}</strong>
        <small>${summary.source_format.toUpperCase()} | обработано ${summary.rows_processed} | создано ${summary.created_count} | обновлено ${summary.updated_count} | warnings ${summary.warning_count}</small>
        ${warnings}
        ${errors}
      </div>
    </div>
  ` + refs.importResults.innerHTML;
}

function renderImportIssueList(items, tone) {
  if (!items || !items.length) {
    return "";
  }
  return `<div class="registry-meta import-issues ${tone}">${items.map((item) => `${escapeHtml(item.row_reference)}${item.code ? ` [${escapeHtml(item.code)}]` : ""}: ${escapeHtml(item.message)}`).join("<br>")}</div>`;
}

function resetAssetForm(showNoticeFlag = false) {
  refs.assetForm.reset();
  state.editingAssetId = null;
  refs.assetModePill.textContent = "Режим создания";
  refs.assetHint.textContent = "Зарегистрируйте новый объект или выберите существующий для загрузки в форму.";
  refs.assetSubmitBtn.textContent = "Создать объект";
  if (showNoticeFlag) {
    showNotice("Форма объекта очищена для новой записи.", "info");
  }
}

function populateAssetForm(asset) {
  state.editingAssetId = asset.id;
  setFormValue(refs.assetForm, "name", asset.name);
  setFormValue(refs.assetForm, "address", asset.address);
  setFormValue(refs.assetForm, "commissioned_year", asset.commissioned_year);
  setFormValue(refs.assetForm, "purpose", asset.purpose);
  setFormValue(refs.assetForm, "responsibility_class", asset.responsibility_class);
  refs.assetModePill.textContent = "Режим редактирования";
  refs.assetHint.textContent = `Редактируется объект #${asset.id}. Сохраните форму для обновления паспорта.`;
  refs.assetSubmitBtn.textContent = "Обновить объект";
}

function resetElementForm(showNoticeFlag = false) {
  refs.elementForm.reset();
  refs.zoneRows.innerHTML = "";
  defaultZoneRows().forEach((row) => addZoneRow(row));
  syncSectionFields();
  state.editingElementId = null;
  refs.elementModePill.textContent = "Режим создания";
  refs.elementHint.textContent = "Заполните геометрию, зоны и расчетную схему либо загрузите сохраненный элемент для редактирования.";
  refs.elementSubmitBtn.textContent = "Создать элемент";
  if (showNoticeFlag) {
    showNotice("Форма элемента очищена для новой записи.", "info");
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
  setFormValue(refs.elementForm, "axial_force_kind", element.action.axial_force_kind);
  setFormValue(refs.elementForm, "axial_force_value", element.action.axial_force_value);
  setFormValue(refs.elementForm, "bending_moment_value", element.action.bending_moment_value);
  setFormValue(refs.elementForm, "effective_length_mm", element.action.effective_length_mm);
  setFormValue(refs.elementForm, "effective_length_factor", element.action.effective_length_factor);
  setFormValue(refs.elementForm, "support_condition", element.action.support_condition);
  setFormValue(refs.elementForm, "moment_amplification_factor", element.action.moment_amplification_factor);
  setFormValue(refs.elementForm, "demand_growth_factor_per_year", element.action.demand_growth_factor_per_year);
  refs.zoneRows.innerHTML = "";
  element.zones.forEach((zone) => addZoneRow(zone));
  syncSectionFields();
  refs.elementModePill.textContent = "Режим редактирования";
  refs.elementHint.textContent = `Редактируется элемент #${element.id}. Сохраните форму для обновления геометрии, зон и расчетных воздействий.`;
  refs.elementSubmitBtn.textContent = "Обновить элемент";
}

function resetInspectionForm(showNoticeFlag = false) {
  refs.inspectionForm.reset();
  refs.measurementRows.innerHTML = "";
  defaultMeasurementRows().forEach((row) => addMeasurementRow(row));
  setFormValue(refs.inspectionForm, "performed_at", todayIso());
  state.editingInspectionId = null;
  refs.inspectionModePill.textContent = "Режим создания";
  refs.inspectionHint.textContent = "Сохраните новое обследование или выберите существующее для обновления кода, выводов и замеров.";
  refs.inspectionSubmitBtn.textContent = "Сохранить обследование";
  if (showNoticeFlag) {
    showNotice("Форма обследования очищена для новой записи.", "info");
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
  refs.inspectionModePill.textContent = "Режим редактирования";
  refs.inspectionHint.textContent = `Редактируется обследование #${inspection.id}. Сохраните форму для замены выводов и замеров.`;
  refs.inspectionSubmitBtn.textContent = "Обновить обследование";
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

function getSelectedElement() {
  return state.elements.find((item) => item.id === state.selectedElementId) || null;
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
  refs.selectedAssetBadge.textContent = asset ? asset.name : "не выбран";
  refs.selectedElementBadge.textContent = element ? element.element_id : "не выбран";
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
    throw new Error(body?.detail || `Ошибка запроса, статус ${response.status}`);
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

function formatLifeInterval(interval) {
  if (!interval) return "-";
  const lower = formatMaybeNumber(interval.lower_years, 2);
  const upper = formatMaybeNumber(interval.upper_years, 2);
  if (lower === "-" && upper === "-") return "-";
  return `[${lower}; ${upper}] лет`;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function translateDatasetName(dataset) {
  if (dataset === "assets") return "объекты";
  if (dataset === "elements") return "элементы";
  if (dataset === "inspections") return "обследования";
  return dataset;
}

function translateSectionType(sectionType) {
  if (sectionType === "plate") return "Лист";
  if (sectionType === "i_section") return "Двутавр";
  if (sectionType === "channel") return "Швеллер";
  if (sectionType === "angle") return "Уголок";
  if (sectionType === "tube") return "Труба";
  if (sectionType === "generic_reduced") return "Обобщенное fallback";
  return sectionType || "-";
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}
