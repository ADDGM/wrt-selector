import "./setup.js";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  buildOptionsFromConfig,
  prepareBuildOptions,
} from "../../www/js/build-options.js";

const device = { id: "example", target: "ramips/mt7621" };
const prepare = (options) => prepareBuildOptions(options, device, "24.10.3");

describe("advanced build options", () => {
  it("validates against the selected service limit instead of one global limit", () => {
    for (const rootfsSize of [2048, 4096]) {
      assert.equal(
        prepareBuildOptions({ rootfsSize }, device, "24.10.6", 4096)
          .rootfs_size_mb,
        rootfsSize
      );
      assert.throws(
        () => prepareBuildOptions({ rootfsSize }, device, "24.10.6", 1024),
        { message: "tr-rootfs-invalid" }
      );
    }
    assert.throws(
      () => prepareBuildOptions({ rootfsSize: 4097 }, device, "24.10.6", 4096),
      { message: "tr-rootfs-invalid" }
    );
  });
  it("omits optional size and mode when no customizations are supplied", () => {
    assert.deepEqual(prepare(buildOptionsFromConfig({})), {
      repositories: {},
      repository_keys: [],
    });
    for (const rootfsSize of ["", "  ", null, undefined]) {
      assert.ok(!("rootfs_size_mb" in prepare({ rootfsSize })));
    }
  });

  it("sends integer sizes including both API limits", () => {
    for (const size of [1, 256, 1024]) {
      assert.equal(prepare({ rootfsSize: ` ${size} ` }).rootfs_size_mb, size);
    }
  });

  it("rejects zero, negatives, fractions, overflow and non-integer input", () => {
    for (const rootfsSize of [
      0,
      -1,
      0.5,
      1025,
      "256.5",
      "1e2",
      "bad",
      Infinity,
    ]) {
      assert.throws(() => prepare({ rootfsSize }), {
        message: "tr-rootfs-invalid",
        selector: "#asu-rootfs-size",
      });
    }
  });

  it("resolves all existing placeholders and defaults to append", () => {
    assert.deepEqual(
      prepare({
        repositories: [
          {
            name: " custom-feed.1 ",
            url: " https://example.com/{openwrt_branch}/{openwrt_version}/{target}/{subtarget} ",
          },
        ],
      }),
      {
        repositories: {
          "custom-feed.1": "https://example.com/24.10/24.10.3/ramips/mt7621",
        },
        repositories_mode: "append",
        repository_keys: [],
      }
    );
  });

  it("resolves release-branch and main snapshot versions", () => {
    for (const [version, branch] of [
      ["24.10-SNAPSHOT", "24.10"],
      ["SNAPSHOT", "SNAPSHOT"],
    ]) {
      const result = prepareBuildOptions(
        {
          repositories: [
            {
              name: "snapshot",
              url: "https://example.com/{openwrt_branch}/{openwrt_version}",
            },
          ],
        },
        device,
        version
      );
      assert.equal(
        result.repositories.snapshot,
        `https://example.com/${branch}/${version}`
      );
    }
  });

  it("preserves explicit replace and multiple feed URLs", () => {
    const result = prepare({
      repositoriesMode: "replace",
      repositories: [
        { name: "one", url: "https://example.com/one" },
        { name: "two", url: "http://example.com/two" },
      ],
    });
    assert.equal(result.repositories_mode, "replace");
    assert.equal(Object.keys(result.repositories).length, 2);
  });

  it("ignores empty rows but rejects partially completed rows", () => {
    assert.deepEqual(
      prepare({ repositories: [{ name: " ", url: " " }] }).repositories,
      {}
    );
    assert.throws(
      () =>
        prepare({ repositories: [{ name: "", url: "https://example.com" }] }),
      {
        message: "tr-repository-name-invalid",
        index: 0,
      }
    );
    assert.throws(
      () => prepare({ repositories: [{ name: "feed", url: "" }] }),
      {
        message: "tr-repository-url-invalid",
        index: 0,
      }
    );
  });

  it("rejects invalid and duplicate feed names without silently overwriting", () => {
    for (const name of ["bad name", "feed/path", "中文", "<script>"]) {
      assert.throws(
        () => prepare({ repositories: [{ name, url: "https://example.com" }] }),
        {
          message: "tr-repository-name-invalid",
        }
      );
    }
    assert.throws(
      () =>
        prepare({
          repositories: [
            { name: "feed", url: "https://example.com/one" },
            { name: " feed ", url: "https://example.com/two" },
          ],
        }),
      { message: "tr-repository-name-duplicate", index: 1 }
    );
  });

  it("rejects non-HTTP URLs, bad hosts, whitespace and unknown placeholders", () => {
    for (const url of [
      "javascript:alert(1)",
      "file:///etc/passwd",
      "/packages",
      "https://",
      "https://example.com:bad",
      "https://example.com/a b",
      "https://example.com/{typo}",
    ]) {
      assert.throws(() => prepare({ repositories: [{ name: "feed", url }] }), {
        message: "tr-repository-url-invalid",
      });
    }
  });

  it("preserves multiple multiline keys, normalizes CRLF and skips empty keys", () => {
    assert.deepEqual(
      prepare({
        repositoryKeys: [
          " untrusted comment: example\r\nRWQexample\r\n",
          "-----BEGIN PUBLIC KEY-----\nexample\n-----END PUBLIC KEY-----",
          " \n",
        ],
      }).repository_keys,
      [
        "untrusted comment: example\nRWQexample",
        "-----BEGIN PUBLIC KEY-----\nexample\n-----END PUBLIC KEY-----",
      ]
    );
  });

  it("initializes editable values without mutating config or restoring deleted rows", () => {
    const config = {
      asu_rootfs_size_mb: 256,
      asu_repositories_mode: "replace",
      asu_repositories: { preset: "https://example.com/packages" },
      asu_repository_keys: ["key"],
    };
    const before = structuredClone(config);
    const options = buildOptionsFromConfig(config);
    assert.equal(prepare(options).rootfs_size_mb, 256);
    assert.equal(prepare(options).repositories_mode, "replace");
    options.rootfsSize = "";
    options.repositories.splice(0);
    options.repositoryKeys.splice(0);
    assert.deepEqual(prepare(options), {
      repositories: {},
      repository_keys: [],
    });
    assert.deepEqual(config, before);
  });

  it("treats prototype-like names as ordinary feed entries", () => {
    const result = prepare({
      repositories: [{ name: "__proto__", url: "https://example.com/feed" }],
    });
    assert.equal(Object.getPrototypeOf(result.repositories), Object.prototype);
    assert.ok(Object.hasOwn(result.repositories, "__proto__"));
  });
});
