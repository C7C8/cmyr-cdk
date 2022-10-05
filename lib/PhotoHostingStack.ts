import { RemovalPolicy, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import {
  CloudFormationInit, InitCommand, InitConfig, InitFile, InitPackage,
  Instance,
  InstanceClass,
  InstanceSize,
  InstanceType, Port,
  SubnetType,
  Vpc
} from "aws-cdk-lib/aws-ec2";
import { FileSystem, PerformanceMode, ThroughputMode } from "aws-cdk-lib/aws-efs";
import { ARecord, PublicHostedZone, RecordTarget } from "aws-cdk-lib/aws-route53";
import { EcsOptimizedImage } from "aws-cdk-lib/aws-ecs";
import { Certificate, CertificateValidation } from "aws-cdk-lib/aws-certificatemanager";
import { ManagedPolicy } from "aws-cdk-lib/aws-iam";

export class PhotoHostingStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    const vpc = new Vpc(this, "vpc", {
      cidr: "10.0.0.0/16",
      maxAzs: 1,
      subnetConfiguration: [{
        name: "Public",
        subnetType: SubnetType.PUBLIC,
        cidrMask: 24,
      }]
    });

    const zone = PublicHostedZone.fromPublicHostedZoneAttributes(this, "HostedZone", {
      zoneName: "crmyers.dev",
      hostedZoneId: "Z06368022REVB4Y50QOQM"
    });

    const cert = new Certificate(this, "PhotosCert", {
      domainName: "photos.crmyers.dev",
      validation: CertificateValidation.fromDns(zone)
    });

    const photoprismFS = new FileSystem(this, "PhotoprismFS", {
      vpc: vpc,
      fileSystemName: "PhotoprismData",
      performanceMode: PerformanceMode.GENERAL_PURPOSE,
      throughputMode: ThroughputMode.BURSTING,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const photoprismInstance = new Instance(this, "PhotoprismInstance", {
      instanceType: InstanceType.of(InstanceClass.T3A, InstanceSize.SMALL),
      machineImage: EcsOptimizedImage.amazonLinux2(),
      vpcSubnets: { subnetType: SubnetType.PUBLIC },
      vpc: vpc,
      userDataCausesReplacement: true,
      // init: CloudFormationInit.fromElements(
      //   InitFile.fromFileInline("/home/ec2-user/docker-compose.yml", "photoprism/docker-compose.yml"),
      // )
    });
    photoprismInstance.userData.addCommands("yum check-update -y",    // Ubuntu: apt-get -y update
      "yum upgrade -y",                                 // Ubuntu: apt-get -y upgrade
      "yum install -y amazon-efs-utils",                // Ubuntu: apt-get -y install amazon-efs-utils
      "yum install -y nfs-utils",                       // Ubuntu: apt-get -y install nfs-common
      "curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/bin/docker-compose",
      "chmod +x /usr/bin/docker-compose",
      "file_system_id_1=" + photoprismFS.fileSystemId,
      "efs_mount_point_1=/photoprism",
      "mkdir -p \"${efs_mount_point_1}\"",
      "test -f \"/sbin/mount.efs\" && echo \"${file_system_id_1}:/ ${efs_mount_point_1} efs defaults,_netdev\" >> /etc/fstab || " +
      "echo \"${file_system_id_1}.efs." + Stack.of(this).region + ".amazonaws.com:/ ${efs_mount_point_1} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0\" >> /etc/fstab",
      "mount -a -t efs,nfs4 defaults"
    );
    photoprismFS.connections.allowDefaultPortFrom(photoprismInstance)
    photoprismInstance.role.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMManagedInstanceCore"));
    photoprismInstance.connections.allowFromAnyIpv4(Port.tcp(80));
    photoprismInstance.connections.allowFromAnyIpv4(Port.tcp(443));

    new ARecord(this, "DnsRecord", {
      zone: zone,
      recordName: "photos.crmyers.dev",
      target: RecordTarget.fromIpAddresses("35.171.186.54")
    });
  }
}
