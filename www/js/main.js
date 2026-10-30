import { $, $$, show, showAlert, hideAlert } from "./utils.js";
import { initTranslation } from "./translation.js";
import { createAsuRequestBuilder } from "./asu.js";
import { setupBuildOptions } from "./build-options.js";
import { getAsuServices, selectAsuService } from "./asu-services.js";
import { updateImages } from "./images.js";
import { setupUciDefaults } from "./uci-defaults.js";
import { createCatalogueLoader } from "./catalogue.js";
import {
  insertSnapshotVersions,
  normalizeOverviewProfiles,
  setModel,
  setupProfilesAutocomplete,
  setupSelectList,
} from "./models.js";

let currentDevice = {};
let urlParams;
let customDevicePackages = {};
let getBuildOptions;
let getBuildService;
let catalogueGeneration = 0;
const loadCatalogueJson = createCatalogueLoader();
let isBuilding = false;
const ofsVersion = "%GIT_VERSION%";
const progress = {
  "tr-init": 5,
  "tr-queued": 10,
  "tr-started": 12,
  "tr-container-setup": 15,
  "tr-download-imagebuilder": 20,
  "tr-validate-revision": 25,
  "tr-validate-manifest": 30,
  "tr-unpack-imagebuilder": 40,
  "tr-calculate-packages-hash": 60,
  "tr-building-image": 80,
};

const config = window.config;

function setCurrentDevice(next) {
  currentDevice = next;
}

function updateImagesBound(version, mobj) {
  const service = getBuildService();
  return updateImages(version, mobj, {
    config: {
      ...config,
      asu_extra_packages: service.asu_extra_packages,
      info_url: service.info_url ?? config.info_url,
    },
    currentDevice,
    customDevicePackages,
  });
}

const buildAsuRequest = createAsuRequestBuilder({
  config,
  progress,
  ofsVersion,
  getCurrentDevice: () => currentDevice,
  updateImages: updateImagesBound,
  getBuildService: () => getBuildService(),
  getBuildOptions: (device, version, service) =>
    getBuildOptions(device, version, service),
  onBuildStateChange: (building) => {
    isBuilding = building;
    for (const selector of [
      "#firmware-distribution",
      "#asu-service",
      "#versions",
      "#models",
    ])
      $(selector).disabled = building;
    $("#asu-request-build").setAttribute("aria-disabled", String(building));
  },
});

async function loadCatalogue(service, params) {
  const generation = ++catalogueGeneration;
  let overviewGeneration = 0;
  currentDevice = {};
  const models = $("#models");
  models.value = "";
  models.disabled = true;
  models.oninput = null;
  models.onkeyup = null;
  $$(".autocomplete-items").forEach((item) => item.remove());
  updateImagesBound();
  hideAlert();
  const versionsSelect = $("#versions").cloneNode(false);
  versionsSelect.disabled = true;
  $("#versions").replaceWith(versionsSelect);

  try {
    const upstream = await loadCatalogueJson(
      service.image_url + "/.versions.json"
    ).catch((error) => {
      if (service.versions && error.status) return { versions_list: [] };
      throw error;
    });
    if (generation !== catalogueGeneration) return;
    let versions = service.versions
      ? [...service.versions]
      : (upstream.versions_list || []).filter(
          (version) => !/^(19\.07\.\d|18\.06\.\d|17\.01\.\d)$/.test(version)
        );
    if (!service.versions) {
      if (config.upcoming_version && upstream.upcoming_version)
        versions.push(upstream.upcoming_version);
      if (service.show_snapshots ?? config.show_snapshots)
        insertSnapshotVersions(versions);
    }
    versions = [...new Set(versions)];
    if (!versions.length)
      throw new Error("No firmware versions available for this service");
    const defaultVersion = service.default_version || upstream.stable_version;
    const selectionParams = new URLSearchParams(params);
    if (!versions.includes(selectionParams.get("version")))
      selectionParams.delete("version");
    config.overview_urls = {};
    config.image_urls = {};
    for (const version of versions) {
      const path = version === "SNAPSHOT" ? "snapshots" : `releases/${version}`;
      config.overview_urls[version] = `${service.image_url}/${path}`;
      config.image_urls[version] = `${
        upstream.image_url_override || service.image_url
      }/${path}`;
    }
    versionsSelect.disabled = false;
    setupSelectList(
      versionsSelect,
      versions,
      async (version) => {
        const overviewId = ++overviewGeneration;
        const isCurrent = () =>
          generation === catalogueGeneration &&
          overviewId === overviewGeneration;
        const previousDevice = currentDevice;
        currentDevice = {};
        models.disabled = true;
        models.oninput = null;
        models.onkeyup = null;
        $$(".autocomplete-items").forEach((item) => item.remove());
        updateImagesBound();
        hideAlert();
        try {
          const data = await loadCatalogueJson(
            `${config.overview_urls[version]}/.overview.json`
          );
          if (!isCurrent()) return;
          const overview = normalizeOverviewProfiles(data);
          const update = (...args) => {
            if (isCurrent()) updateImagesBound(...args);
          };
          setupProfilesAutocomplete(version, overview, {
            updateImages: update,
            changeModelContext: {
              isCurrent,
              config: { ...config },
              updateImages: update,
              setCurrentDevice: (device) => {
                if (isCurrent()) setCurrentDevice(device);
              },
            },
          });
          models.disabled = false;
          hideAlert();
          setModel(
            overview,
            previousDevice.target || selectionParams.get("target"),
            previousDevice.id || selectionParams.get("id")
          );
          models.onkeyup?.();
        } catch (error) {
          if (isCurrent()) showAlert(error.message);
        }
      },
      selectionParams,
      {
        ...config,
        default_version: versions.includes(defaultVersion)
          ? defaultVersion
          : versions[0],
      }
    );
  } catch (error) {
    if (generation === catalogueGeneration) showAlert(error.message);
  }
}

