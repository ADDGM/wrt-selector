import { mockElement } from "./setup.js";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createAsuRequestBuilder } from "../../www/js/asu.js";

/** Translation module fetches lang JSON after status updates; tests only care about ASU API calls. */
function fetchWithLangStub(handler) {
  return (url, opts) => {
    if (String(url).includes("langs/")) {
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve({ _: "stub" }),
      });
    }
    return handler(url, opts);
  };
}

function makeContext(overrides = {}) {
  return {
    config: { asu_url: "http://asu.example.com" },
    progress: {},
    ofsVersion: "1.0",
    getCurrentDevice: () => ({}),
    updateImages: () => {},
    ...overrides,
  };
}

describe("createAsuRequestBuilder", () => {
  it("pins polling, device and downloads to the submitted service", async () => {
    const service = { url: "https://third.example", rootfs_size_mb_max: 4096 };
    const device = { id: "original", target: "x86/64" };
    const requests = [];
    const states = [];
    let retry, result;
    const originalTimeout = globalThis.setTimeout;
    globalThis.setTimeout = (callback) => {
      retry = callback;
    };
    globalThis.fetch = fetchWithLangStub((url, options) => {
      requests.push({ url, ...options });
      return Promise.resolve(
        requests.length === 1
          ? { status: 202, json: async () => ({ request_hash: "queued" }) }
          : {
              status: 200,
              json: async () => ({
                version_number: "24.10.6",
                bin_dir: "result",
              }),
            }
      );
    });
    try {
      const build = createAsuRequestBuilder(
        makeContext({
          config: {
            asu_url: "https://official.example",
            asu_rootfs_size_mb: 2048,
          },
          getBuildService: () => service,
          getCurrentDevice: () => device,
          onBuildStateChange: (state) => states.push(state),
          updateImages: (_version, value) => {
            result = value;
          },
        })
      );
      await build();
      service.url = "https://different.example";
      device.id = "changed";
      await retry();
      assert.equal(JSON.parse(requests[0].body).rootfs_size_mb, 2048);
      assert.equal(
        requests[1].url,
        "https://third.example/api/v1/build/queued"
      );
      assert.equal(result.asu_image_url, "https://third.example/store/result");
      assert.equal(result.id, "original");
      assert.deepEqual(states, [true, false]);
    } finally {
      globalThis.setTimeout = originalTimeout;
    }
  });

  it("ignores a stale response after a newer build has started", async () => {
    const resolveResponses = [];
    const results = [];
    let selected = { url: "https://first.example", rootfs_size_mb_max: 1024 };
    globalThis.fetch = fetchWithLangStub(
      () => new Promise((resolve) => resolveResponses.push(resolve))
    );
    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "dev" }),
        getBuildService: () => selected,
        updateImages: (_version, value) => results.push(value.asu_image_url),
      })
    );
    const first = build();
    selected = { url: "https://second.example", rootfs_size_mb_max: 1024 };
    const second = build();
    const response = {
      status: 200,
      json: async () => ({ version_number: "v", bin_dir: "output" }),
    };
    resolveResponses[1](response);
    await second;
    resolveResponses[0](response);
    await first;
    assert.deepEqual(results, ["https://second.example/store/output"]);
  });

  it("unlocks the selection when the selected service is unreachable", async () => {
    const states = [];
    globalThis.fetch = fetchWithLangStub(() =>
      Promise.reject(new Error("Network error"))
    );
    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "dev" }),
        onBuildStateChange: (state) => states.push(state),
      })
    );
    await build();
    assert.deepEqual(states, [true, false]);
  });
  it("returns a function", () => {
    const build = createAsuRequestBuilder(makeContext());
    assert.equal(typeof build, "function");
  });

  it("does not call the ASU API when no device is selected", () => {
    let asuFetchCalled = false;
    globalThis.fetch = fetchWithLangStub(() => {
      asuFetchCalled = true;
      return Promise.resolve({ status: 200, json: () => Promise.resolve({}) });
    });

    const build = createAsuRequestBuilder(makeContext());
    build();
    assert.equal(asuFetchCalled, false);
  });

  it("does not call the ASU API when getCurrentDevice returns null", () => {
    let asuFetchCalled = false;
    globalThis.fetch = fetchWithLangStub(() => {
      asuFetchCalled = true;
      return Promise.resolve({ status: 200, json: () => Promise.resolve({}) });
    });

    const build = createAsuRequestBuilder(
      makeContext({ getCurrentDevice: () => null })
    );
    build();
    assert.equal(asuFetchCalled, false);
  });

  it("sends POST to the build API when device is selected", async () => {
    let capturedUrl, capturedMethod;
    globalThis.fetch = fetchWithLangStub((url, opts) => {
      capturedUrl = url;
      capturedMethod = opts.method;
      return Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve({ version_number: "23.05.4", bin_dir: "d" }),
      });
    });

    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "my-router", target: "ramips/mt7621" }),
      })
    );
    build();
    await new Promise((r) => setTimeout(r, 50));

    assert.equal(capturedUrl, "http://asu.example.com/api/v1/build");
    assert.equal(capturedMethod, "POST");
  });

  it("includes profile, target, and diff_packages in request body", async () => {
    let capturedBody;
    globalThis.fetch = fetchWithLangStub((_url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve({ version_number: "23.05.4", bin_dir: "d" }),
      });
    });

    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "my-router", target: "ramips/mt7621" }),
      })
    );
    build();
    await new Promise((r) => setTimeout(r, 50));

    assert.equal(capturedBody.profile, "my-router");
    assert.equal(capturedBody.target, "ramips/mt7621");
    assert.equal(capturedBody.diff_packages, true);
  });

  it("includes client version in request body", async () => {
    let capturedBody;
    globalThis.fetch = fetchWithLangStub((_url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve({ version_number: "23.05.4", bin_dir: "d" }),
      });
    });

    const build = createAsuRequestBuilder(
      makeContext({
        ofsVersion: "2.5.0",
        getCurrentDevice: () => ({ id: "dev", target: "t" }),
      })
    );
    build();
    await new Promise((r) => setTimeout(r, 50));

    assert.equal(capturedBody.client, "ofs/2.5.0");
  });

  it("includes resolved custom repositories and keys in request body", async () => {
    let capturedBody;
    const previousQuerySelector = document._qsImpl;
    const select = mockElement({ value: "23.05.4" });
    const qsMap = {
      "#versions": select,
    };
    document._qsImpl = (selector) => qsMap[selector] || mockElement();

    globalThis.fetch = fetchWithLangStub((_url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve({ version_number: "23.05.4", bin_dir: "d" }),
      });
    });

    const build = createAsuRequestBuilder(
      makeContext({
        config: {
          asu_url: "http://asu.example.com",
          asu_repositories: {
            custom:
              "https://repo.example/{openwrt_branch}/{openwrt_version}/{target}/{subtarget}",
          },
          asu_repository_keys: ["pubkey-1"],
          asu_repositories_mode: "append",
        },
        getCurrentDevice: () => ({ id: "dev", target: "ramips/mt7621" }),
      })
    );
    build();
    await new Promise((r) => setTimeout(r, 50));
    document._qsImpl = previousQuerySelector;

    assert.deepEqual(capturedBody.repositories, {
      custom: "https://repo.example/23.05/23.05.4/ramips/mt7621",
    });
    assert.deepEqual(capturedBody.repository_keys, ["pubkey-1"]);
    assert.equal(capturedBody.repositories_mode, "append");
  });

  it("omits repositories_mode for unsupported mode values", async () => {
    let capturedBody;
    globalThis.fetch = fetchWithLangStub((_url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve({ version_number: "23.05.4", bin_dir: "d" }),
      });
    });

    const build = createAsuRequestBuilder(
      makeContext({
        config: {
          asu_url: "http://asu.example.com",
          asu_repositories_mode: "unsupported",
        },
        getCurrentDevice: () => ({ id: "dev", target: "ramips/mt7621" }),
      })
    );
    build();
    await new Promise((r) => setTimeout(r, 50));

    assert.ok(!("repositories_mode" in capturedBody));
  });

  it("sends GET with hash appended when requestHash is provided", async () => {
    let capturedUrl, capturedMethod, capturedBody;
    globalThis.fetch = fetchWithLangStub((url, opts) => {
      capturedUrl = url;
      capturedMethod = opts.method;
      capturedBody = opts.body;
      return Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve({ version_number: "23.05.4", bin_dir: "d" }),
      });
    });

    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "dev", target: "t" }),
      })
    );
    build("hash123");
    await new Promise((r) => setTimeout(r, 50));

    assert.equal(capturedUrl, "http://asu.example.com/api/v1/build/hash123");
    assert.equal(capturedMethod, "GET");
    assert.equal(capturedBody, null);
  });

  it("calls updateImages with version and asu_image_url on 200", async () => {
    let updatedArgs;
    globalThis.fetch = fetchWithLangStub(() =>
      Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve({ version_number: "23.05.4", bin_dir: "output" }),
      })
    );

    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "dev", target: "t" }),
        updateImages: (...args) => {
          updatedArgs = args;
        },
      })
    );
    build();
    await new Promise((r) => setTimeout(r, 100));

    assert.equal(updatedArgs[0], "23.05.4");
    assert.equal(updatedArgs[1].id, "dev");
    assert.equal(
      updatedArgs[1].asu_image_url,
      "http://asu.example.com/store/output"
    );
  });

  it("handles network error without throwing", async () => {
    globalThis.fetch = fetchWithLangStub(() =>
      Promise.reject(new Error("Connection refused"))
    );

    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "dev", target: "t" }),
      })
    );

    assert.doesNotThrow(() => build());
    await new Promise((r) => setTimeout(r, 50));
  });

  it("submits advanced options from the page instead of merging removed presets back", async () => {
    let body;
    globalThis.fetch = fetchWithLangStub((_url, opts) => {
      body = JSON.parse(opts.body);
      return Promise.resolve({
        status: 200,
        json: async () => ({ version_number: "24.10.3", bin_dir: "d" }),
      });
    });
    const build = createAsuRequestBuilder(
      makeContext({
        config: {
          asu_url: "http://asu.example.com",
          asu_repositories: { preset: "https://preset.example.com" },
        },
        getCurrentDevice: () => ({ id: "dev", target: "ramips/mt7621" }),
        getBuildOptions: () => ({
          rootfs_size_mb: 512,
          repositories: { custom: "https://custom.example.com" },
          repositories_mode: "append",
          repository_keys: ["first\nkey", "second\nkey"],
        }),
      })
    );
    build();
    await new Promise(setImmediate);
    assert.equal(body.rootfs_size_mb, 512);
    assert.deepEqual(body.repositories, {
      custom: "https://custom.example.com",
    });
    assert.equal(body.repositories_mode, "append");
    assert.deepEqual(body.repository_keys, ["first\nkey", "second\nkey"]);
  });

  it("blocks invalid size before requesting or clearing existing downloads", () => {
    let apiCalls = 0;
    let removals = 0;
    const previousQsa = document._qsaImpl;
    document._qsaImpl = (selector) =>
      selector.startsWith("#download")
        ? [mockElement({ remove: () => removals++ })]
        : [];
    globalThis.fetch = fetchWithLangStub(() => {
      apiCalls++;
      return Promise.resolve({ status: 200, json: async () => ({}) });
    });
    try {
      createAsuRequestBuilder(
        makeContext({
          config: {
            asu_url: "http://asu.example.com",
            asu_rootfs_size_mb: 2048,
          },
          getCurrentDevice: () => ({ id: "dev", target: "ramips/mt7621" }),
        })
      )();
      assert.equal(apiCalls, 0);
      assert.equal(removals, 0);
    } finally {
      document._qsaImpl = previousQsa;
    }
  });

  it("polls a queued build without reading edited form options again", async () => {
    let reads = 0;
    let retry;
    const calls = [];
    const previousTimeout = globalThis.setTimeout;
    globalThis.setTimeout = (callback, delay) => {
      assert.equal(delay, 5000);
      retry = callback;
    };
    globalThis.fetch = fetchWithLangStub((url, opts) => {
      calls.push({ url, ...opts });
      return Promise.resolve(
        calls.length === 1
          ? { status: 202, json: async () => ({ request_hash: "queued-hash" }) }
          : {
              status: 200,
              json: async () => ({ version_number: "24.10.3", bin_dir: "d" }),
            }
      );
    });
    try {
      createAsuRequestBuilder(
        makeContext({
          getCurrentDevice: () => ({ id: "dev", target: "ramips/mt7621" }),
          getBuildOptions: () => {
            if (++reads > 1)
              throw new Error("Form was edited after submission");
            return { rootfs_size_mb: 256 };
          },
        })
      )();
      await new Promise(setImmediate);
      assert.equal(typeof retry, "function");
      retry();
      await new Promise(setImmediate);
      assert.equal(reads, 1);
      assert.equal(calls.length, 2);
      assert.equal(
        calls[1].url,
        "http://asu.example.com/api/v1/build/queued-hash"
      );
      assert.equal(calls[1].method, "GET");
      assert.equal(calls[1].body, null);
    } finally {
      globalThis.setTimeout = previousTimeout;
    }
  });

  it("handles non-200/202 response without throwing", async () => {
    globalThis.fetch = fetchWithLangStub(() =>
      Promise.resolve({
        status: 500,
        json: () => Promise.resolve({ detail: "Internal error" }),
      })
    );

    const build = createAsuRequestBuilder(
      makeContext({
        getCurrentDevice: () => ({ id: "dev", target: "t" }),
      })
    );

    assert.doesNotThrow(() => build());
    await new Promise((r) => setTimeout(r, 100));
  });
});
