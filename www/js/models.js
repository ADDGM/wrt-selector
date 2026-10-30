import { $ } from "./utils.js";
import { hideAlert, showAlert } from "./utils.js";
import { setupAutocompleteList } from "./autocomplete.js";
import { getModelTitles } from "./images.js";

export function setupSelectList(select, items, onselection, urlParams, config) {
  items.sort((b, a) =>
    (a + (a.indexOf("-") < 0 ? "-Z" : "")).localeCompare(
      b + (b.indexOf("-") < 0 ? "-Z" : ""),
      undefined,
      { numeric: true }
    )
  );

  for (const item of items) {
    const option = document.createElement("OPTION");
    option.innerText = item;
    option.value = item;
    if (item === "latest") {
      option.innerText = "Latest";
      option.classList.add("tr-latest-releases");
    }
    select.appendChild(option);
  }

  const preselect = urlParams.get("version") || config.default_version;
  if (preselect) {
    $("#versions").value = preselect;
  }

  select.addEventListener("change", () => {
    onselection(items[select.selectedIndex]);
  });

  if (select.selectedIndex >= 0) {
    onselection(items[select.selectedIndex]);
  }
}

export function setModel(overview, target, id) {
  if (target && id) {
    const title = $("#models").value;
    for (const mobj of Object.values(overview.profiles)) {
      if ((mobj.target === target && mobj.id === id) || mobj.title === title) {
        $("#models").value = mobj.title;
        $("#models").oninput();
        return;
      }
    }
  }
}

export function changeModel(version, overview, title, context) {
  const {
    config,
    updateImages,
    setCurrentDevice,
    isCurrent = () => true,
  } = context;
  if (!isCurrent()) return;
  const entry = overview.profiles[title];
  const baseUrl = config.image_urls[version];
  if (entry) {
    return fetch(`${baseUrl}/targets/${entry.target}/profiles.json`, {
      cache: "no-cache",
    })
      .then((obj) => {
        if (obj.status !== 200) {
          throw new Error(`Failed to fetch ${obj.url}`);
        }
        return obj.json();
      })
      .then((mobj) => {
        if (!isCurrent()) return;
        hideAlert();
        mobj.id = entry.id;
        mobj.images = mobj.profiles[entry.id].images;
        mobj.titles = mobj.profiles[entry.id].titles;
        mobj.device_packages = mobj.profiles[entry.id].device_packages;
        setCurrentDevice({
          version: version,
          id: entry.id,
          target: entry.target,
        });
        updateImages(version, mobj);
      })
      .catch((err) => {
        if (isCurrent()) showAlert(err.message);
      });
  } else {
    updateImages();
    setCurrentDevice({});
  }
}

export function insertSnapshotVersions(versions) {
  for (const version of versions.slice()) {
    const branch = version.split(".").slice(0, -1).join(".") + "-SNAPSHOT";
    if (!versions.includes(branch)) {
      versions.push(branch);
    }
  }
  versions.push("SNAPSHOT");
}

export function setupProfilesAutocomplete(version, obj, context) {
  const { updateImages, changeModelContext } = context;
  const isCatalogueCurrent = changeModelContext.isCurrent || (() => true);
  let selectionGeneration = 0;
  const resetSelection = () => {
    if (!isCatalogueCurrent()) return;
    const selectionId = ++selectionGeneration;
    changeModelContext.setCurrentDevice({});
    updateImages();
    return selectionId;
  };
  setupAutocompleteList(
    $("#models"),
    Object.keys(obj.profiles),
    resetSelection,
    (selectList) => {
      const selectionId = resetSelection();
      if (selectionId === undefined) return;
      changeModel(version, obj, selectList.value, {
        ...changeModelContext,
        isCurrent: () =>
          isCatalogueCurrent() && selectionId === selectionGeneration,
      });
    }
  );
}

export function normalizeOverviewProfiles(obj) {
  const dups = {};
  const profiles = [];

  function resolveDuplicate(e) {
    const tu = e.title.toUpperCase();
    if (tu in dups) {
      e.title += ` (${e.target})`;
      const o = dups[tu];
      if (o.title.toUpperCase() === tu) {
        o.title += ` (${o.target})`;
      }
    } else {
      dups[tu] = e;
    }
  }

  for (const profile of obj.profiles) {
    for (const title of getModelTitles(profile.titles)) {
      if (title.length === 0) {
        console.warn(
          `Empty device title for model id: ${profile.target}, ${profile.id}`
        );
        continue;
      }

      const e = Object.assign({ id: profile.id, title: title }, profile);
      resolveDuplicate(e);
      profiles.push(e);
    }
  }

  obj.profiles = profiles.reduce((d, e) => ((d[e.title] = e), d), {});
  return obj;
}