async function init() {
  urlParams = new URLSearchParams(window.location.search);
  $("#ofs-version").innerText = ofsVersion;
  initTranslation();
  try {
    const services = getAsuServices(config);
    const select = $("#asu-service");
    const distributionSelect = $("#firmware-distribution");
    for (const distribution of new Set(
      services.map((service) => service.distribution)
    )) {
      const option = document.createElement("option");
      option.value = distribution;
      option.textContent = distribution;
      distributionSelect.appendChild(option);
    }
    const populateServices = (selected) => {
      distributionSelect.value = selected.distribution;
      select.replaceChildren();
      for (const service of services.filter(
        (item) => item.distribution === selected.distribution
      )) {
        const option = document.createElement("option");
        option.value = service.id;
        option.textContent = service.name;
        select.appendChild(option);
      }
      select.value = selected.id;
    };
    populateServices(selectAsuService(services, config, urlParams.get("asu")));
    getBuildService = () =>
      services.find((service) => service.id === select.value);
    const updateService = () => {
      const service = getBuildService();
      config.asu_service_id = service.id;
      $("#asu-service-url").href = service.url;
      $("#asu-service-url").textContent = service.url;
      $("#firmware-source-url").href = service.image_url;
      $("#firmware-source-url").textContent = service.image_url;
      $("#all-downloads").href = service.image_url;
      $("#image-distribution").textContent = service.distribution;
      $("#image-service").textContent = service.name;
      return service;
    };
    updateService();
    show("#firmware-distribution-field");
    if (services.some((service) => service.url)) {
      show("#asu");
      show("#asu-service-field");
    }
    const syncUciDefaults = setupUciDefaults(config, getBuildService);
    getBuildOptions = setupBuildOptions(config, getBuildService);
    distributionSelect.addEventListener("change", () => {
      populateServices(
        selectAsuService(services, config, undefined, distributionSelect.value)
      );
      select.dispatchEvent(new Event("change"));
    });
    select.addEventListener("change", () => {
      const service = updateService();
      syncUciDefaults();
      const nextUrl = new URL(window.location.href);
      nextUrl.search = new URLSearchParams({ asu: service.id });
      history.replaceState(null, null, nextUrl);
      loadCatalogue(service, new URLSearchParams());
    });
    $("#asu-request-build").addEventListener("click", (event) => {
      event.preventDefault();
      if (!isBuilding) buildAsuRequest();
    });
    customDevicePackages = await fetch("device_packages.json", {
      cache: "no-cache",
    })
      .then((response) => (response.ok ? response.json() : {}))
      .catch(() => ({}));
    await loadCatalogue(getBuildService(), urlParams);
  } catch (error) {
    showAlert(error.message);
  }
}

document.addEventListener("DOMContentLoaded", init);
