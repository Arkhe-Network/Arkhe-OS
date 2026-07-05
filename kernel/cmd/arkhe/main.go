package main

import (
	"fmt"
	"os"

	"github.com/arkhe-os/arkhe/cmd/arkhe/commands"
	"github.com/spf13/cobra"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

var oracleAddr string

func main() {
	rootCmd := &cobra.Command{
		Use:   "arkhe",
		Short: "ARKHE Multiversal Orchestrator",
		PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
			if cmd.Name() == "help" || cmd.Name() == "completion" {
				return nil
			}
			conn, err := grpc.Dial(oracleAddr,
				grpc.WithTransportCredentials(insecure.NewCredentials()),
				grpc.WithDefaultCallOptions(grpc.WaitForReady(true)),
			)
			if err != nil {
				return fmt.Errorf("connect to oracle: %w", err)
			}
			commands.InitClients(conn)
			return nil
		},
	}
	rootCmd.PersistentFlags().StringVar(&oracleAddr, "oracle", "localhost:50051", "oracle daemon address")

	rootCmd.AddCommand(commands.ShardCmd())
	rootCmd.AddCommand(commands.PortalCmd())
	rootCmd.AddCommand(commands.SelfCompleteCmd())

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
