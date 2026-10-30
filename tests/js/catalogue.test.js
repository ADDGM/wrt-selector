import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createCatalogueLoader } from "../../www/js/catalogue.js";

function response(data = {}, status = 200) {
  return { ok: status === 200, status, json: async () => data };
}

const url = "https://downloads.openwrt.org/releases/25.12.6/.overview.json";

describe("catalogue requests", () => {
  it("shares pending requests and cached data without sharing mutable results", async () => {
    let finish;
    let calls = 0;
    const load = createCatalogueLoader({
      fetchImpl: () => {
        calls++;
        return new Promise((resolve) => (finish = resolve));
      },
    });
    const first = load(url);
    const second = load(url);
    assert.equal(calls, 1);
    finish(response({ profiles: [{ id: "device", titles: ["original"] }] }));
    const [one, two] = await Promise.all([first, second]);
    one.profiles[0].titles[0] = "changed";
    one.profiles = {};
    assert.deepEqual((await load(url)).profiles, two.profiles);
    assert.equal(two.profiles[0].titles[0], "original");
    assert.equal(calls, 1);
  });

  it("keys data by the full URL, isolating systems and versions", async () => {
    const calls = [];
    const load = createCatalogueLoader({
      fetchImpl: async (address) => {
        calls.push(address);
        return response({ address });
      },
    });
    const urls = [
      url,
      url.replace("openwrt", "immortalwrt"),
      url.replace("25.12.6", "24.10.4"),
    ];
    for (const address of urls)
      assert.equal((await load(address)).address, address);
    await load(url);
    assert.deepEqual(calls, urls);
  });

  it("refreshes after five minutes and after a new page loader is created", async () => {
    let time = 0;
    let calls = 0;
    const options = {
      now: () => time,
      fetchImpl: async () => response({ revision: ++calls }),
    };
    const load = createCatalogueLoader(options);
    assert.equal((await load(url)).revision, 1);
    time = 299999;
    assert.equal((await load(url)).revision, 1);
    time = 300000;
    assert.equal((await load(url)).revision, 2);
    assert.equal((await createCatalogueLoader(options)(url)).revision, 3);
  });

  it("coalesces requests even while the first response is slow", async () => {
    let time = 0;
    let calls = 0;
    let finish;
    const load = createCatalogueLoader({
      now: () => time,
      fetchImpl: () => {
        calls++;
        return new Promise((resolve) => (finish = resolve));
      },
    });
    const first = load(url);
    time = 300001;
    const second = load(url);
    assert.equal(calls, 1);
    finish(response());
    await Promise.all([first, second]);
    await load(url);
    assert.equal(calls, 1);
  });

  it("recovers from HTTP 501 with one delayed reload, shared by all callers", async () => {
    const requests = [];
    const delays = [];
    const load = createCatalogueLoader({
      fetchImpl: async (address, options) => {
        requests.push({ address, ...options });
        return response({ profiles: [] }, requests.length === 1 ? 501 : 200);
      },
      pause: async (ms) => delays.push(ms),
    });
    assert.deepEqual(await Promise.all([load(url), load(url)]), [
      { profiles: [] },
      { profiles: [] },
    ]);
    assert.deepEqual(requests, [
      { address: url, cache: "no-cache" },
      { address: url, cache: "reload" },
    ]);
    assert.deepEqual(delays, [500]);
    await load(url);
    assert.equal(requests.length, 2);
  });

  it("retries network errors once and leaves failed requests available for retry", async () => {
    let calls = 0;
    const load = createCatalogueLoader({
      fetchImpl: async () => {
        if (++calls <= 2) throw new TypeError("Failed to fetch");
        return response({ recovered: true });
      },
      pause: async () => {},
    });
    await assert.rejects(load(url), /Failed to fetch/);
    assert.equal(calls, 2);
    assert.deepEqual(await load(url), { recovered: true });
    assert.equal(calls, 3);
  });

  it("reports the URL and HTTP status after persistent server errors", async () => {
    let calls = 0;
    const load = createCatalogueLoader({
      fetchImpl: async () => {
        calls++;
        return response({}, 503);
      },
      pause: async () => {},
    });
    await assert.rejects(load(url), (error) => {
      assert.equal(error.status, 503);
      assert.ok(error.message.includes(url));
      assert.match(error.message, /HTTP 503/);
      return true;
    });
    assert.equal(calls, 2);
    await assert.rejects(load(url));
    assert.equal(calls, 4);
  });

  it("does not retry or cache missing files and invalid JSON", async () => {
    let calls = 0;
    const load = createCatalogueLoader({
      fetchImpl: async () => {
        calls++;
        if (calls === 1) return response({}, 404);
        if (calls === 2)
          return {
            ok: true,
            json: async () => {
              throw new SyntaxError("Invalid JSON");
            },
          };
        return response({ recovered: true });
      },
      pause: async () => assert.fail("Not a transient error"),
    });
    await assert.rejects(load(url), /HTTP 404/);
    await assert.rejects(load(url), /Invalid JSON/);
    assert.deepEqual(await load(url), { recovered: true });
    assert.equal(calls, 3);
  });

  it("bounds the completed cache when browsing many versions", async () => {
    let calls = 0;
    const load = createCatalogueLoader({
      fetchImpl: async () => response({ request: ++calls }),
    });
    for (let version = 0; version < 33; version++)
      await load(`${url}?v=${version}`);
    assert.equal((await load(`${url}?v=32`)).request, 33);
    assert.equal((await load(`${url}?v=0`)).request, 34);
  });
});
