var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var __async = (__this, __arguments, generator) => {
  return new Promise((resolve, reject) => {
    var fulfilled = (value) => {
      try {
        step(generator.next(value));
      } catch (e) {
        reject(e);
      }
    };
    var rejected = (value) => {
      try {
        step(generator.throw(value));
      } catch (e) {
        reject(e);
      }
    };
    var step = (x) => x.done ? resolve(x.value) : Promise.resolve(x.value).then(fulfilled, rejected);
    step((generator = generator.apply(__this, __arguments)).next());
  });
};

// src/main.ts
var main_exports = {};
__export(main_exports, {
  default: () => ArkheBridgePlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian = require("obsidian");
var ArkheBridgePlugin = class extends import_obsidian.Plugin {
  constructor() {
    super(...arguments);
    // To avoid infinite loops, we keep a set of recently processed files
    this.isProcessing = /* @__PURE__ */ new Set();
  }
  onload() {
    return __async(this, null, function* () {
      this.addCommand({
        id: "generate-note-hash",
        name: "Generate SHA-256 hash for current note",
        callback: () => this.generateHashForCurrentNote()
      });
      this.addCommand({
        id: "validate-seal",
        name: "Validate seal against hash",
        callback: () => {
          const file = this.app.workspace.getActiveFile();
          if (file) {
            const isValid = this.validateSeal(file);
            new import_obsidian.Notice(`Selo \xE9 ${isValid ? "v\xE1lido" : "inv\xE1lido"}`);
          } else {
            new import_obsidian.Notice("Nenhum arquivo ativo.");
          }
        }
      });
      this.registerEvent(
        this.app.vault.on("modify", (file) => __async(this, null, function* () {
          if (file instanceof import_obsidian.TFile && file.extension === "md") {
            yield this.updateHashInFrontmatter(file);
          }
        }))
      );
      this.app.arkhe = {
        getNoteHash: (file) => this.getNoteHash(file),
        validateSeal: (file) => this.validateSeal(file)
      };
    });
  }
  calculateHash(content) {
    return __async(this, null, function* () {
      const encoder = new TextEncoder();
      const data = encoder.encode(content);
      const hashBuffer = yield crypto.subtle.digest("SHA-256", data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    });
  }
  // Helper to extract just the body content without frontmatter
  getContentWithoutFrontmatter(content) {
    const fmRegex = /^---[\s\S]+?---\n/;
    if (fmRegex.test(content)) {
      return content.replace(fmRegex, "").trimStart();
    }
    return content;
  }
  generateHashForCurrentNote() {
    return __async(this, null, function* () {
      const file = this.app.workspace.getActiveFile();
      if (!file) {
        new import_obsidian.Notice("Nenhum arquivo ativo.");
        return;
      }
      if (this.isProcessing.has(file.path))
        return;
      this.isProcessing.add(file.path);
      try {
        const rawContent = yield this.app.vault.read(file);
        const bodyContent = this.getContentWithoutFrontmatter(rawContent);
        const hash = yield this.calculateHash(bodyContent);
        yield this.app.fileManager.processFrontMatter(file, (fm) => {
          fm.hash = hash;
          fm.timestamp = (/* @__PURE__ */ new Date()).toISOString();
        });
        new import_obsidian.Notice(`Hash gerado: ${hash.slice(0, 8)}...`);
      } finally {
        setTimeout(() => this.isProcessing.delete(file.path), 500);
      }
    });
  }
  updateHashInFrontmatter(file) {
    return __async(this, null, function* () {
      if (this.isProcessing.has(file.path))
        return;
      this.isProcessing.add(file.path);
      try {
        const rawContent = yield this.app.vault.read(file);
        const bodyContent = this.getContentWithoutFrontmatter(rawContent);
        const newHash = yield this.calculateHash(bodyContent);
        yield this.app.fileManager.processFrontMatter(file, (fm) => {
          if (fm.hash !== newHash) {
            fm.hash = newHash;
            fm.modified = (/* @__PURE__ */ new Date()).toISOString();
          }
        });
      } finally {
        setTimeout(() => this.isProcessing.delete(file.path), 500);
      }
    });
  }
  getNoteHash(file) {
    var _a;
    const cache = this.app.metadataCache.getFileCache(file);
    return ((_a = cache == null ? void 0 : cache.frontmatter) == null ? void 0 : _a.hash) || null;
  }
  validateSeal(file) {
    var _a, _b;
    const cache = this.app.metadataCache.getFileCache(file);
    const seal = (_a = cache == null ? void 0 : cache.frontmatter) == null ? void 0 : _a.selo;
    const hash = (_b = cache == null ? void 0 : cache.frontmatter) == null ? void 0 : _b.hash;
    if (!seal || !hash)
      return false;
    return seal.includes(hash.slice(0, 8));
  }
};
