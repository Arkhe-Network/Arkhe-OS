package commands

import (
	"context"
	"fmt"
	"log"
	"time"

	pb "github.com/arkhe-os/arkhe/cmd/arkhe/api"
	"github.com/spf13/cobra"
)

func contextTimeout(d time.Duration) (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.Background(), d)
}

func PortalCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "portal",
		Short: "Manage reality portals",
	}
	cmd.AddCommand(portalFinancialCmd())
	cmd.AddCommand(portalStatusCmd())
	return cmd
}

func portalFinancialCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "financial",
		Short: "Financial portal commands",
	}
	cmd.AddCommand(&cobra.Command{
		Use:   "dashboard",
		Short: "Show recent royalty payments",
		Run:   portalFinancialDashboard,
	})
	cmd.AddCommand(&cobra.Command{
		Use:   "status",
		Short: "Show Pix bridge and reconciliation status",
		Run:   portalFinancialStatus,
	})
	return cmd
}

func portalFinancialDashboard(cmd *cobra.Command, args []string) {
	ctx, cancel := contextTimeout(10 * time.Second)
	defer cancel()

	resp, err := PortalClient.QueryRoyalties(ctx, &pb.QueryRoyaltiesRequest{Limit: 20})
	if err != nil {
		log.Fatalf("QueryRoyalties: %v", err)
	}
	fmt.Println("\u250c\u2500\u2500 ARKHE FINANCIAL PORTAL \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510")
	if len(resp.Royalties) == 0 {
		fmt.Println("\u2502  No recent royalties.                             \u2502")
	} else {
		for _, r := range resp.Royalties {
			shortID := r.TargetBlockId
			if len(shortID) > 16 {
				shortID = shortID[:16]
			}
			fmt.Printf("\u2502  Block %-20s \u2192 ORCID: %-16s R$%.2f [%s]\n", shortID, r.SourceOrcid, r.Amount, r.Status)
		}
	}
	fmt.Println("\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518")
}

func portalFinancialStatus(cmd *cobra.Command, args []string) {
	ctx, cancel := contextTimeout(10 * time.Second)
	defer cancel()

	resp, err := PortalClient.GetPortalStatus(ctx, &pb.GetPortalStatusRequest{})
	if err != nil {
		log.Fatalf("GetPortalStatus: %v", err)
	}
	fmt.Println("\u250c\u2500\u2500 PORTAL FINANCIAL STATUS \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510")
	fmt.Printf("\u2502  Portal status:    %-20s           \u2502\n", resp.Status)
	fmt.Printf("\u2502  Total royalties:  %-20d           \u2502\n", resp.TotalRoyalties)
	fmt.Printf("\u2502  Total (BRL):      R$ %-17.2f       \u2502\n", resp.TotalAmountBrl)
	fmt.Printf("\u2502  Bridge status:    %-20s           \u2502\n", resp.BridgeStatus)
	fmt.Printf("\u2502  \u03bb\u2082:             %-20.4f           \u2502\n", resp.Coherence)
	fmt.Println("\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518")
}

func portalStatusCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "status",
		Short: "Show all portal statuses",
		Run: func(cmd *cobra.Command, args []string) {
			ctx, cancel := contextTimeout(10 * time.Second)
			defer cancel()

			resp, err := PortalClient.GetPortalStatus(ctx, &pb.GetPortalStatusRequest{})
			if err != nil {
				log.Fatalf("GetPortalStatus: %v", err)
			}
			fmt.Println("Active Portals:")
			fmt.Printf("  FinancialPortal  | Status: %s | Royalties: %d | Bridge: %s\n",
				resp.Status, resp.TotalRoyalties, resp.BridgeStatus)
			fmt.Println("  TemporalPortal   | Status: SYNCHRONIZED")
			fmt.Println("  QuantumPortal    | Status: ENTANGLED")
			fmt.Println("  GovernancePortal | Status: ACTIVE")
		},
	}
}
