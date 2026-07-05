using Xunit;
using FluentAssertions;
using ArkheNode.Core;

namespace ArkheNode.Core.Tests;

public class InvariantsTests
{
    [Fact]
    public void GhostInvariant_ShouldEqualRoot3Over3()
    {
        double expected = Math.Sqrt(3) / 3;
        ArkheInvariants.GHOST.Should().BeApproximately(expected, 1e-4);
    }

    [Fact]
    public void LoopsealInvariant_ShouldEqualPiOver9()
    {
        double expected = Math.PI / 9.0;
        ArkheInvariants.LOOPSEAL.Should().BeApproximately(expected, 1e-4);
    }

    [Fact]
    public void GapMax_ShouldBeLessThanOne()
    {
        ArkheInvariants.GAP_MAX.Should().BeLessThan(1.0);
    }

    [Fact]
    public void Autocide_ShouldEqualGhost()
    {
        ArkheInvariants.AUTOCIDE.Should().Be(ArkheInvariants.GHOST);
    }

    [Fact]
    public void AllInvariants_ShouldMaintainHierarchy()
    {
        ArkheInvariants.GHOST.Should().BeGreaterThan(ArkheInvariants.LOOPSEAL);
        ArkheInvariants.GAP_MAX.Should().BeGreaterThan(ArkheInvariants.GHOST);
    }
}
