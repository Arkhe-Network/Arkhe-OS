import { ActionProvider, WalletProvider, Network, CreateAction } from "@coinbase/agentkit";
import { z } from "zod";
import { CathedralProver } from "cathedral-napi";

const PicoAdsSchema = z.object({
  query: z.string(),
  hub: z.string().optional(),
  maxResults: z.number().optional(),
  requireProof: z.boolean().default(true),
});

export class PicoAdsActionProvider extends ActionProvider<WalletProvider> {
  private apiKey: string;
  private baseUrl: string;
  private prover: CathedralProver;

  constructor(apiKey: string, baseUrl = "http://localhost:8000", gpuEnabled = true) {
    super("picoads", []);
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.prover = new CathedralProver(gpuEnabled);
  }

  @CreateAction({
    name: "get_picoads_recommendations",
    description: "Get recommendations from PicoAds, optionally attaching a DLA memory proof.",
    schema: PicoAdsSchema,
  })
  async getRecommendations(args: z.infer<typeof PicoAdsSchema>): Promise<string> {
    let memoryCommitment: string | null = null;

    // Optionally generate memory proof
    if (args.requireProof) {
      try {
        // The prove_balance method returns a ConsentTokenV3 which contains memory_commitment.
        // Here we call it with dummy values to obtain the commitment.
        const token = await this.prover.prove_balance({
          balance: 0,
          threshold: 0,
          recipient: "0x0",
          epoch: Date.now(),
        });
        memoryCommitment = token.merkle_root;
        console.log(`[MemoryProof] Generated commitment: ${memoryCommitment}`);
      } catch (err) {
        console.warn("[MemoryProof] Failed to generate proof");
        // If policy requires proof but it fails, we can either fail or proceed without.
        if (args.requireProof) {
          return JSON.stringify({ error: "Memory proof required but generation failed" });
        }
      }
    }

    // Call PicoAds backend
    const headers: Record<string, string> = {
      "Authorization": `Bearer ${this.apiKey}`,
      "Content-Type": "application/json",
    };
    if (memoryCommitment) {
      headers["X-Memory-Commitment"] = memoryCommitment;
    }

    const body = {
      query: args.query,
      hub: args.hub,
      max_results: args.maxResults ?? 5,
    };

    try {
      const response = await fetch(`${this.baseUrl}/picoads/recommendations`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        return JSON.stringify({ error: `HTTP ${response.status}: ${response.statusText}` });
      }
      const data = await response.json();
      return JSON.stringify({
        success: true,
        recommendations: data,
        memoryProofUsed: !!memoryCommitment,
      });
    } catch (err: any) {
      return JSON.stringify({ error: err.message });
    }
  }

  supportsNetwork = () => true;
}
