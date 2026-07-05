package commands

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"time"

	"github.com/spf13/cobra"
)

func SelfCompleteCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "self-complete",
		Short: "Trigger ARKHE ontological self-completion cycle",
		Long: `Run the Self-Completion Engine: analyze gaps, generate Coq specs,
prove correctness via ZK, integrate proofs, and hot-reload firmware.

With --loop the cycle runs every 24h, keeping the cathedral self-consistent.`,
		Run: selfCompleteRun,
	}
	cmd.Flags().Bool("dry-run", false, "Analyze and generate proofs without applying changes")
	cmd.Flags().Bool("loop", false, "Run continuously in background (24h interval)")
	cmd.Flags().String("engine-bin", "arkhe-self-complete", "Path to the Self-Completion Engine binary")
	return cmd
}

func selfCompleteRun(cmd *cobra.Command, args []string) {
	dryRun, _ := cmd.Flags().GetBool("dry-run")
	loop, _ := cmd.Flags().GetBool("loop")
	engineBin, _ := cmd.Flags().GetString("engine-bin")

	runSelfComplete := func() error {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
		defer cancel()

		execArgs := []string{}
		if dryRun {
			execArgs = append(execArgs, "--dry-run")
		}

		c := exec.CommandContext(ctx, engineBin, execArgs...)
		c.Stdout = os.Stdout
		c.Stderr = os.Stderr

		fmt.Println("\u250c\u2500\u2500 ARKHE SELF-COMPLETION ENGINE \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510")
		if dryRun {
			fmt.Println("\u2502  Mode: DRY RUN (no changes applied)              \u2502")
		} else {
			fmt.Println("\u2502  Mode: LIVE                                     \u2502")
		}
		fmt.Printf("\u2502  Engine: %-44s\u2502\n", engineBin)
		fmt.Println("\u2502  Phases:                                       \u2502")
		fmt.Println("\u2502    1. Analyze gaps                             \u2502")
		fmt.Println("\u2502    2. Generate Coq specs                       \u2502")
		fmt.Println("\u2502    3. Prove correctness (ZK)                   \u2502")
		fmt.Println("\u2502    4. Integrate proofs                          \u2502")
		fmt.Println("\u2502    5. Hot-reload firmware                       \u2502")
		fmt.Println("\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518")

		return c.Run()
	}

	if loop {
		fmt.Println("Self-complete loop started (24h interval). Press Ctrl+C to stop.")
		for {
			if err := runSelfComplete(); err != nil {
				log.Printf("self-complete cycle failed: %v", err)
			}
			time.Sleep(24 * time.Hour)
		}
	}

	if err := runSelfComplete(); err != nil {
		log.Fatalf("self-complete failed: %v", err)
	}
}
