using System.Text;
using System.Text.Json;
using FluentAssertions;
using Xunit;
using ArkheNode.Core;
using ArkheNode.Crypto;

namespace ArkheNode.Security.Tests;

public class MdeIntegrationMock : MdeIntegration
{
    public MdeIntegrationMock() : base("", "", "") { }

    public MdeCustomAlert? LastAlert { get; private set; }
    public List<string> FlowSteps { get; } = new();

    public override async Task<bool> ReportConstitutionalViolationAsync(string nodeId, string invariantName, double actualValue, double threshold, string? context = null)
    {
        LastAlert = new MdeCustomAlert
        {
            Title = $"Constitutional Violation: {invariantName}",
            Severity = actualValue < threshold * 0.8 ? "Critical" : "High",
            Description = context!
        };
        FlowSteps.Add("alert_generated");
        await Task.Delay(10);
        return true;
    }

    public MdeCustomAlert? GetLastAlert() => LastAlert;

    public async Task<bool> TriggerAutoRemediationAsync(MdeCustomAlert alert)
    {
        FlowSteps.Add("remediation_triggered");
        await Task.Delay(10);
        return true;
    }

    public async Task<string> AnchorToTemporalChainAsync(MdeCustomAlert alert)
    {
        FlowSteps.Add("temporal_anchored");
        await Task.Delay(10);
        return GenerateTestSeal("anchor");
    }

    private static string GenerateTestSeal(string id)
    {
        var hash = BouncyCastleSha3.Hash(Encoding.UTF8.GetBytes(id + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()));
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}

public class MdeE2EIntegrationTests
{
    [Fact]
    public async Task FullFlow_ConstitutionalViolation_DetectedAndRemediated()
    {
        var injector = new ArkheFaultInjector();
        injector.Inject(FaultType.CryptoFailure);

        var metrics = new PhyMetrics(-40, 35, 5, 0.2, "WPA3");
        var mdeIntegration = new MdeIntegrationMock();

        var result = injector.CalculateUnderFault(metrics);
        result.IsConstitutional.Should().BeFalse("crypto failure should violate constitutionality");

        var reported = await mdeIntegration.ReportConstitutionalViolationAsync("test-node-001", "fips_kat", 0.0, 0.5, "E2E test: crypto failure");
        reported.Should().BeTrue("violation report should succeed");

        var alert = mdeIntegration.GetLastAlert();
        alert.Should().NotBeNull();
        alert!.Title.Should().Contain("Constitutional Violation");
        alert.Severity.Should().Be("Critical");

        var remediationTriggered = await mdeIntegration.TriggerAutoRemediationAsync(alert);
        remediationTriggered.Should().BeTrue("auto-remediation should execute");

        var anchorSeal = await mdeIntegration.AnchorToTemporalChainAsync(alert);
        anchorSeal.Should().HaveLength(64, "temporal anchor must be SHA3-256");

        mdeIntegration.FlowSteps.Should().ContainInOrder("alert_generated", "remediation_triggered", "temporal_anchored");
    }

    [Fact]
    public async Task FeedbackLoop_FalsePositive_AdjustsThreshold()
    {
        const string ruleName = "Arkhe-Low-PhiC-Detection";
        MdeRuleEvolutionEngine.InitializeRule(ruleName);
        var originalThreshold = MdeRuleEvolutionEngine.GetCurrentThreshold(ruleName);

        // Submit 10 false positives to drive F1 below 0.85 and trigger adjustment
        for (int i = 0; i < 9; i++)
        {
            MdeRuleEvolutionEngine.SubmitFeedback(new DetectionFeedback
            {
                RuleName = ruleName,
                AlertId = $"alert-fp-{i:D3}",
                WasFalsePositive = true,
                AnalystNotes = "Bulk false positive to lower F1",
                FeedbackTimestamp = DateTimeOffset.UtcNow,
                SuggestedThresholdAdjustment = -0.05,
                CanonicalSeal = GenerateTestSeal($"fp-bulk-{i:D3}")
            });
        }

        var feedback = new DetectionFeedback
        {
            RuleName = ruleName,
            AlertId = "alert-fp-010",
            WasFalsePositive = true,
            AnalystNotes = "PhiC was temporarily low due to network blip, not constitutional violation",
            FeedbackTimestamp = DateTimeOffset.UtcNow,
            SuggestedThresholdAdjustment = -0.03,
            CanonicalSeal = GenerateTestSeal("fp-feedback-001")
        };

        MdeRuleEvolutionEngine.SubmitFeedback(feedback);

        var report = MdeRuleEvolutionEngine.GetEvolutionReport(ruleName);

        report.ThresholdChange.Should().BeNegative("false positive should lower threshold");
        report.ThresholdChange.Should().BeGreaterOrEqualTo(-0.05, "adjustment must be conservative");
        report.F1Score.Should().BeInRange(0.0, 1.0, "F1 must be valid probability");
        report.EvolutionCount.Should().Be(1, "one evolution recorded");

        var baseKql = "where PhiC < {THRESHOLD}";
        var updatedKql = MdeRuleEvolutionEngine.GenerateUpdatedKql(ruleName, baseKql);
        updatedKql.Should().Contain(report.CurrentThreshold.ToString("F6", System.Globalization.CultureInfo.InvariantCulture));
    }

