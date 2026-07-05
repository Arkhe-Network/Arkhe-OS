package commands

import (
	pb "github.com/arkhe-os/arkhe/cmd/arkhe/api"
	"google.golang.org/grpc"
)

var (
	ShardClient  pb.ShardServiceClient
	PortalClient pb.PortalServiceClient
)

func InitClients(conn *grpc.ClientConn) {
	ShardClient = pb.NewShardServiceClient(conn)
	PortalClient = pb.NewPortalServiceClient(conn)
}
