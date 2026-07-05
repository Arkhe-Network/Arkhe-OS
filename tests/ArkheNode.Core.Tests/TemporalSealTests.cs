using Xunit;
using FluentAssertions;
using ArkheNode.Core;

namespace ArkheNode.Core.Tests;

public class TemporalSealTests
{
    [Fact]
    public void Generate_ShouldProduceValidSeal()
    {
        var seal = TemporalSealGenerator.Generate("310", "NODE-TEST-01", 0.85);
        seal.Should().NotBeNull();
        seal.SealHash.Should().NotBeNullOrEmpty();
        seal.Substrate.Should().Be("310");
    }

    [Fact]
    public void Generate_WithSameInput_ShouldProduceDifferentSeals()
    {
        var seal1 = TemporalSealGenerator.Generate("310", "NODE-X", 0.9);
        var seal2 = TemporalSealGenerator.Generate("310", "NODE-X", 0.9);
        seal1.SealHash.Should().NotBe(seal2.SealHash);
    }

    [Fact]
    public void Generate_ShouldIncludeTimestamp()
    {
        var before = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        var seal = TemporalSealGenerator.Generate("310", "NODE", 0.88);
        seal.Timestamp.Should().BeGreaterThanOrEqualTo(before);
    }

    [Fact]
    public void Generate_ShouldPropagatePreviousSeal()
    {
        var prev = TemporalSealGenerator.Generate("310", "NODE-A", 0.80);
        var next = TemporalSealGenerator.Generate("310", "NODE-B", 0.85, prev.SealHash);
        next.PreviousSealHash.Should().Be(prev.SealHash);
    }
}