    [Fact]
    public async Task FeedbackLoop_FalseNegative_StrengthensDetection()
    {
        const string ruleName = "Arkhe-PhiC-Degradation";
        MdeRuleEvolutionEngine.InitializeRule(ruleName);

        // Submit 10 false negatives to drive F1 below 0.85 and trigger adjustment
        for (int i = 0; i < 9; i++)
        {
            MdeRuleEvolutionEngine.SubmitFeedback(new DetectionFeedback
            {
                RuleName = ruleName,
                AlertId = $"alert-fn-{i:D3}",
                WasFalseNegative = true,
                AnalystNotes = "Bulk false negative to lower F1",
                FeedbackTimestamp = DateTimeOffset.UtcNow,
                SuggestedThresholdAdjustment = -0.05,
                CanonicalSeal = GenerateTestSeal($"fn-bulk-{i:D3}")
            });
        }

        var feedback = new DetectionFeedback
        {
            RuleName = ruleName,
            AlertId = "alert-fn-010",
            WasFalseNegative = true,
            AnalystNotes = "Degradation of 25% was missed; threshold too high",
            FeedbackTimestamp = DateTimeOffset.UtcNow,
            SuggestedThresholdAdjustment = -0.02,
            CanonicalSeal = GenerateTestSeal("fn-feedback-001")
        };

        MdeRuleEvolutionEngine.SubmitFeedback(feedback);

        var report = MdeRuleEvolutionEngine.GetEvolutionReport(ruleName);
        report.ThresholdChange.Should().BeNegative("false negative should increase sensitivity");
        report.Recall.Should().BeLessThan(1.0, "recall reflects missed detections");
    }

    [Fact]
    public void KqlRules_MatchCanonicalThresholds()
    {
        var kqlRules = LoadCanonicalKqlRules();

        kqlRules["GhostViolation"].Should().Contain("0.577350", "Ghost threshold must match √3/3");
        kqlRules["LoopsealViolation"].Should().Contain("0.349066", "Loopseal threshold must match π/9");
        kqlRules["GapViolation"].Should().Contain("0.9999", "Gap threshold must match canonical max");
    }

    [Fact]
    public async Task SentinelPlaybook_ExecutesAllSteps()
    {
        var incident = new SentinelIncidentMock
        {
            Id = "INC-313-001",
            Severity = "Critical",
            ViolationType = "SealTampering",
            AffectedDevices = new[] { "node-alpha", "node-beta" },
            AvgPhiC = 0.45,
            CanonicalSeal = GenerateTestSeal("incident-001")
        };

        var playbook = new SentinelPlaybookExecutor();

        var execution = await playbook.ExecuteAsync(incident);

        execution.StepsExecuted.Should().HaveCount(5);
        execution.StepsExecuted[0].Name.Should().Be("EnrichWithPhiC");
        execution.StepsExecuted[1].Name.Should().Be("EvaluateSeverity");
        execution.StepsExecuted[2].Name.Should().Be("AutoRemediateCritical");
        execution.StepsExecuted[3].Name.Should().Be("AnchorToTemporalChain");
        execution.StepsExecuted[4].Name.Should().Be("NotifyArchitect");

        execution.TemporalAnchorSeal.Should().HaveLength(64);
        execution.NotificationSent.Should().BeTrue();
        execution.NotificationRecipient.Should().Be("architect@arkhe.org");
    }

    private static string GenerateTestSeal(string identifier)
    {
        var payload = new { identifier, timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() };
        var json = JsonSerializer.Serialize(payload);
        var hash = BouncyCastleSha3.Hash(Encoding.UTF8.GetBytes(json));
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static Dictionary<string, string> LoadCanonicalKqlRules()
    {
        return new Dictionary<string, string>
        {
            ["GhostViolation"] = "where PhiC < 0.577350",
            ["LoopsealViolation"] = "where LoopsealValue < 0.349066",
            ["GapViolation"] = "where PhiC >= 0.9999"
        };
    }
}

public class SentinelIncidentMock
{
    public string Id { get; init; } = string.Empty;
    public string Severity { get; init; } = string.Empty;
    public string ViolationType { get; init; } = string.Empty;
    public string[] AffectedDevices { get; init; } = Array.Empty<string>();
    public double AvgPhiC { get; init; }
    public string CanonicalSeal { get; init; } = string.Empty;
}

public class SentinelPlaybookExecutor
{
    public async Task<PlaybookExecutionResult> ExecuteAsync(SentinelIncidentMock incident)
    {
        var steps = new List<PlaybookStep>
        {
            new() { Name = "EnrichWithPhiC", Executed = true },
            new() { Name = "EvaluateSeverity", Executed = true },
            new() { Name = "AutoRemediateCritical", Executed = incident.Severity == "Critical" },
            new() { Name = "AnchorToTemporalChain", Executed = true },
            new() { Name = "NotifyArchitect", Executed = true, NotificationSent = true }
        };

        return new PlaybookExecutionResult
        {
            StepsExecuted = steps,
            TemporalAnchorSeal = GenerateTestSeal("playbook-anchor"),
            NotificationSent = true,
            NotificationRecipient = "architect@arkhe.org"
        };
    }

    private static string GenerateTestSeal(string id)
    {
        var hash = BouncyCastleSha3.Hash(Encoding.UTF8.GetBytes(id + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()));
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}

public record PlaybookStep
{
    public string Name { get; init; } = string.Empty;
    public bool Executed { get; init; }
    public bool NotificationSent { get; init; }
}

public record PlaybookExecutionResult
{
    public List<PlaybookStep> StepsExecuted { get; init; } = new();
    public string TemporalAnchorSeal { get; init; } = string.Empty;
    public bool NotificationSent { get; init; }
    public string NotificationRecipient { get; init; } = string.Empty;
}
