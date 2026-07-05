using System.Diagnostics;
using Xunit;
using FluentAssertions;

namespace ArkheNode.Core.Tests;

public class PhiCCalculatorEdgeCaseTests
{
    [Theory]
    [InlineData(-200)]
    [InlineData(100)]
    [InlineData(-90)]
    [InlineData(-30)]
    public void Rssi_Normalization_Handles_Extreme_Values(double rssiDbm)
    {
        var metrics = new PhyMetrics(rssiDbm, 20, 50, 0.5, "WPA2");
        var result = PhiCCalculator.Calculate(metrics);
        result.SignalFactor.Should().BeInRange(0.0, 1.0);
    }

    [Theory]
    [InlineData(-100)]
    [InlineData(0)]
    [InlineData(40)]
    [InlineData(100)]
    public void Snr_Normalization_Clamps_Extreme_Values(double snrDb)
    {
        var metrics = new PhyMetrics(-50, snrDb, 50, 0.5, "WPA2");
        var result = PhiCCalculator.Calculate(metrics);
        result.SignalFactor.Should().BeInRange(0.0, 1.0);
    }

    [Theory]
    [InlineData(-1000)]
    [InlineData(0)]
    [InlineData(1000)]
    [InlineData(10000)]
    public void ErrorRate_Normalization_Handles_Invalid_Values(double errorRatePpm)
    {
        var metrics = new PhyMetrics(-50, 30, errorRatePpm, 0.5, "WPA2");
        var result = PhiCCalculator.Calculate(metrics);
        result.PerformanceFactor.Should().BeInRange(0.0, 1.0);
    }

    [Theory]
    [InlineData(-0.5)]
    [InlineData(0.0)]
    [InlineData(1.0)]
    [InlineData(2.5)]
    public void ChannelUtilization_Clamps_Invalid_Values(double utilization)
    {
        var metrics = new PhyMetrics(-50, 30, 50, utilization, "WPA2");
        var result = PhiCCalculator.Calculate(metrics);
        result.MediumFactor.Should().BeInRange(0.0, 1.0);
    }

    [Fact]
    public void Calculate_WithNullSecurityType_UsesDefaultScore()
    {
        var result = PhiCCalculator.Calculate(new PhyMetrics(-50, 30, 50, 0.5, null!));
        result.SecurityFactor.Should().Be(0.50);
    }

    [Fact]
    public void Calculate_WithEmptySecurityType_UsesDefaultScore()
    {
        var result = PhiCCalculator.Calculate(new PhyMetrics(-50, 30, 50, 0.5, ""));
        result.SecurityFactor.Should().Be(0.50);
    }

    [Fact]
    public void Calculate_Preserves_Gap_Soberano_Under_Extreme_Conditions()
    {
        var result = PhiCCalculator.Calculate(new PhyMetrics(-20, 50, 0, 0.0, "WPA3"));
        result.PhiC.Should().BeLessThan(1.0);
        result.Invariants["gap"].Should().BeTrue();
    }

    [Fact]
    public void Calculate_Handles_Rapid_Successive_Calls_Without_Degradation()
    {
        var metrics = new PhyMetrics(-50, 30, 50, 0.5, "WPA2");
        var sw = Stopwatch.StartNew();
        for (int i = 0; i < 10000; i++)
            PhiCCalculator.Calculate(metrics).Should().NotBeNull();
        sw.Stop();
        sw.ElapsedMilliseconds.Should().BeLessThan(1000);
    }
}

public class TemporalSealEdgeCaseTests
{
    [Fact]
    public void Generate_Handles_Very_Large_PhiC_Values()
    {
        var seal = TemporalSealGenerator.Generate("244", "test", 999999.9999);
        seal.SealHash.Should().HaveLength(64);
    }

    [Fact]
    public void Generate_Handles_Negative_PhiC_Values()
    {
        var act = () => TemporalSealGenerator.Generate("244", "test", -123.456);
        act.Should().NotThrow();
    }

    [Fact]
    public void Generate_Handles_Very_Long_NodeId()
    {
        var seal = TemporalSealGenerator.Generate("244", new string('A', 10000), 0.95);
        seal.SealHash.Should().HaveLength(64);
    }

