#!/usr/bin/env python3

from aws_cdk import core

from cdk.personal_website_stack import PersonalWebsiteStack

app = core.App()

PersonalWebsiteStack(app, "PersonalWebsite",
                     stack_name="PersonalWebsite",
                     termination_protection=True,
                     cert_arn="arn:aws:acm:us-east-1:690829806577:certificate/e4db35bd-12f5-450c-82d4-5fa6fe3e9374",
                     hosted_zone_id="Z06368022REVB4Y50QOQM",
                     domain_name="crmyers.dev",
                     tags={"project": "personal-site"},
                     description="Stack for my personal static website")
app.synth()
