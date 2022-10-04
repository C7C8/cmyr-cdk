import { RemovalPolicy, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import { InstanceClass, InstanceSize, InstanceType, Port, SubnetType, Vpc } from "aws-cdk-lib/aws-ec2";
import { FileSystem, PerformanceMode, ThroughputMode } from "aws-cdk-lib/aws-efs";
import {
    AmiHardwareType,
    Cluster,
    ContainerDependencyCondition,
    ContainerImage,
    Ec2Service,
    Ec2TaskDefinition,
    EcsOptimizedImage, LogDriver,
    NetworkMode
} from "aws-cdk-lib/aws-ecs";
import { ARecord, PublicHostedZone, RecordTarget } from "aws-cdk-lib/aws-route53";
import { Certificate, CertificateValidation } from "aws-cdk-lib/aws-certificatemanager";
import { Effect, PolicyStatement } from "aws-cdk-lib/aws-iam";

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

        const photoprismFS = new FileSystem(this, "PhotoprismFS", {
            vpc: vpc,
            fileSystemName: "PhotoprismData",
            performanceMode: PerformanceMode.GENERAL_PURPOSE,
            throughputMode: ThroughputMode.BURSTING,
            removalPolicy: RemovalPolicy.RETAIN,
        });

        const cluster = new Cluster(this, "Cluster", {
            clusterName: "CmyrCluster",
            vpc: vpc,
            capacity: {
                instanceType: InstanceType.of(InstanceClass.T3A, InstanceSize.SMALL),
                desiredCapacity: 1,
                machineImage: EcsOptimizedImage.amazonLinux2(AmiHardwareType.STANDARD),
                vpcSubnets: {subnetType: SubnetType.PUBLIC},
                associatePublicIpAddress: true
            }
        });
        cluster.connections.allowFromAnyIpv4(Port.tcp(2432))

        const taskdef = new Ec2TaskDefinition(this, "PhotoprismTask", {
            family: "photoprism",
            networkMode: NetworkMode.HOST,
            volumes: [
                {
                    name: "originals",
                    efsVolumeConfiguration: {
                        fileSystemId: photoprismFS.fileSystemId,
                        rootDirectory: "/photoprism/originals",
                        transitEncryption: "ENABLED",
                    }
                },
                {
                    name: "storage",
                    efsVolumeConfiguration: {
                        fileSystemId: photoprismFS.fileSystemId,
                        rootDirectory: "/photoprism/storage",
                        transitEncryption: "ENABLED",
                    }
                }
            ],
        });

        const photoprismContainer = taskdef.addContainer("Photoprism", {
            containerName: "photoprism",
            image: ContainerImage.fromRegistry("photoprism/photoprism"),
            essential: true,
            cpu: 1536,
            memoryLimitMiB: 1536,
            logging: LogDriver.awsLogs({
                streamPrefix: "photoprism-",
            }),
            portMappings: [{
                hostPort: 2432,
                containerPort: 2432,
            }],
        });

        taskdef.taskRole!!.addToPrincipalPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ["ecs:Describe*", "ecs:List*", "ec2:Describe*"],
            resources: ["*"]
        }));

        const photoprismService = new Ec2Service(this, "PhotoprismService", {
            serviceName: "photoprism",
            desiredCount: 1,
            cluster: cluster,
            taskDefinition: taskdef
        });

        new ARecord(this, "DNS", {
            zone: zone,
            recordName: "photos.crmyers.dev",
            target: RecordTarget.fromIpAddresses("3.85.77.30")
        });
    }
}
