using Xunit;
using FluentAssertions;
using ArkheNode.Core;

namespace ArkheNode.Core.Tests;

public class PhiCCalculatorTests
{
    [Theory]
    [InlineData("WPA3", -40, 35, 10, 0.2, 0.80)]
    [InlineData("WPA2", -55, 25, 50, 0.4, 0.70)]
    [InlineData("OPEN", -75, 10, 200, 0.8, 0.35)]
    public void Calculate_ShouldReturnExpectedRange(
        string security, double rssi, double snr, double error, double util, double expectedMin)
    {
        var metrics = new PhyMetrics(rssi, snr, error, util, security);
        var result = PhiCCalculator.Calculate(metrics);

        result.PhiC.Should().BeGreaterOrEqualTo(expectedMin);
        result.PhiC.Should().BeLessThan(ArkheInvariants.GAP_MAX);
    }

    [Fact]
    public void Calculate_WithWPA3AndMaxSignal_ShouldReturnHighPhiC()
    {
        var metrics = new PhyMetrics(-40, 35, 0, 0.0, "WPA3");
        var result = PhiCCalculator.Calculate(metrics);
        result.PhiC.Should().BeGreaterThan(0.95);
        result.IsConstitutional.Should().BeTrue();
    }

    [Fact]
    public void Calculate_WithOpenNetwork_ShouldBeUnconstitutional()
    {
        var metrics = new PhyMetrics(-80, 10, 500, 0.8, "OPEN");
        var result = PhiCCalculator.Calculate(metrics);
        result.Invariants["ghost"].Should().BeFalse();
        result.IsConstitutional.Should().BeFalse();
    }

    [Fact]
    public void Calculate_WithFipsFailed_ShouldBeUnconstitutional()
    {
        var metrics = new PhyMetrics(-30, 40, 0, 0.0, "WPA3");
        var result = PhiCCalculator.Calculate(metrics, fipsKatPassed: false);
        result.Invariants["fips_kat"].Should().BeFalse();
        result.IsConstitutional.Should().BeFalse();
    }

    [Fact]
    public void Calculate_ShouldRespectGapSoberano()
    {
        var metrics = new PhyMetrics(-20, 50, 0, 0.0, "SATCOM-KYBER");
        var result = PhiCCalculator.Calculate(metrics);
        result.PhiC.Should().BeLessThan(1.0);
        result.Invariants["gap"].Should().BeTrue();
    }
}
