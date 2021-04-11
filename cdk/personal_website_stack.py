from aws_cdk import core
from aws_cdk.aws_certificatemanager import Certificate
from aws_cdk.aws_cloudfront import Distribution, SecurityPolicyProtocol, AllowedMethods, ViewerProtocolPolicy
from aws_cdk.aws_cloudfront_origins import S3Origin
from aws_cdk.aws_codebuild import FilterGroup, EventAction, Artifacts, Project, Source, BuildSpec
from aws_cdk.aws_events import RuleTargetInput
from aws_cdk.aws_route53 import PublicHostedZone, RecordTarget, ARecord, AaaaRecord
from aws_cdk.aws_iam import PolicyStatement, Effect
from aws_cdk.aws_route53_targets import CloudFrontTarget
from aws_cdk.aws_s3 import Bucket
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_sns_subscriptions import SmsSubscription
import aws_cdk.aws_events_targets as targets
from aws_cdk.core import RemovalPolicy


class PersonalWebsiteStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str,
                 cert_arn: str,
                 hosted_zone_id: str,
                 domain_name: str,
                 **kwargs) -> None:
        """
        :param cert_arn: ARN of certificate to use
        :param hosted_zone_id: ID of hosted zone to use
        :param domain_name: Domain name to use
        """
        super().__init__(scope, construct_id, **kwargs)

        ##################################
        # WEBSITE HOSTING INFRASTRUCTURE #
        ##################################

        # Grab hosted zone for the website to contain our records and an SSL certificate for HTTPS. These two have to
        # be grabbed from existing resources instead of created here because CloudFormation will time out waiting for a
        # newly-created cert to validate.
        self.hosted_zone = PublicHostedZone.from_public_hosted_zone_id(self, "personal-site-hosted-zone", hosted_zone_id)
        self.cert = Certificate.from_certificate_arn(self, "personal-site-cert", cert_arn)

        # Add an S3 bucket to host the website content
        self.website_bucket = Bucket(self, "personal-site-bucket",
                                     bucket_name=domain_name,
                                     removal_policy=RemovalPolicy.DESTROY,
                                     public_read_access=True,
                                     website_index_document="index.html",
                                     website_error_document="index.html")


        # Create a cloudfront distribution for the site
        self.distribution = Distribution(self, "personal-site-cf-distribution",
                                         default_behavior={
                                             "origin": S3Origin(self.website_bucket),
                                             "allowed_methods": AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                                             "viewer_protocol_policy": ViewerProtocolPolicy.REDIRECT_TO_HTTPS
                                         },
                                         certificate=self.cert,
                                         minimum_protocol_version=SecurityPolicyProtocol.TLS_V1_2_2019,
                                         enable_ipv6=True,
                                         domain_names=[domain_name, f"www.{domain_name}"])

        # Point traffic to base and www.base to the cloudfront distribution, for both IPv4 and IPv6
        ARecord(self, "personal-site-a-record",
                zone=self.hosted_zone,
                record_name=f"{domain_name}.",
                target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)))
        ARecord(self, "personal-site-a-record-www",
                zone=self.hosted_zone,
                target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)),
                record_name=f"www.{domain_name}.")
        AaaaRecord(self, "personal-site-aaaa-record",
                   zone=self.hosted_zone,
                   record_name=f"{domain_name}.",
                   target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)))
        AaaaRecord(self, "personal-site-aaaa-record-www",
                   zone=self.hosted_zone,
                   target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)),
                   record_name=f"www.{domain_name}.")

        #############################
        # WEBSITE CD INFRASTRUCTURE #
        #############################

        # CodeBuild project to build the website
        self.code_build_project = \
            Project(self, "personal-site-builder",
                    project_name="PersonalWebsite",
                    description="Builds & deploys a personal static website on changes from GitHub",
                    source=Source.git_hub(
                        owner="c7c8",
                        repo="crmyers.dev",
                        clone_depth=1,
                        branch_or_ref="master",
                        webhook_filters=[
                            FilterGroup.in_event_of(EventAction.PUSH, EventAction.PULL_REQUEST_MERGED).and_branch_is(
                                "master")]),
                    artifacts=Artifacts.s3(bucket=self.website_bucket, include_build_id=False,
                                           package_zip=False,
                                           path="/"),
                    build_spec=BuildSpec.from_object_to_yaml({
                        "version": "0.2",
                        "phases": {
                            "install": {
                                "runtime-versions": {
                                    "nodejs": 10,
                                }
                            },
                            "pre_build": {
                                "commands": ["npm install"]
                            },
                            "build": {
                                "commands": [
                                    "npm run-script build &&",
                                    f"aws cloudfront create-invalidation --distribution-id={self.distribution.distribution_id} --paths '/*'"
                                ]
                            }
                        },
                        "artifacts": {
                            "files": ["./*"],
                            "name": ".",
                            "discard-paths": "no",
                            "base-directory": "dist/crmyers-dev"
                        }
                    }))
        self.code_build_project.role.add_to_policy(PolicyStatement(
            effect=Effect.ALLOW,
            resources=[f"arn:aws:cloudfront::{self.account}:distribution/{self.distribution.distribution_id}"],
            actions=['cloudfront:CreateInvalidation']
        ))

        # Set up an SNS topic for text message notifications
        self.deployment_topic = Topic(self, 'personal-site-deployment-topic',
                                      topic_name='WebsiteDeployments',
                                      display_name='Website Deployments')
        self.deployment_topic.add_subscription(SmsSubscription("+19255968684"))
        self.code_build_project.on_build_failed("BuildFailed",
                                                target=targets.SnsTopic(self.deployment_topic,
                                                                        message=RuleTargetInput.from_text("Build for crmyers.dev FAILED")))
        self.code_build_project.on_build_succeeded("BuildSucceeded",
                                                   target=targets.SnsTopic(self.deployment_topic,
                                                                           message=RuleTargetInput.from_text("Build for crmyers.dev SUCCEEDED")))

