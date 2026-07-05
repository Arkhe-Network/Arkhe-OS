package commands

import (
	"fmt"
	"log"
	"time"

	pb "github.com/arkhe-os/arkhe/cmd/arkhe/api"
	"github.com/spf13/cobra"
)

func ShardCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "shard",
		Short: "Manage compute shards",
	}
	cmd.AddCommand(shardCreateCmd())
	cmd.AddCommand(shardListCmd())
	cmd.AddCommand(shardDestroyCmd())
	cmd.AddCommand(shardStatusCmd())
	return cmd
}

func shardCreateCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "create <name>",
		Short: "Create a new shard",
		Args:  cobra.ExactArgs(1),
		Run:   shardCreateRun,
	}
	cmd.Flags().String("motor", "continental-mind", "motor type")
	cmd.Flags().String("substrate", "9001", "substrate ID")
	cmd.Flags().Bool("gpu", false, "request GPU acceleration")
	return cmd
}

func shardCreateRun(cmd *cobra.Command, args []string) {
	name := args[0]
	motor, _ := cmd.Flags().GetString("motor")
	substrate, _ := cmd.Flags().GetString("substrate")
	gpu, _ := cmd.Flags().GetBool("gpu")

	ctx, cancel := contextTimeout(30 * time.Second)
	defer cancel()

	resp, err := ShardClient.CreateShard(ctx, &pb.CreateShardRequest{
		SubstrateId: substrate,
		Motor:       motor,
		Gpu:         gpu,
		Labels:      map[string]string{"name": name},
	})
	if err != nil {
		log.Fatalf("CreateShard: %v", err)
	}
	fmt.Printf("Shard %s created\n", resp.ShardId)
	fmt.Printf("  Substrate: %s\n", resp.SubstrateId)
	fmt.Printf("  Motor:     %s\n", resp.Motor)
	fmt.Printf("  Status:    %s\n", resp.Status)
	fmt.Printf("  Endpoint:  %s\n", resp.Endpoint)
}

func shardListCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "list",
		Short: "List all shards",
		Run: func(cmd *cobra.Command, args []string) {
			ctx, cancel := contextTimeout(10 * time.Second)
			defer cancel()

			resp, err := ShardClient.ListShards(ctx, &pb.ListShardsRequest{})
			if err != nil {
				log.Fatalf("ListShards: %v", err)
			}
			if len(resp.Shards) == 0 {
				fmt.Println("No shards.")
				return
			}
			fmt.Printf("%-36s %-12s %-20s %-12s %s\n", "SHARD ID", "STATUS", "MOTOR", "SUBSTRATE", "ENDPOINT")
			for _, s := range resp.Shards {
				fmt.Printf("%-36s %-12s %-20s %-12s %s\n", s.ShardId, s.Status, s.Motor, s.SubstrateId, s.Endpoint)
			}
		},
	}
}

func shardDestroyCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "destroy <shard-id>",
		Short: "Destroy a shard",
		Args:  cobra.ExactArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			ctx, cancel := contextTimeout(30 * time.Second)
			defer cancel()

			_, err := ShardClient.DestroyShard(ctx, &pb.DestroyShardRequest{ShardId: args[0]})
			if err != nil {
				log.Fatalf("DestroyShard: %v", err)
			}
			fmt.Printf("Shard %s destroyed\n", args[0])
		},
	}
}

func shardStatusCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "status <shard-id>",
		Short: "Get shard health and coherence",
		Args:  cobra.ExactArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			ctx, cancel := contextTimeout(10 * time.Second)
			defer cancel()

			resp, err := ShardClient.GetShardStatus(ctx, &pb.GetShardStatusRequest{ShardId: args[0]})
			if err != nil {
				log.Fatalf("GetShardStatus: %v", err)
			}
			fmt.Printf("Shard:    %s\n", resp.ShardId)
			fmt.Printf("Status:   %s\n", resp.Status)
			fmt.Printf("Uptime:   %ds\n", resp.UptimeSeconds)
			fmt.Printf("\u03bb\u2082:     %.4f\n", resp.Coherence)
		},
	}
}
