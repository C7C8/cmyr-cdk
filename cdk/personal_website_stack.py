from aws_cdk import core
from aws_cdk.aws_certificatemanager import DnsValidatedCertificate
from aws_cdk.aws_cloudfront import Distribution, SecurityPolicyProtocol, AllowedMethods, ViewerProtocolPolicy
from aws_cdk.aws_cloudfront_origins import S3Origin
from aws_cdk.aws_route53 import PublicHostedZone, MxRecord, RecordTarget, MxRecordValue, \
    ARecord, AaaaRecord
from aws_cdk.aws_route53_targets import CloudFrontTarget
from aws_cdk.aws_s3 import Bucket
from aws_cdk.core import RemovalPolicy


class PersonalWebsiteStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str,
                 domain_name: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a hosted zone for the website to contain our records
        self.hosted_zone = PublicHostedZone(self, 'personal-site-hosted-zone',
                                            zone_name=domain_name)
        domain_name = self.hosted_zone.zone_name

        # Allow Google to manage mail for this domain
        MxRecord(self, "personal-site-gmail",
                 zone=self.hosted_zone,
                 values=[MxRecordValue(host_name="gmr-smtp-in.l.google.com.", priority=5),
                         MxRecordValue(host_name="alt1.gmr-smtp-in.l.google.com.", priority=10),
                         MxRecordValue(host_name="alt2.gmr-smtp-in.l.google.com.", priority=20),
                         MxRecordValue(host_name="alt3.gmr-smtp-in.l.google.com.", priority=30),
                         MxRecordValue(host_name="alt4.gmr-smtp-in.l.google.com.", priority=40)])

        # Add an S3 bucket to host the website content
        self.website_bucket = Bucket(self, "personal-site-bucket",
                                     bucket_name=domain_name,
                                     removal_policy=RemovalPolicy.DESTROY,
                                     public_read_access=True,
                                     website_index_document="index.html",
                                     website_error_document="index.html")

        # ...and an SSL certificate for HTTPS
        self.cert = DnsValidatedCertificate(self, 'personal-site-cert',
                                            hosted_zone=self.hosted_zone,
                                            domain_name=domain_name,
                                            subject_alternative_names=[f"www.{domain_name}"])

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
                target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)))
        ARecord(self, "personal-site-a-record-www",
                zone=self.hosted_zone,
                target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)),
                record_name='www')
        AaaaRecord(self, "personal-site-aaaa-record",
                   zone=self.hosted_zone,
                   target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)))
        AaaaRecord(self, "personal-site-aaaa-record-www",
                   zone=self.hosted_zone,
                   target=RecordTarget.from_alias(CloudFrontTarget(self.distribution)),
                   record_name='www')
