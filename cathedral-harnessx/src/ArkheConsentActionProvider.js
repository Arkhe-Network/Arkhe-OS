"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ArkheConsentActionProvider = void 0;
const zod_1 = require("zod");
// Mock napi imports
const cathedral_napi = {
    query_symbolic_plan: (query) => "Plan: " + query,
    get_policy_suggestions: () => []
};
// Mock decorator
function CreateAction(opts) {
    return function (target, propertyKey, descriptor) {
        // mock implementation
    };
}
class ArkheConsentActionProvider {
    // @ts-ignore
    @CreateAction({
        name: "query_plan",
        description: "Consulta o motor simbólico para obter um plano.",
        schema: zod_1.z.object({ query: zod_1.z.string() }),
    })
    async queryPlan(args) {
        const plan = cathedral_napi.query_symbolic_plan(args.query);
        return JSON.stringify({ plan });
    }
    // @ts-ignore
    @CreateAction({
        name: "adjust_policy_metacognitive",
        description: "Aplica sugestões metacognitivas à política de provas.",
        schema: zod_1.z.object({}),
    })
    async adjustPolicy() {
        const suggestions = cathedral_napi.get_policy_suggestions();
        // Aplicar as sugestões localmente ou enviar ao core
        return JSON.stringify({ suggestions });
    }
}
exports.ArkheConsentActionProvider = ArkheConsentActionProvider;
//# sourceMappingURL=ArkheConsentActionProvider.js.map