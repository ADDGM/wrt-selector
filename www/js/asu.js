import { $, $$, hide, show, split } from "./utils.js";
import { translate } from "./translation.js";
import {
  buildOptionMessages,
  buildOptionsFromConfig,
  prepareBuildOptions,
} from "./build-options.js";
import { getAsuServices, selectAsuService } from "./asu-services.js";

export function createAsuRequestBuilder(context) {
  const {
    config,
    progress,
    ofsVersion,
    getCurrentDevice,
    updateImages,
    getBuildService = () => selectAsuService(getAsuServices(config), config),
    getBuildOptions = (device, version, service) =>
      prepareBuildOptions(
        buildOptionsFromConfig(config),
        device,
        version,
        service.rootfs_size_mb_max
      ),
    onBuildStateChange = () => {},
  } = context;
  let activeBuild = 0;

  function showStatus(message, loading, type) {
    const bs = $("#asu-buildstatus");
    switch (type) {
      case "error":
        bs.classList.remove("asu-info");
        bs.classList.add("asu-error");
        show(bs);
        break;
      case "info":
        bs.classList.remove("asu-error");
        bs.classList.add("asu-info");
        show(bs);
        break;
      default:
        hide(bs);
        break;
    }

    const tr = message.startsWith("tr-") ? message.replaceAll("_", "-") : "";
    const spanContainer = $("#asu-buildstatus span");
    spanContainer.textContent = "";

    if (loading) {
      const progressElem = document.createElement("progress");
      progressElem.style.marginRight = "10px";
      progressElem.max = 100;
      if (progress[tr]) {
        progressElem.value = progress[tr];
      }
      spanContainer.appendChild(progressElem);
    }

    const msgSpan = document.createElement("span");
    if (tr) {
      msgSpan.className = tr;
    }
    msgSpan.textContent = buildOptionMessages[message] || message;
    spanContainer.appendChild(msgSpan);

    translate();
  }

  function buildAsuRequest(requestHash, pending) {
    if (pending && pending.id !== activeBuild) return;
    const currentDevice = pending?.device || getCurrentDevice();
    if (!currentDevice || !currentDevice.id) {
      showStatus("bad profile", false, "error");
      return;
    }

    let buildBody;
    let task = pending;
    try {
      if (!task)
        task = {
          device: { ...currentDevice },
          service: { ...getBuildService() },
        };
      if (!task.service.url) throw new Error("No ASU service configured");
      if (!requestHash) {
        const selectedVersion = $("#versions").value;
        buildBody = {
          profile: currentDevice.id,
          target: currentDevice.target,
          packages: split($("#asu-packages").value),
          defaults: $("#uci-defaults-content").value,
          version_code: $("#image-code").innerText,
          version: selectedVersion,
          diff_packages: true,
          client: "ofs/" + ofsVersion,
          ...getBuildOptions(task.device, selectedVersion, task.service),
        };
      }
    } catch (error) {
      showStatus(error.message, false, "error");
      return;
    }
    if (!pending) {
      task.id = ++activeBuild;
      onBuildStateChange(true);
    }
    $$("#download-table1 *").forEach((e) => e.remove());
    $$("#download-links2 *").forEach((e) => e.remove());
    $$("#download-extras2 *").forEach((e) => e.remove());
    hide("#asu-log");
    const requestUrl =
      `${task.service.url}/api/v1/build` +
      (requestHash ? `/${encodeURIComponent(requestHash)}` : "");

    return fetch(requestUrl, {
      cache: "no-cache",
      method: requestHash ? "GET" : "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: requestHash ? null : JSON.stringify(buildBody),
    })
      .then(async (response) => {
        const mobj = await response.json();
        if (task.id !== activeBuild) return;
        if (response.status !== 202) {
          onBuildStateChange(false);
          if ("stderr" in mobj) {
            $("#asu-stderr").innerText = mobj.stderr;
            $("#asu-stdout").innerText = mobj.stdout;
            show("#asu-log");
          } else {
            hide("#asu-log");
          }
        }
        switch (response.status) {
          case 200:
            showStatus("tr-build-successful", false, "info");
            mobj.id = task.device.id;
            mobj.asu_image_url = task.service.url + "/store/" + mobj.bin_dir;
            updateImages(mobj.version_number, mobj);
            break;
          case 202:
            if (typeof mobj.request_hash !== "string" || !mobj.request_hash) {
              throw new Error("Missing ASU request hash");
            }
            showStatus(
              `tr-${mobj.imagebuilder_status || mobj.detail || "init"}`,
              true,
              "info"
            );
            if (mobj.queue_position) {
              $("#asu-buildstatus span").appendChild(
                document.createTextNode(` (${mobj.queue_position})`)
              );
            }
            setTimeout(() => buildAsuRequest(mobj.request_hash, task), 5000);
            break;
          default:
            if ("detail" in mobj) {
              showStatus(
                typeof mobj.detail === "string"
                  ? mobj.detail
                  : JSON.stringify(mobj.detail),
                false,
                "error"
              );
            } else if (
              "stderr" in mobj &&
              mobj.stderr.includes("images are too big")
            ) {
              showStatus("tr-build-size", false, "error");
            } else {
              showStatus("tr-build-failed", false, "error");
            }
            break;
        }
      })
      .catch((err) => {
        if (task.id !== activeBuild) return;
        onBuildStateChange(false);
        showStatus(err.message, false, "error");
      });
  }

  return buildAsuRequest;
}