    [Fact]
    public void Generate_Handles_Special_Characters_In_Substrate()
    {
        var seal = TemporalSealGenerator.Generate("244-\xce\xb1\xce\xb2\xce\xb3\xce\xb4", "test", 0.95);
        seal.SealHash.Should().NotBeNullOrEmpty();
        seal.SealHash.Should().HaveLength(64);
    }

    [Fact]
    public void Verify_Returns_False_For_Tampered_Data()
    {
        var data = "original data"u8.ToArray();
        var hex = Convert.ToHexString(TemporalSealGenerator.SHA3_256(data)).ToLowerInvariant();
        TemporalSealGenerator.Verify("tampered data"u8.ToArray(), hex).Should().BeFalse();
    }

    [Fact]
    public void Verify_Returns_True_For_Exact_Match()
    {
        var data = "test data"u8.ToArray();
        var hex = Convert.ToHexString(TemporalSealGenerator.SHA3_256(data)).ToLowerInvariant();
        TemporalSealGenerator.Verify(data, hex).Should().BeTrue();
    }

    [Fact]
    public void Verify_Handles_Case_Insensitive_Hash()
    {
        var data = "case test"u8.ToArray();
        var hash = TemporalSealGenerator.SHA3_256(data);
        TemporalSealGenerator.Verify(data, Convert.ToHexString(hash).ToLowerInvariant()).Should().BeTrue();
        TemporalSealGenerator.Verify(data, Convert.ToHexString(hash).ToUpperInvariant()).Should().BeTrue();
    }
}

public class AuditLoggerEdgeCaseTests
{
    [Fact]
    public void Log_Handles_Very_Long_Message()
    {
        var logger = new InMemoryAuditLogger();
        var act = () => logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Info, "244", "test", new string('X', 100000), 0.95, null, null));
        act.Should().NotThrow();
    }

    [Fact]
    public void Log_Handles_Null_Optional_Fields()
    {
        var logger = new InMemoryAuditLogger();
        var act = () => logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Info, "244", "test", "test", null, null, null));
        act.Should().NotThrow();
    }

    [Fact]
    public void GetEvents_WithNullSince_Returns_All()
    {
        var logger = new InMemoryAuditLogger();
        logger.Log(new AuditEvent(DateTimeOffset.UtcNow.AddHours(-2), "", AuditEventLevel.Info, "244", "n1", "old", null, null, null));
        logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Info, "244", "n1", "new", null, null, null));
        logger.GetEvents(since: null).Should().HaveCount(2);
    }

    [Fact]
    public void Flush_Handles_Empty_Event_List()
    {
        var logger = new InMemoryAuditLogger();
        logger.Invoking(l => l.Flush()).Should().NotThrow();
    }

    [Fact]
    public async Task Concurrent_Logs_From_Multiple_Threads_Are_ThreadSafe()
    {
        var logger = new InMemoryAuditLogger();
        var tasks = Enumerable.Range(0, 50).Select(tid => Task.Run(() =>
        {
            for (int i = 0; i < 200; i++)
                logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Info, "244", $"T{tid}", $"E{i}", 0.90 + (i % 10) * 0.01, null, null));
        })).ToArray();
        await Task.WhenAll(tasks);
        var events = logger.GetEvents();
        events.Should().HaveCount(10000);
        events.Select(e => e.EventId).Should().OnlyHaveUniqueItems();
    }
}

public class StressTests
{
    [Fact]
    public void PhiC_Calculation_Performance_Under_Load()
    {
        var metrics = new PhyMetrics(-50, 30, 50, 0.5, "WPA2");
        var sw = Stopwatch.StartNew();
        for (int i = 0; i < 100000; i++)
            if (PhiCCalculator.Calculate(metrics).PhiC < 0) throw new("unreachable");
        sw.Stop();
        sw.ElapsedMilliseconds.Should().BeLessThan(300);
    }

    [Fact]
    public void Seal_Generation_Performance_Under_Load()
    {
        var sw = Stopwatch.StartNew();
        for (int i = 0; i < 10000; i++)
        {
            var s = TemporalSealGenerator.Generate("244", $"node-{i}", 0.90 + (i % 10) * 0.01);
            if (string.IsNullOrEmpty(s.SealHash)) throw new("unreachable");
        }
        sw.Stop();
        sw.ElapsedMilliseconds.Should().BeLessThan(5000);
    }
}
