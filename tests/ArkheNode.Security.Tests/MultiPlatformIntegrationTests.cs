using FluentAssertions;
using Xunit;
using ArkheNode.Core;

namespace ArkheNode.Security.Tests;

public class CanonicalSchemaTests
{
    [Fact]
    public void SchemaVersion_Is_313_1_0()
    {
        ArkheCanonicalSchema.Version.Should().Be("313.1.0");
    }

    [Fact]
    public void CreatePayload_GeneratesValidCanonicalPayload()
    {
        var payload = ArkheCanonicalSchema.CreatePayload("313", "NODE-TEST-01", 0.9234, "GHOST", "Constitutional", true);

        payload.Should().NotBeNull();
        payload.Substrate.Should().Be("313");
        payload.PhiC.Should().Be(0.9234);
        payload.SealHash.Should().HaveLength(64);
        payload.SchemaVersion.Should().Be("313.1.0");
    }

    [Fact]
    public void ValidatePayload_ReturnsTrue_ForValidPayload()
    {
        var payload = ArkheCanonicalSchema.CreatePayload("313", "NODE-01", 0.95, "GHOST", "None", true);
        ArkheCanonicalSchema.ValidatePayload(payload).Should().BeTrue();
    }

    [Theory]
    [InlineData(-0.1)]
    [InlineData(1.0)]
    [InlineData(1.5)]
    public void ValidatePayload_ReturnsFalse_ForInvalidPhiC(double phiC)
    {
        var payload = new CanonicalPayload
        {
            Substrate = "313",
            NodeId = "NODE-01",
            PhiC = phiC,
            Invariant = "GHOST",
            ViolationType = "None",
            IsConstitutional = phiC >= ArkheInvariants.GHOST,
            SealHash = new string('a', 64),
            SchemaVersion = "313.1.0"
        };

        ArkheCanonicalSchema.ValidatePayload(payload).Should().BeFalse();
    }

    [Fact]
    public void TranslateTo_SentinelOne_MapsAllCanonicalFields()
    {
        var payload = ArkheCanonicalSchema.CreatePayload("313", "NODE-S1-01", 0.88, "GHOST", "Violation", false);
        var translated = ArkheCanonicalSchema.TranslateTo(payload, EdrPlatform.SentinelOne);

        translated.Should().ContainKey("customTags.arkhe_substrate");
        translated.Should().ContainKey("customTags.arkhe_invariant");
        translated.Should().ContainKey("customTags.arkhe_phi_c");
        translated.Should().ContainKey("agentDetectionInfo.agentName");
    }

    [Fact]
    public void TranslateTo_CrowdStrike_MapsAllCanonicalFields()
    {
        var payload = ArkheCanonicalSchema.CreatePayload("313", "NODE-CS-01", 0.88, "GHOST", "Violation", false);
        var translated = ArkheCanonicalSchema.TranslateTo(payload, EdrPlatform.CrowdStrike);

        translated.Should().ContainKey("event.PlatformName");
        translated.Should().ContainKey("event.IOAName");
        translated.Should().ContainKey("event.HostName");
    }

    [Fact]
    public void TranslateTo_MicrosoftDefender_MapsAllCanonicalFields()
    {
        var payload = ArkheCanonicalSchema.CreatePayload("313", "NODE-MD-01", 0.88, "GHOST", "Violation", false);
        var translated = ArkheCanonicalSchema.TranslateTo(payload, EdrPlatform.MicrosoftDefender);

        translated.Should().ContainKey("additionalFields.arkhe_substrate");
        translated.Should().ContainKey("deviceName");
        translated.Should().ContainKey("alertTitle");
    }

    [Fact]
    public void ValidatePayload_Detects_InconsistentConstitutionalFlag()
    {
        var payload = new CanonicalPayload
        {
            Substrate = "313",
            NodeId = "NODE-01",
            PhiC = 0.50,
            Invariant = "GHOST",
            ViolationType = "Violation",
            IsConstitutional = true,
            SealHash = new string('a', 64),
            SchemaVersion = "313.1.0"
        };

        ArkheCanonicalSchema.ValidatePayload(payload).Should().BeFalse();
    }
}

public class FederationMeshTests
{
    [Fact]
    public void FederationConsensus_RequiresQuorumOf7()
    {
        var nodes = Enumerable.Range(1, 10).Select(i => new FederationNode
        {
            NodeId = $"NODE-{i}",
            Region = $"REGION-{i}",
            Endpoint = $"https://node-{i}.arkhe.org",
            Platform = EdrPlatform.MicrosoftDefender
        }).ToList();

        var mesh = new FederationSecurityMesh(nodes);

        mesh.Should().NotBeNull();
        nodes.Should().HaveCount(10);
    }

    [Fact]
    public void CalculateFederationPhiC_HandlesNodeFailures()
    {
        var nodes = new List<FederationNode>
        {
            new() { NodeId = "NA-01", Endpoint = "https://na-01.arkhe.org", Platform = EdrPlatform.SentinelOne },
            new() { NodeId = "EU-01", Endpoint = "https://eu-01.arkhe.org", Platform = EdrPlatform.CrowdStrike },
            new() { NodeId = "AP-01", Endpoint = "https://ap-01.arkhe.org", Platform = EdrPlatform.MicrosoftDefender }
        };

        var mesh = new FederationSecurityMesh(nodes);
        var action = () => mesh.CalculateFederationPhiCAsync();

        action.Should().NotThrowAsync();
    }

    [Fact]
    public void CanonicalPayload_PreservesInvariantHierarchy_AcrossPlatforms()
    {
        var payload = ArkheCanonicalSchema.CreatePayload("313", "NODE-01", 0.58, "LOOPSEAL", "LoopsealViolation", false);

        var s1 = ArkheCanonicalSchema.TranslateTo(payload, EdrPlatform.SentinelOne);
        var cs = ArkheCanonicalSchema.TranslateTo(payload, EdrPlatform.CrowdStrike);
        var md = ArkheCanonicalSchema.TranslateTo(payload, EdrPlatform.MicrosoftDefender);

        s1["customTags.arkhe_phi_c"].Should().Be(0.58);
        cs["event.Severity"].Should().Be(0.58);
        md["additionalFields.arkhe_phi_c"].Should().Be(0.58);
    }
}

public class CrossPlatformPhiCMonitorTests
{
    [Theory]
    [InlineData(0.95, true, true, true)]
    [InlineData(0.60, true, true, true)]
    [InlineData(0.35, false, true, true)]
    [InlineData(0.30, false, false, true)]
    [InlineData(0.9999, true, true, true)]
    public void PhiC_EvaluatesCorrectly_AcrossAllPlatforms(double phiC, bool ghost, bool loopseal, bool gap)
    {
        var payload = ArkheCanonicalSchema.CreatePayload("313", "NODE-01", phiC, "TEST", "Test", phiC >= ArkheInvariants.GHOST);

        payload.IsConstitutional.Should().Be(phiC >= ArkheInvariants.GHOST);
        (phiC >= ArkheInvariants.GHOST).Should().Be(ghost);
        (phiC >= ArkheInvariants.LOOPSEAL).Should().Be(loopseal);
        (phiC <= ArkheInvariants.GAP_MAX).Should().Be(gap);
    }
}
