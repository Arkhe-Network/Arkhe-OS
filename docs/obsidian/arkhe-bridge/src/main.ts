import { Plugin, TFile, Notice } from 'obsidian';

export default class ArkheBridgePlugin extends Plugin {
  // To avoid infinite loops, we keep a set of recently processed files
  private isProcessing = new Set<string>();

  async onload() {
    // 1. Comando: Gerar hash da nota atual
    this.addCommand({
      id: 'generate-note-hash',
      name: 'Generate SHA-256 hash for current note',
      callback: () => this.generateHashForCurrentNote(),
    });

    // 2. Comando: Validar selo
    this.addCommand({
      id: 'validate-seal',
      name: 'Validate seal against hash',
      callback: () => {
        const file = this.app.workspace.getActiveFile();
        if (file) {
            const isValid = this.validateSeal(file);
            new Notice(`Selo é ${isValid ? 'válido' : 'inválido'}`);
        } else {
            new Notice('Nenhum arquivo ativo.');
        }
      },
    });

    // 3. Evento: Atualizar hash ao salvar
    this.registerEvent(
      this.app.vault.on('modify', async (file) => {
        if (file instanceof TFile && file.extension === 'md') {
          await this.updateHashInFrontmatter(file);
        }
      })
    );

    // 4. API exposta para outros plugins
    (this.app as any).arkhe = {
      getNoteHash: (file: TFile) => this.getNoteHash(file),
      validateSeal: (file: TFile) => this.validateSeal(file),
    };
  }

  async calculateHash(content: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // Helper to extract just the body content without frontmatter
  getContentWithoutFrontmatter(content: string): string {
    const fmRegex = /^---[\s\S]+?---\n/;
    if (fmRegex.test(content)) {
      return content.replace(fmRegex, '').trimStart();
    }
    return content;
  }

  async generateHashForCurrentNote() {
    const file = this.app.workspace.getActiveFile();
    if (!file) {
        new Notice('Nenhum arquivo ativo.');
        return;
    }

    if (this.isProcessing.has(file.path)) return;
    this.isProcessing.add(file.path);

    try {
        const rawContent = await this.app.vault.read(file);
        const bodyContent = this.getContentWithoutFrontmatter(rawContent);

        // Match the Python script by stripping the frontmatter and trailing newlines
        // Wait, Python script uses `content` (which doesn't include frontmatter) exactly as passed in.
        const hash = await this.calculateHash(bodyContent);
        await this.app.fileManager.processFrontMatter(file, (fm) => {
          fm.hash = hash;
          fm.timestamp = new Date().toISOString();
        });
        new Notice(`Hash gerado: ${hash.slice(0, 8)}...`);
    } finally {
        // Allow further modifications after processing is done
        setTimeout(() => this.isProcessing.delete(file.path), 500);
    }
  }

  async updateHashInFrontmatter(file: TFile) {
    if (this.isProcessing.has(file.path)) return;

    // Prevent infinite loop by locking
    this.isProcessing.add(file.path);

    try {
        const rawContent = await this.app.vault.read(file);
        const bodyContent = this.getContentWithoutFrontmatter(rawContent);
        const newHash = await this.calculateHash(bodyContent);

        await this.app.fileManager.processFrontMatter(file, (fm) => {
          if (fm.hash !== newHash) {
            fm.hash = newHash;
            fm.modified = new Date().toISOString();
          }
        });
    } finally {
        setTimeout(() => this.isProcessing.delete(file.path), 500);
    }
  }

  getNoteHash(file: TFile): string | null {
    const cache = this.app.metadataCache.getFileCache(file);
    return cache?.frontmatter?.hash || null;
  }

  validateSeal(file: TFile): boolean {
    const cache = this.app.metadataCache.getFileCache(file);
    const seal = cache?.frontmatter?.selo;
    const hash = cache?.frontmatter?.hash;
    if (!seal || !hash) return false;
    // Verificação simples: selo contém hash?
    return seal.includes(hash.slice(0, 8));
  }
}
